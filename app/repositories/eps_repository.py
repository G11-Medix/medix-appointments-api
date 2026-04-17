from __future__ import annotations

from supabase import Client


class EpsRepository:
    RELATION_TABLE = "Institucion_EPS"

    def list(self, supabase: Client, limit: int = 20) -> list[dict]:
        response = (
            supabase.table("EPS")
            .select("id_eps,nombre,codigo,estado")
            .order("id_eps")
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_by_id(self, supabase: Client, id_eps: int) -> dict | None:
        response = (
            supabase.table("EPS")
            .select("id_eps,nombre,codigo,estado")
            .eq("id_eps", id_eps)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def list_related_instituciones(self, supabase: Client, id_eps: int) -> list[dict]:
        response = (
            supabase.table(self.RELATION_TABLE)
            .select("id_institucion")
            .eq("id_eps", id_eps)
            .execute()
        )
        relation_rows = response.data or []

        institucion_ids = [
            row["id_institucion"]
            for row in relation_rows
            if row.get("id_institucion") is not None
        ]
        if not institucion_ids:
            return []

        response = (
            supabase.table("Institucion")
            .select("id_institucion,nombre,nit,direccion,telefono,estado,longitud,latitud,logo_url")
            .in_("id_institucion", institucion_ids)
            .order("id_institucion")
            .execute()
        )
        return response.data or []
