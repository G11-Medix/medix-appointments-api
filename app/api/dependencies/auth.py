from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.db.supabase import get_supabase_client

_bearer_scheme = HTTPBearer(auto_error=False)
ADMIN_ROLES = frozenset({"ADMIN", "ADMINISTRADOR", "SUPERADMIN"})


@dataclass(frozen=True)
class AuthenticatedUserContext:
    id_usuario: UUID
    rol: str
    estado: str


def require_active_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> AuthenticatedUserContext:
    if not credentials:
        raise _unauthorized("Token de acceso requerido")

    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _unauthorized("Formato de autorización inválido")

    token = credentials.credentials.strip()
    if not token:
        raise _unauthorized("Formato de autorización inválido")

    supabase = get_supabase_client()
    user_id = _validate_token(supabase=supabase, token=token)

    request.state.authenticated_user_id = user_id

    usuario = _get_usuario(supabase=supabase, user_id=user_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no autorizado",
        )

    estado_usuario = str(usuario.get("estado") or "").upper()
    if estado_usuario != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo o no autorizado",
        )

    rol_usuario = str(usuario.get("rol") or "")
    try:
        context = AuthenticatedUserContext(
            id_usuario=UUID(user_id),
            rol=rol_usuario,
            estado=estado_usuario,
        )
    except ValueError as exc:
        raise _unauthorized("Token inválido") from exc

    request.state.authenticated_user = context
    return context


def get_authenticated_user_from_state(request: Request) -> AuthenticatedUserContext:
    context = getattr(request.state, "authenticated_user", None)
    if isinstance(context, AuthenticatedUserContext):
        return context

    raise _unauthorized("Sesión no autenticada")


def require_active_admin_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> AuthenticatedUserContext:
    context = getattr(request.state, "authenticated_user", None)
    if not isinstance(context, AuthenticatedUserContext):
        context = require_active_user(request=request, credentials=credentials)

    if str(context.rol or "").upper() not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sin permisos administrativos",
        )

    return context


def _validate_token(supabase: Client, token: str) -> str:
    try:
        user_response = supabase.auth.get_user(token)
    except Exception as exc:
        raise _unauthorized("Token inválido o expirado") from exc

    user = getattr(user_response, "user", None)
    user_id = getattr(user, "id", None)
    if not user_id:
        raise _unauthorized("Token inválido o expirado")
    return str(user_id)


def _get_usuario(supabase: Client, user_id: str) -> dict | None:
    response = (
        supabase.table("Usuario")
        .select("id_usuario,rol,estado")
        .eq("id_usuario", user_id)
        .limit(1)
        .execute()
    )
    data = response.data or []
    return data[0] if data else None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
