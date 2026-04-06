from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies.auth import (
    AuthenticatedTokenContext,
    AuthenticatedUserContext,
    get_authenticated_user_from_state,
    require_authenticated_token_user,
)
from app.db.supabase import get_supabase_client
from app.schemas.paciente import PacienteCreate, PacienteResponse, PacienteUpdate
from app.services.paciente_service import PacienteService

protected_router = APIRouter(prefix="/pacientes", tags=["Pacientes"])
registration_router = APIRouter(prefix="/pacientes", tags=["Pacientes"])
paciente_service = PacienteService()
supabase = get_supabase_client()


@protected_router.get("/", response_model=list[PacienteResponse])
def list_pacientes(limit: int = Query(default=20, ge=1, le=100)) -> list[PacienteResponse]:
    rows = paciente_service.list_pacientes(supabase=supabase, limit=limit)
    return [PacienteResponse.model_validate(row) for row in rows]


@protected_router.get("/{id_paciente}", response_model=PacienteResponse)
def get_paciente(id_paciente: int) -> PacienteResponse:
    row = paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return PacienteResponse.model_validate(row)


@registration_router.post("/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def create_paciente(
    payload: PacienteCreate,
    auth_user: AuthenticatedTokenContext = Depends(require_authenticated_token_user),
) -> PacienteResponse:
    row = paciente_service.create_paciente(
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
) -> PacienteResponse:
    existing = paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    row = paciente_service.update_paciente(
        supabase=supabase,
        id_paciente=id_paciente,
        payload=payload,
        authenticated_user_id=str(auth_user.id_usuario),
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar el paciente")
    return PacienteResponse.model_validate(row)


@protected_router.delete("/{id_paciente}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paciente(id_paciente: int) -> Response:
    existing = paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    paciente_service.delete_paciente(supabase=supabase, id_paciente=id_paciente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
