from supabase import Client


class ConsentimientoRepository:

    _select_documento_fields = (
        "id_documento,version,contenido,fecha_publicacion,estado"
    )

    _select_aceptacion_fields = (
        "id_aceptacion,id_usuario,id_documento,fecha_aceptacion,ip,dispositivo"
    )

    def get_documento_activo(self, supabase: Client) -> dict | None:
        response = (
            supabase.table("Documento_Legal")
            .select(self._select_documento_fields)
            .eq("estado", "ACTIVO")
            .order("fecha_publicacion", desc=True)
            .limit(1)
            .execute()
        )

        data = response.data or []
        return data[0] if data else None

    def exists_aceptacion(
        self,
        supabase: Client,
        user_id: str,
        id_documento: int,
    ) -> bool:
        response = (
            supabase.table("Aceptacion_Documento")
            .select("id_aceptacion")
            .eq("id_usuario", user_id)
            .eq("id_documento", id_documento)
            .limit(1)
            .execute()
        )

        return len(response.data or []) > 0

    def create_aceptacion(
        self,
        supabase: Client,
        payload: dict,
    ) -> dict:
        response = (
            supabase.table("Aceptacion_Documento")
            .insert(payload)
            .execute()
        )

        data = response.data or []
        return data[0] if data else {}

    def get_aceptaciones_by_user(
        self,
        supabase: Client,
        user_id: str,
    ) -> list[dict]:
        response = (
            supabase.table("Aceptacion_Documento")
            .select(self._select_aceptacion_fields)
            .eq("id_usuario", user_id)
            .order("fecha_aceptacion", desc=True)
            .execute()
        )

        return response.data or []
