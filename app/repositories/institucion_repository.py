from __future__ import annotations

from supabase import Client


class InstitucionRepository:
    RELATION_TABLE = "Institucion_Especialidad"

    def list(self, supabase: Client, limit: int = 20) -> list[dict]:
        response = (
            supabase.table("Institucion")
            .select("id_institucion,nombre,nit,direccion,telefono,estado,longitud,latitud,logo_url")
            .order("id_institucion")
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_by_id(self, supabase: Client, id_institucion: int) -> dict | None:
        response = (
            supabase.table("Institucion")
            .select("id_institucion,nombre,nit,direccion,telefono,estado,longitud,latitud,logo_url")
            .eq("id_institucion", id_institucion)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def list_related_especialidades(self, supabase: Client, id_institucion: int) -> list[dict]:
        response = (
            supabase.table(self.RELATION_TABLE)
            .select("id_especialidad")
            .eq("id_institucion", id_institucion)
            .execute()
        )
        relation_rows = response.data or []

        especialidad_ids = [
            row["id_especialidad"]
            for row in relation_rows
            if row.get("id_especialidad") is not None
        ]
        if not especialidad_ids:
            return []

        response = (
            supabase.table("Especialidad")
            .select("id_especialidad,nombre,codigo_reps")
            .in_("id_especialidad", especialidad_ids)
            .order("id_especialidad")
            .execute()
        )
        return response.data or []
