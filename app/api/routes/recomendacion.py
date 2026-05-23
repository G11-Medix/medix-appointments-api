from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from app.db.supabase import get_supabase_client
from app.schemas.recomendacion import RecomendacionCreate, RecomendacionResponse, RecomendacionUpdate
from app.services.recomendacion_service import RecomendacionService

router = APIRouter(prefix="/recomendaciones", tags=["Recomendaciones"])


def get_recomendacion_service() -> RecomendacionService:
    return RecomendacionService()


@router.get("/", response_model=list[RecomendacionResponse])
def list_recomendaciones(
    institucion_id: int | None = Query(default=None),
    especialidad_id: int | None = Query(default=None),
    activa: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: Annotated[RecomendacionService, Depends(get_recomendacion_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[RecomendacionResponse]:
    rows = service.list_recomendaciones(
        supabase=supabase,
        institucion_id=institucion_id,
        especialidad_id=especialidad_id,
        activa=activa,
        limit=limit,
    )
    return [RecomendacionResponse.model_validate(row) for row in rows]


@router.get("/{id_recomendacion}", response_model=RecomendacionResponse)
def get_recomendacion(
    id_recomendacion: int,
    service: Annotated[RecomendacionService, Depends(get_recomendacion_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> RecomendacionResponse:
    row = service.get_recomendacion(supabase=supabase, id_recomendacion=id_recomendacion)
    return RecomendacionResponse.model_validate(row)


@router.post("/", response_model=RecomendacionResponse, status_code=status.HTTP_201_CREATED)
def create_recomendacion(
    payload: RecomendacionCreate,
    service: Annotated[RecomendacionService, Depends(get_recomendacion_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> RecomendacionResponse:
    row = service.create_recomendacion(supabase=supabase, payload=payload)
    return RecomendacionResponse.model_validate(row)


@router.put("/{id_recomendacion}", response_model=RecomendacionResponse)
def update_recomendacion(
    id_recomendacion: int,
    payload: RecomendacionUpdate,
    service: Annotated[RecomendacionService, Depends(get_recomendacion_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> RecomendacionResponse:
    row = service.update_recomendacion(
        supabase=supabase,
        id_recomendacion=id_recomendacion,
        payload=payload,
    )
    return RecomendacionResponse.model_validate(row)


@router.delete("/{id_recomendacion}", response_model=RecomendacionResponse)
def delete_recomendacion(
    id_recomendacion: int,
    service: Annotated[RecomendacionService, Depends(get_recomendacion_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> RecomendacionResponse:
    row = service.delete_recomendacion(supabase=supabase, id_recomendacion=id_recomendacion)
    return RecomendacionResponse.model_validate(row)
