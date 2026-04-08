from supabase import Client
from app.repositories.eps_repository import EPSRepository


class EPSService:
    def __init__(self, repository: EPSRepository | None = None) -> None:
        self.repository = repository or EPSRepository()

    def get_eps_nombre(self, supabase: Client, id_eps: int) -> str:
        eps = self.repository.get_by_id(supabase, id_eps)
        return eps["nombre"] if eps else "Sin EPS"