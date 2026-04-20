from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.db.supabase import get_supabase_client
from app.schemas.especialidad import EspecialidadResponse
from app.services.assistant_appointments_service import AssistantAppointmentsService
from app.services.especialidad_service import EspecialidadService

router = APIRouter(tags=["Assistant"])


def get_assistant_service() -> AssistantAppointmentsService:
    return AssistantAppointmentsService()


def get_especialidad_service() -> EspecialidadService:
    return EspecialidadService()


@router.get("/especialidades", response_model=list[EspecialidadResponse])
def list_specialties(
    service: Annotated[EspecialidadService, Depends(get_especialidad_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[EspecialidadResponse]:
    rows = service.list_especialidades(supabase=supabase)
    return [EspecialidadResponse.model_validate(row) for row in rows]
