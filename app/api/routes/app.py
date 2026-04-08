from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.db.supabase import get_supabase_client
from app.schemas.cita import CitaAppResponse
from app.services.cita_service import CitaService

from app.schemas.paciente import PacienteCreate, PacienteResponse, PacienteUpdate, UserProfileDto
from app.services.paciente_service import PacienteService

router = APIRouter(prefix="/app", tags=["Citas"])
cita_service = CitaService()
paciente_service = PacienteService()
supabase = get_supabase_client()


@router.get("/citas/{id_paciente}", response_model=list[CitaAppResponse])
def get_all_citas_by_paciente(
    id_paciente: int
):
    return cita_service.list_citas_app_by_paciente(
        supabase=supabase,
        id_paciente=id_paciente
    )

@router.get("/profile/{id_paciente}", response_model=UserProfileDto)
def get_paciente(
    id_paciente: int
):
    profile = paciente_service.get_user_profile(
        supabase=supabase,
        id_paciente=id_paciente
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )

    return profile

