from ipaddress import ip_address

from fastapi import Request
from supabase import Client

from app.repositories.log_auditoria_repository import LogAuditoriaRepository


class AuditService:
    def __init__(self, repository: LogAuditoriaRepository | None = None) -> None:
        self.repository = repository or LogAuditoriaRepository()

    def get_ip_origen(self, request: Request) -> str | None:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            candidate = forwarded_for.split(",")[0].strip()
        else:
            candidate = request.client.host if request.client else None

        if not candidate:
            return None

        try:
            ip_address(candidate)
            return candidate
        except ValueError:
            return None

    def get_id_usuario(self, supabase: Client, authorization_header: str | None) -> str | None:
        token = self._extract_bearer_token(authorization_header)
        if not token:
            return None

        try:
            user_response = supabase.auth.get_user(token)
            user = getattr(user_response, "user", None)
            user_id = getattr(user, "id", None)
            return str(user_id) if user_id else None
        except Exception:
            return None

    def get_authenticated_user_id(self, request: Request, allow_token_user_id: bool = True) -> str | None:
        cached_user = getattr(request.state, "authenticated_user", None)
        user_id = getattr(cached_user, "id_usuario", None)
        if user_id:
            return str(user_id)

        if not allow_token_user_id:
            return None

        cached_id = getattr(request.state, "authenticated_user_id", None)
        return str(cached_id) if cached_id else None

    def build_detail(self, status_code: int, path: str, query: str) -> str:
        detail = f"status={status_code}; path={path}; query={query if query else '-'}"
        return self._truncate_detail(detail)

    def build_exception_detail(self, exception: Exception, status_code: int, path: str, query: str) -> str:
        detail = (
            f"status={status_code}; path={path}; query={query if query else '-'}; "
            f"exception={exception.__class__.__name__}"
        )
        return self._truncate_detail(detail)

    def record(
        self,
        supabase: Client,
        tipo_accion: str,
        id_usuario: str | None,
        ip_origen: str | None,
        resultado: str,
        detalle: str,
    ) -> None:
        payload = {
            "tipo_accion": tipo_accion,
            "id_usuario": id_usuario,
            "ip_origen": ip_origen,
            "resultado": resultado,
            "detalle": self._truncate_detail(detalle),
        }
        self.repository.insert(supabase=supabase, payload=payload)

    @staticmethod
    def _truncate_detail(detail: str) -> str:
        return detail[:255]

    @staticmethod
    def _extract_bearer_token(authorization_header: str | None) -> str | None:
        if not authorization_header:
            return None

        scheme, _, token = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        return token.strip()
