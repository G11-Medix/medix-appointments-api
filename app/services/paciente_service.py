from supabase import Client

from app.repositories.paciente_repository import PacienteRepository
from app.schemas.paciente import PacienteCreate, PacienteUpdate


class PacienteService:
    def __init__(self, repository: PacienteRepository | None = None) -> None:
        self.repository = repository or PacienteRepository()

    def list_pacientes(self, supabase: Client, limit: int = 20) -> list[dict]:
        return self.repository.list(supabase=supabase, limit=limit)

    def get_paciente(self, supabase: Client, id_paciente: int) -> dict | None:
        return self.repository.get_by_id(supabase=supabase, id_paciente=id_paciente)

    def create_paciente(
        self,
        supabase: Client,
        payload: PacienteCreate,
        authenticated_user_id: str | None = None,
    ) -> dict:
        create_data = payload.model_dump(mode="json")
        if authenticated_user_id is not None:
            create_data["id_usuario"] = authenticated_user_id
        return self.repository.create(supabase=supabase, payload=create_data)

    def update_paciente(
        self,
        supabase: Client,
        id_paciente: int,
        payload: PacienteUpdate,
        authenticated_user_id: str | None = None,
    ) -> dict | None:
        update_data = payload.model_dump(exclude_unset=True, mode="json")
        if authenticated_user_id is not None:
            update_data["id_usuario"] = authenticated_user_id
        if not update_data:
            return self.repository.get_by_id(supabase=supabase, id_paciente=id_paciente)

        self.repository.update(supabase=supabase, id_paciente=id_paciente, payload=update_data)
        return self.repository.get_by_id(supabase=supabase, id_paciente=id_paciente)

    def delete_paciente(self, supabase: Client, id_paciente: int) -> None:
        self.repository.delete(supabase=supabase, id_paciente=id_paciente)
