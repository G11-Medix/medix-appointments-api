from datetime import datetime

from fastapi import APIRouter, Query

from app.db.supabase import get_supabase_client
from app.schemas.cita import CitaAppResponse, CitaCreate, CitaDelete, CitaResponse, CitaUpdate
from app.services.cita_service import CitaService

router = APIRouter(prefix="/instituciones/{id_institucion}/citas", tags=["Citas"])
patient_router = APIRouter(prefix="/pacientes", tags=["Citas"])
cita_service = CitaService()
supabase = get_supabase_client()


@router.post("/", response_model=CitaResponse, status_code=201)
def create_cita(id_institucion: int, payload: CitaCreate) -> CitaResponse:
    row = cita_service.create_cita(id_institucion=id_institucion, payload=payload)
    return CitaResponse.model_validate(row)


@router.get("/{id_cita}", response_model=CitaResponse)
def get_cita(id_institucion: int, id_cita: int) -> CitaResponse:
    row = cita_service.get_cita(id_institucion=id_institucion, id_cita=id_cita)
    return CitaResponse.model_validate(row)


@router.get("/", response_model=list[CitaResponse])
def list_citas(
    id_institucion: int,
    id_paciente: int | None = Query(default=None),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
) -> list[CitaResponse]:
    rows = cita_service.list_citas(
        id_institucion=id_institucion,
        id_paciente=id_paciente,
        desde=desde,
        hasta=hasta,
    )
    return [CitaResponse.model_validate(row) for row in rows]


@router.put("/{id_cita}", response_model=CitaResponse)
def update_cita(id_institucion: int, id_cita: int, payload: CitaUpdate) -> CitaResponse:
    row = cita_service.update_cita(id_institucion=id_institucion, id_cita=id_cita, payload=payload)
    return CitaResponse.model_validate(row)


@router.delete("/{id_cita}", response_model=CitaResponse)
def delete_cita(id_institucion: int, id_cita: int, payload: CitaDelete) -> CitaResponse:
    row = cita_service.delete_cita(id_institucion=id_institucion, id_cita=id_cita, payload=payload)
    return CitaResponse.model_validate(row)


@patient_router.get("/{id_paciente}/citas", response_model=list[CitaAppResponse])
def get_all_citas_by_paciente(id_paciente: int) -> list[CitaAppResponse]:
    return cita_service.list_citas_app_by_paciente(
        supabase=supabase,
        id_paciente=id_paciente,
    )
