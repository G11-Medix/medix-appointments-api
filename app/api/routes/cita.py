from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.auth import get_access_token_from_state
from supabase import Client

from app.db.supabase import get_supabase_client
from app.schemas.cita import CitaAppResponse, CitaCreate, CitaDelete, CitaResponse, CitaUpdate
from app.services.cita_service import CitaService

router = APIRouter(prefix="/instituciones/{id_institucion}/citas", tags=["Citas"])
patient_router = APIRouter(prefix="/pacientes", tags=["Citas"])


def get_cita_service() -> CitaService:
    return CitaService()


@router.post("/", response_model=CitaResponse, status_code=201)
def create_cita(
    request: Request,
    id_institucion: int,
    payload: CitaCreate,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
) -> CitaResponse:
    row = service.create_cita(
        id_institucion=id_institucion,
        payload=payload,
        access_token=get_access_token_from_state(request),
    )
    return CitaResponse.model_validate(row)


@router.get("/{id_cita}", response_model=CitaResponse)
def get_cita(
    request: Request,
    id_institucion: int,
    id_cita: int,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
) -> CitaResponse:
    row = service.get_cita(
        id_institucion=id_institucion,
        id_cita=id_cita,
        access_token=get_access_token_from_state(request),
    )
    return CitaResponse.model_validate(row)


@router.get("/", response_model=list[CitaResponse])
def list_citas(
    request: Request,
    id_institucion: int,
    id_paciente: int | None = Query(default=None),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
) -> list[CitaResponse]:
    rows = service.list_citas(
        id_institucion=id_institucion,
        id_paciente=id_paciente,
        desde=desde,
        hasta=hasta,
        access_token=get_access_token_from_state(request),
    )
    return [CitaResponse.model_validate(row) for row in rows]


@router.put("/{id_cita}", response_model=CitaResponse)
def update_cita(
    request: Request,
    id_institucion: int,
    id_cita: int,
    payload: CitaUpdate,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
) -> CitaResponse:
    row = service.update_cita(
        id_institucion=id_institucion,
        id_cita=id_cita,
        payload=payload,
        access_token=get_access_token_from_state(request),
    )
    return CitaResponse.model_validate(row)


@router.delete("/{id_cita}", response_model=CitaResponse)
def delete_cita(
    request: Request,
    id_institucion: int,
    id_cita: int,
    payload: CitaDelete,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
) -> CitaResponse:
    row = service.delete_cita(
        id_institucion=id_institucion,
        id_cita=id_cita,
        payload=payload,
        access_token=get_access_token_from_state(request),
    )
    return CitaResponse.model_validate(row)


# @patient_router.get("/{id_paciente}/citas", response_model=list[CitaAppResponse])
# def get_all_citas_by_paciente(
#     id_paciente: int,
#     service: Annotated[CitaService, Depends(get_cita_service)] = None,
#     supabase: Client = Depends(get_supabase_client),
# ) -> list[CitaAppResponse]:
#     return service.list_citas_app_by_paciente(
#         supabase=supabase,
#         id_paciente=id_paciente,
#     )

@patient_router.get("/{id_paciente}/citas", response_model=list[CitaAppResponse])
def get_all_citas_by_paciente(
    request: Request,
    id_paciente: int,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[CitaAppResponse]:
    return service.list_citas_app_by_paciente_doc(
        supabase=supabase,
        id_paciente=id_paciente,
        access_token=get_access_token_from_state(request),
    )

