from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from supabase import Client

from app.api.dependencies.auth import (
    AuthenticatedTokenContext,
    AuthenticatedUserContext,
    get_authenticated_user_from_state,
    require_authenticated_token_user,
)
from app.db.supabase import get_supabase_client
from app.schemas.paciente import PacienteCreate, PacienteResponse, PacienteUpdate, UserProfileResponse
from app.services.paciente_service import PacienteService

protected_router = APIRouter(prefix="/pacientes", tags=["Pacientes"])
registration_router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


def get_paciente_service() -> PacienteService:
    return PacienteService()


@protected_router.get("/", response_model=list[PacienteResponse])
def list_pacientes(
    limit: int = Query(default=20, ge=1, le=100),
    service: Annotated[PacienteService, Depends(get_paciente_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[PacienteResponse]:
    rows = service.list_pacientes(supabase=supabase, limit=limit)
    return [PacienteResponse.model_validate(row) for row in rows]


@protected_router.get("/{id_paciente}", response_model=PacienteResponse)
def get_paciente(
    id_paciente: int,
    service: Annotated[PacienteService, Depends(get_paciente_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> PacienteResponse:
    row = service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return PacienteResponse.model_validate(row)


@protected_router.get("/{id_paciente}/profile", response_model=UserProfileResponse)
def get_paciente_profile(
    id_paciente: int,
    service: Annotated[PacienteService, Depends(get_paciente_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> UserProfileResponse:
    profile = service.get_user_profile(
        supabase=supabase,
        id_paciente=id_paciente,
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return profile


@registration_router.post("/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def create_paciente(
    payload: PacienteCreate,
    auth_user: AuthenticatedTokenContext = Depends(require_authenticated_token_user),
    service: Annotated[PacienteService, Depends(get_paciente_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> PacienteResponse:
    row = service.create_paciente(
        supabase=supabase,
        payload=payload,
        authenticated_user_id=str(auth_user.id_usuario),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear el paciente")
    return PacienteResponse.model_validate(row)


@protected_router.put("/{id_paciente}", response_model=PacienteResponse)
def update_paciente(
    id_paciente: int,
    payload: PacienteUpdate,
    auth_user: AuthenticatedUserContext = Depends(get_authenticated_user_from_state),
    service: Annotated[PacienteService, Depends(get_paciente_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> PacienteResponse:
    existing = service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    row = service.update_paciente(
        supabase=supabase,
        id_paciente=id_paciente,
        payload=payload,
        authenticated_user_id=str(auth_user.id_usuario),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar el paciente")
    return PacienteResponse.model_validate(row)


@protected_router.delete("/{id_paciente}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paciente(
    id_paciente: int,
    service: Annotated[PacienteService, Depends(get_paciente_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> Response:
    existing = service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    service.delete_paciente(supabase=supabase, id_paciente=id_paciente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
