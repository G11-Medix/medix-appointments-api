from supabase import Client

from app.repositories.auth_access_repository import AuthAccessRepository
from app.repositories.paciente_repository import PacienteRepository
from app.schemas.paciente import PacienteCreate, PacienteUpdate, UserProfileDto



class PacienteService:
    def __init__(
        self,
        repository: PacienteRepository | None = None,
        auth_access_repository: AuthAccessRepository | None = None,
    ) -> None:
        self.repository = repository or PacienteRepository()
        self.auth_access_repository = auth_access_repository or AuthAccessRepository()

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
            self._ensure_usuario_active(supabase=supabase, user_id=authenticated_user_id)
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

    def get_user_profile(
        self,
        supabase: Client,
        id_paciente: int,
    ) -> UserProfileDto | None:

        row = self.repository.get_user_profile(supabase, id_paciente)

        if not row:
            return None

        return UserProfileDto(
            nombres=row["nombres"],
            apellidos=row["apellidos"],
            documento=row["numero_documento"],
            eps=row["EPS"]["nombre"] if row.get("EPS") else "Sin EPS",
            correo=row.get("correo") or "",
            telefono=row.get("telefono") or "",
            correoVerificado=True,
            telefonoVerificado=True,
        )
    def _ensure_usuario_active(self, supabase: Client, user_id: str) -> dict | None:
        usuario = self.auth_access_repository.get_usuario_by_id(supabase=supabase, id_usuario=user_id)
        rol = str((usuario or {}).get("rol") or "PACIENTE").upper()
        payload = {"rol": rol, "estado": "ACTIVO"}
        if usuario:
            return self.auth_access_repository.update_usuario(
                supabase=supabase,
                id_usuario=user_id,
                payload=payload,
            )

        payload["id_usuario"] = user_id
        return self.auth_access_repository.create_usuario(supabase=supabase, payload=payload)
