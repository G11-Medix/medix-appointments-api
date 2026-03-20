from fastapi import APIRouter, Query

from app.db.supabase import get_supabase_client
from app.schemas.institucion import InstitucionResponse
from app.services.institucion_service import InstitucionService

router = APIRouter(prefix="/instituciones", tags=["Instituciones"])
institucion_service = InstitucionService()
supabase = get_supabase_client()


@router.get("/", response_model=list[InstitucionResponse])
def list_instituciones(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[InstitucionResponse]:
    rows = institucion_service.list_instituciones(supabase=supabase, limit=limit)
    return [InstitucionResponse.model_validate(row) for row in rows]
