from supabase import Client

from app.repositories.institucion_repository import InstitucionRepository


class InstitucionService:
    def __init__(self, repository: InstitucionRepository | None = None) -> None:
        self.repository = repository or InstitucionRepository()

    def list_instituciones(self, supabase: Client, limit: int = 20) -> list[dict]:
        return self.repository.list(supabase=supabase, limit=limit)
