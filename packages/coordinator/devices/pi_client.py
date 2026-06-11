from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import HTTPException


class PiClient:
    def __init__(self, base_url: str, timeout: float = 8.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    params=params,
                    json=body,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = _response_detail(exc.response)
                raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail=f"Pi request failed: {exc}") from exc
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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, f"{self.base_url}{path}", params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = _response_detail(exc.response)
                raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail=f"Pi request failed: {exc}") from exc
        return (
            response.content,
            response.headers.get("content-type", "application/octet-stream"),
            response.headers.get("content-disposition"),
        )


def _response_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            return str(data.get("detail") or data)
    except ValueError:
        pass
    return response.text or f"HTTP {response.status_code}"

