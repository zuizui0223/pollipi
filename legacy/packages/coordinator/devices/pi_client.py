from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import httpx
from fastapi import HTTPException

DEVICE_SECRET_HEADER = "X-Pollipi-Device-Secret"


class PiClient:
    def __init__(self, base_url: str, timeout: float = 8.0, device_secret: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout, connect=2.0, read=timeout, write=4.0, pool=2.0)
        self.device_secret = (device_secret or "").strip()
        self._client: Optional[httpx.AsyncClient] = None
        self._failures = 0
        self._cooldown_until = 0.0
        self._inflight: dict[tuple[str, str, str, str], asyncio.Task] = {}

    def headers(self) -> dict[str, str]:
        if not self.device_secret:
            return {}
        return {DEVICE_SECRET_HEADER: self.device_secret}

    async def json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> Any:
        response = await self._coalesced_request(method, path, params=params, body=body)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text

    async def bytes(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
    ) -> tuple[bytes, str, Optional[str]]:
        response = await self._request(method, path, params=params)
        return (
            response.content,
            response.headers.get("content-type", "application/octet-stream"),
            response.headers.get("content-disposition"),
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _coalesced_request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        key = (method.upper(), path, repr(sorted((params or {}).items())), repr(sorted((body or {}).items())))
        task = self._inflight.get(key)
        if task is None or task.done():
            task = asyncio.create_task(self._request(method, path, params=params, body=body))
            self._inflight[key] = task
        try:
            return await task
        finally:
            if self._inflight.get(key) is task:
                self._inflight.pop(key, None)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        now = time.monotonic()
        if now < self._cooldown_until:
            raise HTTPException(status_code=503, detail="Pi circuit breaker cooling down")
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        try:
            response = await self._client.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=body,
                headers=self.headers(),
            )
            response.raise_for_status()
            self._failures = 0
            return response
        except httpx.HTTPStatusError as exc:
            detail = _response_detail(exc.response)
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.HTTPError as exc:
            self._failures += 1
            if self._failures >= 3:
                self._cooldown_until = time.monotonic() + min(30.0, 2.0 * self._failures)
            raise HTTPException(status_code=502, detail=f"Pi request failed: {exc}") from exc


def _response_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            return str(data.get("detail") or data)
    except ValueError:
        pass
    return response.text or f"HTTP {response.status_code}"

