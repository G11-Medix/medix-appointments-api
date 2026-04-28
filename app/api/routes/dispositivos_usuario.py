from typing import Annotated

from fastapi import APIRouter, Depends, Request
from supabase import Client

from app.db.supabase import get_supabase_client
from app.services.dispositivos_usuario_service import DispositivosUsuarioService
from app.schemas.dispositivos_usuario import DispositivoUsuarioResponse
from app.api.dependencies.auth import require_active_user



router = APIRouter(prefix="/dispositivos", tags=["Dispositivos Usuario"])


def get_service():
    return DispositivosUsuarioService()


@router.post("/token", response_model=DispositivoUsuarioResponse)
def save_token(
    payload: dict,
    request: Request,
    service: Annotated[DispositivosUsuarioService, Depends(get_service)] = None,
    supabase: Client = Depends(get_supabase_client),
    user=Depends(require_active_user),
):

    result = service.save_or_update_token(
        supabase=supabase,
        id_usuario=user.id_usuario,
        token=payload["token_dispositivo"],
        plataforma=payload.get("plataforma"),
    )

    return result