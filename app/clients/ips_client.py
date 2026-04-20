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
        path: str,
        payload: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        extra_headers: Mapping[str, Any] | None = None,
    ) -> Any:
        url = f"{base_url.rstrip('/')}{path}"
        headers: dict[str, str] = {}
        if extra_headers:
            headers.update({str(key): str(value) for key, value in extra_headers.items()})
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
            detail = _extract_error_detail(body)
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


def _extract_error_detail(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    if "detail" in body:
        return str(body["detail"])
    if body.get("resourceType") == "OperationOutcome":
        issues = body.get("issue")
        if isinstance(issues, list) and issues:
            diagnostics = issues[0].get("diagnostics")
            if diagnostics:
                return str(diagnostics)
    return None
