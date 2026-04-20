from supabase import Client
from app.repositories.especialidad_repository import EspecialidadRepository


class EspecialidadService:
    def __init__(self, repository: EspecialidadRepository | None = None) -> None:
        self.repository = repository or EspecialidadRepository()

    def list_especialidades(self, supabase: Client, limit: int = 50) -> list[dict]:
        return self.repository.list(supabase=supabase, limit=limit)