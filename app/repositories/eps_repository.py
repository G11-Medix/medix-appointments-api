from supabase import Client


class EpsRepository:
    def list(self, supabase: Client, limit: int = 20) -> list[dict]:
        response = (
            supabase.table("EPS")
            .select("id_eps,nombre,codigo,estado")
            .order("id_eps")
            .limit(limit)
            .execute()
        )
        return response.data or []
