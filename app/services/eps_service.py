from supabase import Client

from app.repositories.eps_repository import EpsRepository


class EpsService:
    def __init__(self, repository: EpsRepository | None = None) -> None:
        self.repository = repository or EpsRepository()

    def list_eps(self, supabase: Client, limit: int = 20) -> list[dict]:
        return self.repository.list(supabase=supabase, limit=limit)

    def get_eps(self, supabase: Client, id_eps: int) -> dict | None:
        return self.repository.get_by_id(supabase=supabase, id_eps=id_eps)

    def list_related_ips(self, supabase: Client, id_eps: int) -> list[dict]:
        return self.repository.list_related_instituciones(supabase=supabase, id_eps=id_eps)
