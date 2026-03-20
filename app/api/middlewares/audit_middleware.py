from collections.abc import Callable

from fastapi import Request
from starlette.responses import Response
from supabase import Client

from app.services.audit_service import AuditService

AUDITED_PREFIX = "/api/"
EXCLUDED_PATHS = {"/", "/docs", "/redoc", "/openapi.json"}


def build_audit_middleware(supabase: Client) -> Callable:
    service = AuditService()

    async def audit_middleware(request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if not _should_audit(path):
            return await call_next(request)

        query = request.url.query
        tipo_accion = f"{request.method} {path}"
        ip_origen = service.get_ip_origen(request)
        id_usuario = service.get_id_usuario(supabase, request.headers.get("authorization"))

        try:
            response = await call_next(request)
            status_code = response.status_code
            resultado = "EXITO" if status_code < 400 else "ERROR"
            detalle = service.build_detail(status_code=status_code, path=path, query=query)

            try:
                service.record(
                    supabase=supabase,
                    tipo_accion=tipo_accion,
                    id_usuario=id_usuario,
                    ip_origen=ip_origen,
                    resultado=resultado,
                    detalle=detalle,
                )
            except Exception:
                pass

            return response
        except Exception as exc:
            status_code = getattr(exc, "status_code", 500)
            detalle = service.build_exception_detail(
                exception=exc,
                status_code=status_code,
                path=path,
                query=query,
            )

            try:
                service.record(
                    supabase=supabase,
                    tipo_accion=tipo_accion,
                    id_usuario=id_usuario,
                    ip_origen=ip_origen,
                    resultado="ERROR",
                    detalle=detalle,
                )
            except Exception:
                pass

            raise

    return audit_middleware


def _should_audit(path: str) -> bool:
    return path.startswith(AUDITED_PREFIX) and path not in EXCLUDED_PATHS
