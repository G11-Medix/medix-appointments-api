from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.auth import get_access_token_from_state
from supabase import Client

from app.db.supabase import get_supabase_client
from app.schemas.cita import CitaAppResponse, CitaConfirmacionResponse, CitaCreate, CitaDelete, CitaIpsResponse, CitaResponse, CitaUpdate
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
    supabase: Client = Depends(get_supabase_client),
) -> CitaResponse:
    row = service.create_cita( 
        id_institucion=id_institucion,
        payload=payload,
        access_token=get_access_token_from_state(request),
        supabase=supabase,
    )
    return CitaResponse.model_validate(row)


@router.get("/{id_cita}", response_model=CitaIpsResponse)
def get_cita(
    request: Request,
    id_institucion: int,
    id_cita: int,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> CitaIpsResponse:
    return service.get_cita_ips(
        supabase=supabase,
        id_institucion=id_institucion,
        id_cita=id_cita,
        access_token=get_access_token_from_state(request),
    )


@router.get("/{id_cita}/confirmacion", response_model=CitaConfirmacionResponse)
def get_cita_confirmacion(
    request: Request,
    id_institucion: int,
    id_cita: int,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> CitaConfirmacionResponse:
    row = service.get_cita_confirmacion(
        supabase=supabase,
        id_institucion=id_institucion,
        id_cita=id_cita,
        access_token=get_access_token_from_state(request),
    )
    return CitaConfirmacionResponse.model_validate(row)


@router.get("/", response_model=list[CitaIpsResponse])
def list_citas(
    request: Request,
    id_institucion: int,
    tipo_documento: str | None = Query(default=None, min_length=1),
    cedula: str | None = Query(default=None, min_length=1),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[CitaIpsResponse]:
    return service.list_citas_ips(
        supabase=supabase,
        id_institucion=id_institucion,
        tipo_documento=tipo_documento,
        cedula=cedula,
        desde=desde,
        hasta=hasta,
        access_token=get_access_token_from_state(request),
    )


@router.put("/{id_cita}", response_model=CitaResponse)
def update_cita(
    request: Request,
    id_institucion: int,
    id_cita: int,
    payload: CitaUpdate,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> CitaResponse:
    row = service.update_cita(
        id_institucion=id_institucion,
        id_cita=id_cita,
        payload=payload,
        access_token=get_access_token_from_state(request),
        supabase=supabase,
    )
    return CitaResponse.model_validate(row)


@router.delete("/{id_cita}", response_model=CitaResponse)
def delete_cita(
    request: Request,
    id_institucion: int,
    id_cita: int,
    payload: CitaDelete,
    service: Annotated[CitaService, Depends(get_cita_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> CitaResponse:
    row = service.delete_cita( 
        id_institucion=id_institucion,
        id_cita=id_cita,
        payload=payload,
        access_token=get_access_token_from_state(request),
        supabase=supabase,
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
