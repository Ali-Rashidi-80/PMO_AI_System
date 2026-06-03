"""LM Studio HTTP client — patterns from pc_client/main.py."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Dict, Optional

import httpx

logger = logging.getLogger("lm_client")

_PROXY_VARS = [
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
]
for _var in _PROXY_VARS:
    os.environ.pop(_var, None)


def normalize_host(raw: str) -> str:
    host = raw.strip().rstrip("/")
    if not host.startswith("http://") and not host.startswith("https://"):
        return f"http://{host}"
    return host


class LMStudioClient:
    def __init__(
        self,
        upstream: str,
        timeout_seconds: float = 900.0,
        max_concurrent: int = 2,
    ) -> None:
        self.upstream = normalize_host(upstream)
        self.timeout_seconds = timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=40,
            keepalive_expiry=30.0,
        )
        self._timeout = httpx.Timeout(timeout_seconds, connect=10.0)
        self._client = httpx.AsyncClient(
            limits=limits,
            timeout=self._timeout,
            trust_env=False,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_models(self) -> Dict[str, Any]:
        resp = await self._client.get(f"{self.upstream}/v1/models", timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    async def health(self) -> Dict[str, Any]:
        try:
            data = await self.get_models()
            models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
            return {"status": "up", "lmstudio": "up", "models": models}
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("LM Studio health check failed: %s", exc)
            return {"status": "down", "lmstudio": "down", "models": [], "error": str(exc)}

    async def unload_all_models(self) -> None:
        resp = await self._client.get(f"{self.upstream}/v1/models", timeout=10.0)
        if resp.status_code != 200:
            return
        for model in resp.json().get("data", []):
            mid = model.get("id")
            if not mid:
                continue
            try:
                await self._client.post(
                    f"{self.upstream}/api/v1/models/unload",
                    json={"model": mid},
                    timeout=10.0,
                )
            except Exception:  # pylint: disable=broad-except
                pass

    async def proxy_request(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ) -> httpx.Response:
        url = f"{self.upstream}{path}"
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(
                {k: v for k, v in headers.items() if k.lower() != "host"}
            )
        async with self._semaphore:
            if stream:
                return await self._client.build_request(
                    method, url, content=body, headers=req_headers
                )
            return await self._client.request(
                method, url, content=body, headers=req_headers
            )

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload.setdefault("stream", False)
        async with self._semaphore:
            resp = await self._client.post(
                f"{self.upstream}/v1/chat/completions",
                json=payload,
                timeout=self.timeout_seconds,
            )
        if resp.status_code != 200:
            detail = resp.text[:500]
            raise httpx.HTTPStatusError(
                f"LM Studio error {resp.status_code}: {detail}",
                request=resp.request,
                response=resp,
            )
        data = resp.json()
        if not data.get("choices"):
            data = {
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "object": "chat.completion",
            }
        return data

    async def embeddings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with self._semaphore:
            resp = await self._client.post(
                f"{self.upstream}/v1/embeddings",
                json=payload,
                timeout=120.0,
            )
        if resp.status_code != 200:
            detail = resp.text[:300]
            raise httpx.HTTPStatusError(
                f"LM Studio embed {resp.status_code}: {detail}",
                request=resp.request,
                response=resp,
            )
        return resp.json()

    async def stream_chat_completions(
        self, payload: Dict[str, Any]
    ) -> AsyncIterator[bytes]:
        payload = dict(payload)
        payload["stream"] = True
        async with self._semaphore:
            async with self._client.stream(
                "POST",
                f"{self.upstream}/v1/chat/completions",
                json=payload,
                timeout=self.timeout_seconds,
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    yield chunk
