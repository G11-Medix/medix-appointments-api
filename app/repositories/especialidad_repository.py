from supabase import Client


class EspecialidadRepository:
    def list(self, supabase: Client, limit: int = 50) -> list[dict]:
        response = (
            supabase.table("Especialidad")
            .select("id_especialidad,nombre,codigo_reps")
            .order("id_especialidad")
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_by_codigo_reps(self, supabase: Client, codigo_reps: int) -> dict | None:
        response = (
            supabase.table("Especialidad")
            .select("id_especialidad,nombre,codigo_reps")
            .eq("codigo_reps", codigo_reps)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None
    
