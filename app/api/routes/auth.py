from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.db.supabase import get_supabase_admin_client, get_supabase_client
from app.schemas.auth import PhoneEligibilityResponse
from app.services.auth_access_service import AuthAccessService

public_router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_access_service() -> AuthAccessService:
    return AuthAccessService()


@public_router.get("/eligibility/{telefono}", response_model=PhoneEligibilityResponse)
def get_phone_login_eligibility(
    telefono: str,
    service: Annotated[AuthAccessService, Depends(get_auth_access_service)] = None,
    supabase: Client = Depends(get_supabase_client),
    admin_supabase: Client = Depends(get_supabase_admin_client),
) -> PhoneEligibilityResponse:
    return service.check_phone_login_eligibility(
        supabase=supabase,
        admin_supabase=admin_supabase,
        telefono=telefono,
    )
