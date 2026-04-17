from supabase import Client

from app.repositories.institucion_repository import InstitucionRepository


class InstitucionService:
    def __init__(self, repository: InstitucionRepository | None = None) -> None:
        self.repository = repository or InstitucionRepository()

    def list_instituciones(self, supabase: Client, limit: int = 20) -> list[dict]:
        return self.repository.list(supabase=supabase, limit=limit)

    def get_institucion(self, supabase: Client, id_institucion: int) -> dict | None:
        return self.repository.get_by_id(supabase=supabase, id_institucion=id_institucion)

    def list_related_especialidades(self, supabase: Client, id_institucion: int) -> list[dict]:
        return self.repository.list_related_especialidades(supabase=supabase, id_institucion=id_institucion)
