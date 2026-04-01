from collections.abc import Mapping
from typing import Any

import httpx
from fastapi import HTTPException, status


class IpsClient:
    def __init__(self, timeout_seconds: float = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        *,
        method: str,
        base_url: str,
        api_key: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        url = f"{base_url.rstrip('/')}{path}"
        headers = {"x-api-key": api_key}
        try:
            response = httpx.request(
                method=method,
                url=url,
                headers=headers,
                json=payload,
                params=params,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Timeout al consultar IPS",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No fue posible conectar con la IPS",
            ) from exc

        body = _safe_json(response)
        if response.status_code >= 400:
            detail = body.get("detail") if isinstance(body, dict) else None
            raise HTTPException(
                status_code=response.status_code,
                detail=detail or "Error en respuesta de la IPS",
            )
        return body


def _safe_json(response: httpx.Response) -> Any:
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        return {}
