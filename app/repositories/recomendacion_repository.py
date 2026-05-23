from typing import Any

from supabase import Client


class RecomendacionRepository:
    TABLE = "recomendaciones_institucion"
    SELECT_FIELDS = "id,created_at,institucion_id,especialidad_id,codigo,recomendaciones,prioridad,activa"

    def list(
        self,
        supabase: Client,
        *,
        institucion_id: int | None = None,
        especialidad_id: int | None = None,
        activa: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = supabase.table(self.TABLE).select(self.SELECT_FIELDS)
        if institucion_id is not None:
            query = query.eq("institucion_id", institucion_id)
        if especialidad_id is not None:
            query = query.eq("especialidad_id", especialidad_id)
        if activa is not None:
            query = query.eq("activa", activa)
        response = (
            query
            .order("prioridad", desc=True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_by_id(self, supabase: Client, id_recomendacion: int) -> dict[str, Any] | None:
        response = (
            supabase.table(self.TABLE)
            .select(self.SELECT_FIELDS)
            .eq("id", id_recomendacion)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def get_active_for_context(
        self,
        supabase: Client,
        *,
        institucion_id: int,
        especialidad_id: int,
    ) -> dict[str, Any] | None:
        response = (
            supabase.table(self.TABLE)
            .select(self.SELECT_FIELDS)
            .eq("institucion_id", institucion_id)
            .eq("especialidad_id", especialidad_id)
            .eq("activa", True)
            .order("prioridad", desc=True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def create(self, supabase: Client, payload: dict[str, Any]) -> dict[str, Any]:
        response = (
            supabase.table(self.TABLE)
            .insert(payload)
            .execute()
        )
        data = response.data or []
        return data[0] if data else {}

    def update(self, supabase: Client, id_recomendacion: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = (
            supabase.table(self.TABLE)
            .update(payload)
            .eq("id", id_recomendacion)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def delete(self, supabase: Client, id_recomendacion: int) -> dict[str, Any] | None:
        response = (
            supabase.table(self.TABLE)
            .delete()
            .eq("id", id_recomendacion)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None
