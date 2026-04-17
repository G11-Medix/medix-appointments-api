from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies.auth import get_access_token_from_state
from supabase import Client

from app.api.routes.assistant import get_assistant_service
from app.schemas.assistant import AssistantAvailabilityResponse, AssistantInstitutionResponse
from app.db.supabase import get_supabase_client
from app.schemas.especialidad import EspecialidadResponse
from app.schemas.institucion import InstitucionResponse
from app.services.assistant_appointments_service import AssistantAppointmentsService
from app.services.institucion_service import InstitucionService

router = APIRouter(prefix="/instituciones", tags=["Instituciones"])


def get_institucion_service() -> InstitucionService:
    return InstitucionService()


@router.get("/", response_model=list[InstitucionResponse] | list[AssistantInstitutionResponse])
def list_instituciones(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    codigo_reps: int | None = Query(default=None),
    service: Annotated[InstitucionService, Depends(get_institucion_service)] = None,
    assistant_service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[InstitucionResponse] | list[AssistantInstitutionResponse]:
    if codigo_reps is not None:
        return assistant_service.list_instituciones_by_especialidad(
            codigo_reps,
            access_token=get_access_token_from_state(request),
        )
    rows = service.list_instituciones(supabase=supabase, limit=limit)
    return [InstitucionResponse.model_validate(row) for row in rows]


@router.get("/{id_institucion}/disponibilidad", response_model=AssistantAvailabilityResponse)
def get_disponibilidad(
    request: Request,
    id_institucion: int,
    codigo_reps: int = Query(...),
    fecha_desde: date = Query(...),
    dias: int = Query(..., ge=1),
    assistant_service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
) -> AssistantAvailabilityResponse:
    return assistant_service.get_disponibilidad(
        id_institucion=id_institucion,
        codigo_reps=codigo_reps,
        fecha_desde=fecha_desde,
        dias=dias,
        access_token=get_access_token_from_state(request),
    )


@router.get("/{id_institucion}/especialidades", response_model=list[EspecialidadResponse])
def list_institucion_related_especialidades(
    id_institucion: int,
    service: Annotated[InstitucionService, Depends(get_institucion_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[EspecialidadResponse]:
    institucion = service.get_institucion(supabase=supabase, id_institucion=id_institucion)
    if not institucion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institucion no encontrada")

    rows = service.list_related_especialidades(supabase=supabase, id_institucion=id_institucion)
    return [EspecialidadResponse.model_validate(row) for row in rows]
