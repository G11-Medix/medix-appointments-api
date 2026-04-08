from supabase import Client


class EspecialidadRepository:
    def list(self, supabase: Client, limit: int = 50) -> list[dict]:
        response = (
            supabase.table("Especialidad")
            .select("id_especialidad,nombre")
            .order("id_especialidad")
            .limit(limit)
            .execute()
        )
        return response.data or []
    