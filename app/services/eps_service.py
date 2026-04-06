from supabase import Client

from app.repositories.eps_repository import EpsRepository


class EpsService:
    def __init__(self, repository: EpsRepository | None = None) -> None:
        self.repository = repository or EpsRepository()

    def list_eps(self, supabase: Client, limit: int = 20) -> list[dict]:
        return self.repository.list(supabase=supabase, limit=limit)
