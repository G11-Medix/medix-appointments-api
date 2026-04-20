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
from app.services.eps_service import EpsService
from app.services.institucion_service import InstitucionService
from app.services.paciente_service import PacienteService

router = APIRouter(prefix="/instituciones", tags=["Instituciones"])


def get_institucion_service() -> InstitucionService:
    return InstitucionService()


def get_eps_service() -> EpsService:
    return EpsService()


def get_paciente_service() -> PacienteService:
    return PacienteService()


@router.get("/", response_model=list[InstitucionResponse] | list[AssistantInstitutionResponse])
def list_instituciones(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    codigo_reps: int | None = Query(default=None),
    id_paciente: int | None = Query(default=None),
    service: Annotated[InstitucionService, Depends(get_institucion_service)] = None,
    eps_service: Annotated[EpsService, Depends(get_eps_service)] = None,
    paciente_service: Annotated[PacienteService, Depends(get_paciente_service)] = None,
    assistant_service: Annotated[AssistantAppointmentsService, Depends(get_assistant_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[InstitucionResponse] | list[AssistantInstitutionResponse]:
    if codigo_reps is not None:
        rows = assistant_service.list_instituciones_by_especialidad(
            codigo_reps,
            access_token=get_access_token_from_state(request),
        )
        if id_paciente is None:
            return rows

        paciente = paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
        if not paciente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
        id_eps = paciente.get("id_eps")
        if id_eps is None:
            return []

        related_instituciones = eps_service.list_related_ips(supabase=supabase, id_eps=int(id_eps))
        related_ids = {
            int(row["id_institucion"])
            for row in related_instituciones
            if row.get("id_institucion") is not None
        }
        return [
            row
            for row in rows
            if _get_institucion_id(row) in related_ids
        ]
    rows = service.list_instituciones(supabase=supabase, limit=limit)
    return [InstitucionResponse.model_validate(row) for row in rows]


def _get_institucion_id(row: AssistantInstitutionResponse | dict) -> int | None:
    if isinstance(row, dict):
        value = row.get("id_institucion")
    else:
        value = row.id_institucion
    return int(value) if value is not None else None


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
