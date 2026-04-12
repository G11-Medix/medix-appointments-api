from typing import Annotated

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.db.supabase import get_supabase_client
from app.schemas.eps import EpsResponse
from app.services.eps_service import EpsService

router = APIRouter(prefix="/eps", tags=["EPS"])


def get_eps_service() -> EpsService:
    return EpsService()


@router.get("/", response_model=list[EpsResponse])
def list_eps(
    limit: int = Query(default=20, ge=1, le=100),
    service: Annotated[EpsService, Depends(get_eps_service)] = None,
    supabase: Client = Depends(get_supabase_client),
) -> list[EpsResponse]:
    rows = service.list_eps(supabase=supabase, limit=limit)
    return [EpsResponse.model_validate(row) for row in rows]
