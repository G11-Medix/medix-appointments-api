from supabase import Client


class InstitucionRepository:
    def list(self, supabase: Client, limit: int = 20) -> list[dict]:
        response = (
            supabase.table("Institucion")
            .select("id_institucion,nombre,nit,direccion,telefono,estado")
            .order("id_institucion")
            .limit(limit)
            .execute()
        )
        return response.data or []
