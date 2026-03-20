from fastapi import APIRouter, HTTPException, Query, Response, status

from app.db.supabase import get_supabase_client
from app.schemas.paciente import PacienteCreate, PacienteResponse, PacienteUpdate
from app.services.paciente_service import PacienteService

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])
paciente_service = PacienteService()
supabase = get_supabase_client()


@router.get("/", response_model=list[PacienteResponse])
def list_pacientes(limit: int = Query(default=20, ge=1, le=100)) -> list[PacienteResponse]:
    rows = paciente_service.list_pacientes(supabase=supabase, limit=limit)
    return [PacienteResponse.model_validate(row) for row in rows]


@router.get("/{id_paciente}", response_model=PacienteResponse)
def get_paciente(id_paciente: int) -> PacienteResponse:
    row = paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return PacienteResponse.model_validate(row)


@router.post("/", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def create_paciente(payload: PacienteCreate) -> PacienteResponse:
    row = paciente_service.create_paciente(supabase=supabase, payload=payload)
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear el paciente")
    return PacienteResponse.model_validate(row)


@router.put("/{id_paciente}", response_model=PacienteResponse)
def update_paciente(id_paciente: int, payload: PacienteUpdate) -> PacienteResponse:
    existing = paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    row = paciente_service.update_paciente(supabase=supabase, id_paciente=id_paciente, payload=payload)
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar el paciente")
    return PacienteResponse.model_validate(row)


@router.delete("/{id_paciente}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paciente(id_paciente: int) -> Response:
    existing = paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    paciente_service.delete_paciente(supabase=supabase, id_paciente=id_paciente)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
