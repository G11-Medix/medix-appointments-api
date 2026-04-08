from supabase import Client


class EPSRepository:
    def get_by_id(self, supabase: Client, id_eps: int) -> dict | None:
        response = (
            supabase.table("EPS")
            .select("id_eps,nombre")
            .eq("id_eps", id_eps)
            .limit(1)
            .execute()
        )

        data = response.data or []
        return data[0] if data else None