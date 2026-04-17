from typing import Annotated

from fastapi import APIRouter, Depends, Request
from supabase import Client

from app.api.dependencies.auth import get_access_token_from_state
from app.db.supabase import get_supabase_client
from app.schemas.assistant import (
    AssistantAppointmentActionResponse,
    AssistantCancelAppointmentRequest,
    AssistantRescheduleAppointmentRequest,
    AssistantScheduleAppointmentRequest,
)
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


@router.post("/citas/agendar", response_model=AssistantAppointmentActionResponse, status_code=201)
def schedule_appointment(
    request: Request,
    payload: AssistantScheduleAppointmentRequest,
    service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
) -> AssistantAppointmentActionResponse:
    return service.schedule_appointment(
        id_paciente=payload.id_paciente,
        id_institucion=payload.id_institucion,
        id_especialidad=payload.id_especialidad,
        fecha=payload.fecha,
        hora=payload.hora,
        access_token=get_access_token_from_state(request),
    )


@router.patch("/citas/{id_cita}/cancelar", response_model=AssistantAppointmentActionResponse)
def cancel_appointment(
    request: Request,
    id_cita: int,
    payload: AssistantCancelAppointmentRequest,
    service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
) -> AssistantAppointmentActionResponse:
    return service.cancel_appointment(
        id_cita=id_cita,
        id_institucion=payload.id_institucion,
        motivo=payload.motivo,
        access_token=get_access_token_from_state(request),
    )


@router.patch("/citas/{id_cita}/reprogramar", response_model=AssistantAppointmentActionResponse)
def reschedule_appointment(
    request: Request,
    id_cita: int,
    payload: AssistantRescheduleAppointmentRequest,
    service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
) -> AssistantAppointmentActionResponse:
    return service.reschedule_appointment(
        id_cita=id_cita,
        id_institucion=payload.id_institucion,
        id_especialidad=payload.id_especialidad,
        nueva_fecha=payload.nueva_fecha,
        nueva_hora=payload.nueva_hora,
        access_token=get_access_token_from_state(request),
    )
