from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from supabase import Client

from app.api.dependencies.auth import require_authenticated_token_user
from app.db.supabase import get_supabase_client
from app.schemas.consentimiento import (
    AceptacionRequest,
    ConsentStatusResponse,
    DocumentoLegalResponse,
)
from app.services.consentimiento_service import ConsentimientoService

router = APIRouter(prefix="/aceptacion-documento", tags=["Consentimiento"])


def get_consent_service() -> ConsentimientoService:
    return ConsentimientoService()


# 🔹 1. Obtener documento activo
@router.get("/activo", response_model=DocumentoLegalResponse)
def get_documento_activo(
    service: Annotated[ConsentimientoService, Depends(get_consent_service)],
    supabase: Client = Depends(get_supabase_client),
):
    doc = service.get_documento_activo(supabase)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


# 🔹 2. Verificar si aceptó
@router.get("/estado", response_model=ConsentStatusResponse)
def has_accepted(
    auth_user=Depends(require_authenticated_token_user),
    service: Annotated[ConsentimientoService, Depends(get_consent_service)] = None,
    supabase: Client = Depends(get_supabase_client),
):
    accepted = service.has_accepted_latest(
        supabase=supabase,
        user_id=str(auth_user.id_usuario),
    )
    return {"accepted": accepted}


@router.post("", status_code=status.HTTP_201_CREATED)
def aceptar_documento(
    payload: AceptacionRequest,
    request: Request,
    auth_user=Depends(require_authenticated_token_user),
    service: Annotated[ConsentimientoService, Depends(get_consent_service)] = None,
    supabase: Client = Depends(get_supabase_client),
):
    user_id = str(auth_user.id_usuario)

    success = service.aceptar_documento(
        supabase=supabase,
        user_id=user_id,
        payload=payload,  # ✅ pasas el objeto completo
        ip=request.client.host if request.client else None,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="No se pudo registrar la aceptación",
        )

    return {"message": "Aceptación registrada"}