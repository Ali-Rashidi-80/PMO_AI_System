"""PMO LM Studio Gateway — FastAPI proxy + BFF for UI and optional n8n."""

from __future__ import annotations

import io
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from fastapi import FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from config import load_settings
from lm_client import LMStudioClient
from documents_service import delete_document, list_documents, upload_documents
from manifest import list_files, load_manifest, summarize_documents
from pmo_service import pmo_chat, pmo_ingest, pmo_letter, pmo_risk, prepare_chat_messages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

settings = load_settings()
lm: Optional[LMStudioClient] = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global lm  # noqa: PLW0603
    lm = LMStudioClient(
        settings.lmstudio_upstream,
        timeout_seconds=settings.llm_timeout_seconds,
        max_concurrent=settings.max_concurrent,
    )
    yield
    if lm:
        await lm.close()


app = FastAPI(title="PMO LM Studio Gateway", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _check_webhook(token: Optional[str]) -> None:
    if not token or token != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")


async def _lm_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    assert lm is not None
    return await lm.chat_completions(payload)


async def _lm_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    assert lm is not None
    if path == "/v1/embeddings":
        return await lm.embeddings(payload)
    raise ValueError(f"unsupported path {path}")


async def _n8n_webhook(path: str, payload: Dict[str, Any], token: str) -> Dict[str, Any]:
    url = f"{settings.n8n_internal_url}{path}"
    headers = {"X-PMO-Token": token, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds, trust_env=False) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"ارتباط با n8n برقرار نشد: {exc}") from exc
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    try:
        return resp.json()
    except json.JSONDecodeError:
        return {"status": "success", "raw": resp.text}


@app.get("/health")
async def health() -> Dict[str, Any]:
    assert lm is not None
    base = await lm.health()
    qdrant_ok = False
    n8n_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
            qresp = await client.get(f"{settings.qdrant_url}/healthz")
            qdrant_ok = qresp.status_code == 200
            nresp = await client.get(f"{settings.n8n_internal_url}/healthz")
            n8n_ok = nresp.status_code == 200
    except Exception:  # pylint: disable=broad-except
        pass
    base["qdrant"] = "up" if qdrant_ok else "down"
    base["n8n"] = "up" if n8n_ok else "down"
    base["llm_model"] = settings.llm_model_id
    base["embed_model"] = settings.embed_model_id
    base["mode"] = "gateway-direct"
    return base


@app.get("/v1/models")
async def list_models() -> Dict[str, Any]:
    assert lm is not None
    try:
        return await lm.get_models()
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    assert lm is not None
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    if payload.get("stream"):
        async def streamer():
            assert lm is not None
            async for chunk in lm.stream_chat_completions(payload):
                yield chunk

        return StreamingResponse(streamer(), media_type="text/event-stream")
    try:
        data = await lm.chat_completions(payload)
        return JSONResponse(content=data)
    except httpx.HTTPStatusError as exc:
        return JSONResponse(
            status_code=502,
            content={"error": {"message": str(exc), "type": "upstream_error"}},
        )


@app.post("/v1/embeddings")
async def embeddings(request: Request) -> Response:
    assert lm is not None
    payload = json.loads(await request.body())
    payload.setdefault("model", settings.embed_model_id)
    try:
        data = await lm.embeddings(payload)
        return JSONResponse(content=data)
    except Exception as exc:  # pylint: disable=broad-except
        return JSONResponse(
            status_code=502,
            content={"error": {"message": str(exc), "type": "upstream_error"}},
        )


@app.get("/api/pmo/status")
async def pmo_status() -> Dict[str, Any]:
    health_data = await health()
    docs_root = Path(settings.pmo_docs_path)
    manifest = load_manifest(docs_root)
    files = list_files(docs_root)
    doc_summary = summarize_documents(files)
    return {
        "dashboard": health_data,
        "public_url": settings.lmstudio_upstream,
        "ready": health_data.get("lmstudio") == "up",
        "documents_count": len(files),
        "documents_summary": doc_summary,
        "last_ingest_at": manifest.get("last_ingest_at"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "rag_min_score": settings.rag_min_score,
        "embed_model_id": settings.embed_model_id,
        "llm_model_id": settings.llm_model_id,
        "upload_auto_ingest": settings.upload_auto_ingest,
        "qdrant_collection": settings.qdrant_collection,
        "limits": {
            "max_upload_mb": settings.max_upload_mb,
            "max_files_per_upload": settings.max_files_per_upload,
        },
        "supported_formats": [".txt", ".docx", ".pdf", ".md", ".csv", ".json", ".log", ".text"],
        "services": {
            "gateway": "up",
            "lmstudio": health_data.get("lmstudio", "down"),
            "qdrant": health_data.get("qdrant", "down"),
            "n8n": health_data.get("n8n", "down"),
        },
        "architecture": {
            "ui": "مرورگر → Gateway → LM Studio (streaming)",
            "rag": "Gateway → Qdrant (اختیاری برای اسناد PMO)",
            "n8n": "Webhook/zمان‌بندی → Gateway (همان منطق UI)",
        },
    }


@app.post("/api/pmo/chat")
async def api_pmo_chat(
    request: Request,
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    body = await request.json()
    try:
        return await pmo_chat(
            body=body,
            settings=settings,
            lm_chat=_lm_chat,
            lm_post=_lm_post,
            prompts_dir=Path(settings.prompts_path),
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("chat failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/pmo/chat/stream")
async def api_pmo_chat_stream(
    request: Request,
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> StreamingResponse:
    _check_webhook(x_pmo_token)
    body = await request.json()
    prep = await prepare_chat_messages(
        body=body,
        settings=settings,
        lm_post=_lm_post,
        prompts_dir=Path(settings.prompts_path),
    )
    if prep.get("error"):
        raise HTTPException(status_code=400, detail=prep["error"])

    payload = {
        "model": settings.llm_model_id,
        "messages": prep["messages"],
        "temperature": prep["temperature"],
        "stream": True,
    }
    used_rag = prep["used_rag"]

    async def generate():
        assert lm is not None
        buffer = ""
        try:
            async for chunk_bytes in lm.stream_chat_completions(payload):
                buffer += chunk_bytes.decode("utf-8", errors="ignore")
                while "\n\n" in buffer:
                    block, buffer = buffer.split("\n\n", 1)
                    for line in block.split("\n"):
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            yield f"data: {json.dumps({'done': True, 'used_rag': used_rag}, ensure_ascii=False)}\n\n"
                            return
                        try:
                            obj = json.loads(data_str)
                            delta = (obj.get("choices") or [{}])[0].get("delta", {}).get("content") or ""
                            if delta:
                                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
                        except json.JSONDecodeError:
                            continue
            yield f"data: {json.dumps({'done': True, 'used_rag': used_rag}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("chat stream failed")
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/pmo/letter")
async def api_pmo_letter(
    request: Request,
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    body = await request.json()
    try:
        return await pmo_letter(
            body=body,
            settings=settings,
            prompts_dir=Path(settings.prompts_path),
            lm_chat=_lm_chat,
            lm_post=_lm_post,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("letter failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/pmo/letter/docx")
async def pmo_letter_docx(
    request: Request,
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Response:
    _check_webhook(x_pmo_token)
    body = await request.json()
    letter_text = body.get("letter", "")
    if not letter_text:
        raise HTTPException(status_code=400, detail="letter الزامی است")
    doc = Document()
    for line in letter_text.split("\n"):
        para = doc.add_paragraph(line)
        para.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return Response(
        content=buffer.read(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=pmo_letter.docx"},
    )


@app.post("/api/pmo/risk/run")
async def api_pmo_risk(
    request: Request,
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    body = await request.json() if request.headers.get("content-length") else {}
    try:
        return await pmo_risk(
            body=body or {},
            settings=settings,
            prompts_dir=Path(settings.prompts_path),
            docs_path=Path(settings.pmo_docs_path),
            lm_chat=_lm_chat,
            lm_post=_lm_post,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("risk failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/pmo/ingest")
async def api_pmo_ingest(
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    try:
        return await pmo_ingest(
            settings=settings,
            docs_path=Path(settings.pmo_docs_path),
            lm_post=_lm_post,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/pmo/documents/list")
async def api_documents_list(
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    return await list_documents(Path(settings.pmo_docs_path))


@app.delete("/api/pmo/documents/{name:path}")
async def api_documents_delete(
    name: str,
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    result = await delete_document(
        docs_root=Path(settings.pmo_docs_path),
        name=name,
        settings=settings,
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=404, detail=result.get("message", "یافت نشد"))
    return result


@app.post("/api/pmo/documents/upload")
async def api_documents_upload(
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
    files: list[UploadFile] = File(default=[]),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    if not files:
        raise HTTPException(status_code=400, detail="فایلی ارسال نشده")
    payload: list = []
    for uf in files:
        content = await uf.read()
        payload.append((uf.filename or "upload.bin", content))
    try:
        return await upload_documents(
            files=payload,
            docs_root=Path(settings.pmo_docs_path),
            settings=settings,
            lm_post=_lm_post,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("upload failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/pmo/n8n/letter")
async def pmo_letter_n8n(
    request: Request,
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    body = await request.json()
    return await _n8n_webhook("/webhook/pmo/letter", body, x_pmo_token or "")


@app.post("/api/pmo/n8n/ingest")
async def pmo_ingest_n8n(
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    return await _n8n_webhook("/webhook/pmo/ingest", {}, x_pmo_token or "")


@app.post("/api/pmo/n8n/risk")
async def pmo_risk_n8n(
    request: Request,
    x_pmo_token: Optional[str] = Header(default=None, alias="X-PMO-Token"),
) -> Dict[str, Any]:
    _check_webhook(x_pmo_token)
    body = await request.json() if request.headers.get("content-length") else {}
    return await _n8n_webhook("/webhook/pmo/risk", body or {}, x_pmo_token or "")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.gateway_host,
        port=settings.gateway_port,
        reload=False,
    )
