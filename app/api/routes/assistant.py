from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.assistant import (
    AssistantAppointmentActionResponse,
    AssistantCancelAppointmentRequest,
    AssistantRescheduleAppointmentRequest,
    AssistantScheduleAppointmentRequest,
    AssistantSpecialtyResponse,
)
from app.services.assistant_appointments_service import AssistantAppointmentsService

router = APIRouter(tags=["Assistant"])


def get_assistant_service() -> AssistantAppointmentsService:
    return AssistantAppointmentsService()


@router.get("/especialidades", response_model=list[AssistantSpecialtyResponse])
def list_specialties(
    service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
) -> list[AssistantSpecialtyResponse]:
    return service.list_specialties()


@router.post("/citas/agendar", response_model=AssistantAppointmentActionResponse, status_code=201)
def schedule_appointment(
    payload: AssistantScheduleAppointmentRequest,
    service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
) -> AssistantAppointmentActionResponse:
    return service.schedule_appointment(
        id_paciente=payload.id_paciente,
        id_institucion=payload.id_institucion,
        id_especialidad=payload.id_especialidad,
        fecha=payload.fecha,
        hora=payload.hora,
    )


@router.patch("/citas/{id_cita}/cancelar", response_model=AssistantAppointmentActionResponse)
def cancel_appointment(
    id_cita: int,
    payload: AssistantCancelAppointmentRequest,
    service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
) -> AssistantAppointmentActionResponse:
    return service.cancel_appointment(
        id_cita=id_cita,
        id_institucion=payload.id_institucion,
        motivo=payload.motivo,
    )


@router.patch("/citas/{id_cita}/reprogramar", response_model=AssistantAppointmentActionResponse)
def reschedule_appointment(
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
    )
