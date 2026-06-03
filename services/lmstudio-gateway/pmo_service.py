"""PMO business logic — direct LM Studio + Qdrant (no n8n dependency for UI)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from document_loader import read_documents
from rag import format_context, ingest_directory, search


def _load_prompt(prompts_dir: Path, name: str, fallback: str) -> str:
    path = prompts_dir / name
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return fallback


def sanitize_model_output(text: str) -> str:
    text = re.sub(r"<\|think\|>[\s\S]*?<\|/think\|>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\|think\|>[^\n]*\n?", "", text, flags=re.IGNORECASE)
    if text.strip() == "ERROR_NO_DOCS":
        return "سند معتبری در پایگاه یافت نشد. لطفاً از اطلاعات ورودی کاربر استفاده کنید."
    return text.strip()


def _load_chat_system(prompts_dir: Path) -> str:
    return _load_prompt(
        prompts_dir,
        "chat_system.txt",
        "شما دستیار هوشمند PMO هستید. پاسخ دقیق، رسمی و فارسی بدهید. "
        "اگر اطلاعات کافی ندارید صادقانه بگویید.",
    )


async def chat_completion(
    lm_chat,
    *,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    data = await lm_chat(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
    )
    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    content = msg.get("content") or ""
    return sanitize_model_output(content)


async def prepare_chat_messages(
    *,
    body: Dict[str, Any],
    settings,
    lm_post: Callable,
    prompts_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    prompt = (body.get("prompt") or body.get("message") or "").strip()
    if not prompt:
        return {"error": "متن درخواست الزامی است"}

    default_system = (
        _load_chat_system(prompts_dir)
        if prompts_dir
        else "شما دستیار هوشمند PMO هستید. پاسخ دقیق، رسمی و فارسی بدهید."
    )
    system = (body.get("system_prompt") or "").strip() or default_system
    temperature = float(body.get("temperature", 0.3))
    use_rag = bool(body.get("use_rag", False))

    user_msg = prompt
    rag_used = False
    if use_rag:
        hits = await search(
            query=prompt,
            qdrant_url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            embed_model=settings.embed_model_id,
            lm_post=lm_post,
            min_score=settings.rag_min_score,
            embed_batch_size=settings.embed_batch_size,
        )
        ctx = format_context(hits)
        if ctx:
            user_msg = f"{ctx}\n\n---\n\nدرخواست کاربر:\n{prompt}"
            rag_used = True
        else:
            user_msg = (
                f"{prompt}\n\n[توجه: سند مرتبطی در پایگاه یافت نشد — "
                "فقط بر اساس دانش عمومی PMO پاسخ دهید.]"
            )

    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        "temperature": temperature,
        "used_rag": rag_used,
    }


async def pmo_chat(
    *,
    body: Dict[str, Any],
    settings,
    lm_chat: Callable,
    lm_post: Callable,
    prompts_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    prep = await prepare_chat_messages(
        body=body,
        settings=settings,
        lm_post=lm_post,
        prompts_dir=prompts_dir,
    )
    if prep.get("error"):
        return {"status": "failed", "message": prep["error"]}

    text = await chat_completion(
        lm_chat,
        model=settings.llm_model_id,
        system=prep["messages"][0]["content"],
        user=prep["messages"][1]["content"],
        temperature=prep["temperature"],
    )
    if not text:
        return {"status": "failed", "message": "پاسخی از مدل دریافت نشد"}
    return {"status": "success", "output": text, "used_rag": prep["used_rag"]}


async def pmo_letter(
    *,
    body: Dict[str, Any],
    settings,
    prompts_dir: Path,
    lm_chat: Callable,
    lm_post: Callable,
) -> Dict[str, Any]:
    contractor = (body.get("contractor_name") or "").strip()
    subject = (body.get("delay_subject") or body.get("subject") or "").strip()
    extra = (body.get("extra_context") or "").strip()
    free = (body.get("free_prompt") or "").strip()

    if not contractor and not subject and not extra and not free:
        return {"status": "failed", "message": "حداقل یکی از فیلدها را پر کنید"}

    system = _load_prompt(
        prompts_dir,
        "scenario_a_legal.txt",
        "کارشناس حقوقی PMO — نامه رسمی فارسی بدون جعل اطلاعات.",
    )
    query = f"پیمانکار: {contractor} — موضوع: {subject} — {extra}".strip()
    hits = await search(
        query=query or free or "نامه PMO",
        qdrant_url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        embed_model=settings.embed_model_id,
        lm_post=lm_post,
        min_score=settings.rag_min_score,
        embed_batch_size=settings.embed_batch_size,
    )
    ctx = format_context(hits)
    if free:
        user = free
        if ctx:
            user += f"\n\n{ctx}"
    else:
        user = f"نگارش نامه اخطار رسمی.\nپیمانکار: {contractor}\nموضوع تأخیر: {subject}\n"
        if extra:
            user += f"توضیحات: {extra}\n"
        if ctx:
            user += f"\n{ctx}\n"

    letter = await chat_completion(
        lm_chat,
        model=settings.llm_model_id,
        system=system,
        user=user,
        temperature=0.1,
    )
    if not letter.strip():
        return {"status": "failed", "message": "پاسخی از مدل دریافت نشد — LM Studio را بررسی کنید"}
    return {"status": "success", "letter": letter}


def _parse_risk_json(raw: str) -> List[Any]:
    try:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            parsed = json.loads(match.group(0))
            risks = parsed.get("project_risks", parsed)
            if isinstance(risks, list):
                return risks
    except (json.JSONDecodeError, TypeError):
        pass
    return [
        {
            "risk_title": "تحلیل متنی",
            "severity": "Medium",
            "evidence": raw[:400],
            "recommended_action": "بررسی دستی",
        }
    ]


async def pmo_risk(
    *,
    body: Dict[str, Any],
    settings,
    prompts_dir: Path,
    docs_path: Path,
    lm_chat: Callable,
    lm_post: Callable,
) -> Dict[str, Any]:
    system = _load_prompt(
        prompts_dir,
        "scenario_b_risk.txt",
        "تحلیلگر ریسک PMO — خروجی JSON با کلید project_risks.",
    )
    reports_dir = docs_path / "weekly_reports"
    report_text = read_documents(reports_dir) or read_documents(docs_path)
    extra = (body.get("context") or body.get("prompt") or "").strip()

    if not report_text and not extra:
        return {"status": "failed", "message": "گزارش یا متن ورودی یافت نشد"}

    hits = await search(
        query=(report_text[:500] if report_text else extra),
        qdrant_url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        embed_model=settings.embed_model_id,
        lm_post=lm_post,
        min_score=settings.rag_min_score,
        embed_batch_size=settings.embed_batch_size,
    )
    ctx = format_context(hits)
    user = f"گزارشات:\n{report_text or extra}\n"
    if ctx:
        user += f"\n{ctx}\n"
    user += "\nخروجی: JSON با کلید project_risks (risk_title, severity, evidence, recommended_action)"

    raw = await chat_completion(
        lm_chat,
        model=settings.llm_model_id,
        system=system,
        user=user,
        temperature=0.3,
    )
    if not raw.strip():
        return {"status": "failed", "message": "تحلیل ریسک ناموفق بود"}

    project_risks = _parse_risk_json(raw)

    rows = ""
    for r in project_risks if isinstance(project_risks, list) else []:
        rows += (
            f"<tr><td>{r.get('risk_title', '')}</td>"
            f"<td>{r.get('severity', '')}</td>"
            f"<td>{r.get('evidence', '')}</td>"
            f"<td>{r.get('recommended_action', '')}</td></tr>"
        )
    html = (
        "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='UTF-8'>"
        "<style>body{font-family:Tahoma,sans-serif;background:#0a0a0a;color:#eee;padding:20px}"
        "table{width:100%;border-collapse:collapse}td,th{border:1px solid #333;padding:8px}</style>"
        "</head><body><h2>گزارش ریسک PMO</h2><table>"
        "<tr><th>ریسک</th><th>شدت</th><th>مدرک</th><th>اقدام</th></tr>"
        f"{rows}</table></body></html>"
    )
    return {"status": "success", "project_risks": project_risks, "htmlReport": html, "raw": raw}


async def pmo_ingest(
    *,
    settings,
    docs_path: Path,
    lm_post: Callable,
) -> Dict[str, Any]:
    result = await ingest_directory(
        docs_path=docs_path,
        qdrant_url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        embed_model=settings.embed_model_id,
        lm_post=lm_post,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        strict_clean=settings.strict_clean,
        embed_batch_size=settings.embed_batch_size,
        rag_reset=settings.rag_reset,
        rag_min_score=settings.rag_min_score,
    )
    if result.get("status") == "success":
        from manifest import set_last_ingest

        set_last_ingest(docs_path)
    return result
