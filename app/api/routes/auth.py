from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.api.dependencies.auth import AuthenticatedUserContext, require_active_admin_user
from app.db.supabase import get_supabase_admin_client, get_supabase_client
from app.schemas.auth import (
    GrantPatientAccessRequest,
    GrantPatientAccessResponse,
    PhoneEligibilityResponse,
)
from app.services.auth_access_service import AuthAccessService

public_router = APIRouter(prefix="/auth", tags=["Auth"])
admin_router = APIRouter(prefix="/admin/pacientes", tags=["Admin Pacientes"])


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


@admin_router.post("/{id_paciente}/grant-access", response_model=GrantPatientAccessResponse)
def grant_patient_access(
    id_paciente: int,
    payload: GrantPatientAccessRequest,
    _auth_user: AuthenticatedUserContext = Depends(require_active_admin_user),
    service: Annotated[AuthAccessService, Depends(get_auth_access_service)] = None,
    supabase: Client = Depends(get_supabase_client),
    admin_supabase: Client = Depends(get_supabase_admin_client),
) -> GrantPatientAccessResponse:
    row = service.grant_patient_access(
        supabase=supabase,
        admin_supabase=admin_supabase,
        id_paciente=id_paciente,
        telefono=payload.telefono,
        rol=payload.rol,
    )
    return GrantPatientAccessResponse.model_validate(row)
