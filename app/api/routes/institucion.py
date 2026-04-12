from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.api.routes.assistant import get_assistant_service
from app.schemas.assistant import AssistantAvailabilityResponse, AssistantInstitutionResponse
from app.db.supabase import get_supabase_client
from app.schemas.institucion import InstitucionResponse
from app.services.assistant_appointments_service import AssistantAppointmentsService
from app.services.institucion_service import InstitucionService

router = APIRouter(prefix="/instituciones", tags=["Instituciones"])


def get_institucion_service() -> InstitucionService:
    return InstitucionService()


@router.get("/", response_model=list[InstitucionResponse] | list[AssistantInstitutionResponse])
def list_instituciones(
    limit: int = Query(default=20, ge=1, le=100),
    id_especialidad: int | None = Query(default=None),
    service: Annotated[InstitucionService, Depends(get_institucion_service)] = None,
    assistant_service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[InstitucionResponse] | list[AssistantInstitutionResponse]:
    if id_especialidad is not None:
        return assistant_service.list_instituciones_by_especialidad(id_especialidad)
    rows = service.list_instituciones(supabase=supabase, limit=limit)
    return [InstitucionResponse.model_validate(row) for row in rows]


@router.get("/{id_institucion}/disponibilidad", response_model=AssistantAvailabilityResponse)
def get_disponibilidad(
    id_institucion: int,
    id_especialidad: int = Query(...),
    fecha_desde: date = Query(...),
    dias: int = Query(..., ge=1),
    assistant_service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
) -> AssistantAvailabilityResponse:
    return assistant_service.get_disponibilidad(
        id_institucion=id_institucion,
        id_especialidad=id_especialidad,
        fecha_desde=fecha_desde,
        dias=dias,
    )
