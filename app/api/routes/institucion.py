from typing import Annotated

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.db.supabase import get_supabase_client
from app.schemas.institucion import InstitucionResponse
from app.services.institucion_service import InstitucionService

router = APIRouter(prefix="/instituciones", tags=["Instituciones"])


def get_institucion_service() -> InstitucionService:
    return InstitucionService()


@router.get("/", response_model=list[InstitucionResponse])
def list_instituciones(
    limit: int = Query(default=20, ge=1, le=100),
    service: Annotated[InstitucionService, Depends(get_institucion_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[InstitucionResponse]:
    rows = service.list_instituciones(supabase=supabase, limit=limit)
    return [InstitucionResponse.model_validate(row) for row in rows]
