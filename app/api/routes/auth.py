from fastapi import APIRouter, Depends

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
auth_access_service = AuthAccessService()
supabase = get_supabase_client()
admin_supabase = get_supabase_admin_client()


@public_router.get("/eligibility/{telefono}", response_model=PhoneEligibilityResponse)
def get_phone_login_eligibility(telefono: str) -> PhoneEligibilityResponse:
    return auth_access_service.check_phone_login_eligibility(
        supabase=supabase,
        admin_supabase=admin_supabase,
        telefono=telefono,
    )


@admin_router.post("/{id_paciente}/grant-access", response_model=GrantPatientAccessResponse)
def grant_patient_access(
    id_paciente: int,
    payload: GrantPatientAccessRequest,
    _auth_user: AuthenticatedUserContext = Depends(require_active_admin_user),
) -> GrantPatientAccessResponse:
    row = auth_access_service.grant_patient_access(
        supabase=supabase,
        admin_supabase=admin_supabase,
        id_paciente=id_paciente,
        telefono=payload.telefono,
        rol=payload.rol,
    )
    return GrantPatientAccessResponse.model_validate(row)
