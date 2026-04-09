from fastapi import APIRouter, Query

from app.db.supabase import get_supabase_client
from app.schemas.eps import EpsResponse
from app.services.eps_service import EpsService

router = APIRouter(prefix="/eps", tags=["EPS"])
eps_service = EpsService()
supabase = get_supabase_client()


@router.get("/", response_model=list[EpsResponse])
def list_eps(limit: int = Query(default=20, ge=1, le=100)) -> list[EpsResponse]:
    rows = eps_service.list_eps(supabase=supabase, limit=limit)
    return [EpsResponse.model_validate(row) for row in rows]
