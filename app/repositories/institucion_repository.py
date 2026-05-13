from __future__ import annotations

from postgrest.exceptions import APIError
from supabase import Client


class ServiceUrlColumnMissingError(Exception):
    pass


class InstitucionRepository:
    RELATION_TABLE = "Institucion_Especialidad"
    SELECT_FIELDS = "id_institucion,nombre,nit,direccion,telefono,estado,longitud,latitud,logo_url,service_url"
    LEGACY_SELECT_FIELDS = "id_institucion,nombre,nit,direccion,telefono,estado,longitud,latitud,logo_url"

    def list(self, supabase: Client, limit: int = 20) -> list[dict]:
        try:
            response = (
                supabase.table("Institucion")
                .select(self.SELECT_FIELDS)
                .order("id_institucion")
                .limit(limit)
                .execute()
            )
            return response.data or []
        except APIError as exc:
            if not _is_missing_service_url_error(exc):
                raise

        response = (
            supabase.table("Institucion")
            .select(self.LEGACY_SELECT_FIELDS)
            .order("id_institucion")
            .limit(limit)
            .execute()
        )
        return _with_missing_service_url(response.data or [])

    def get_by_id(self, supabase: Client, id_institucion: int) -> dict | None:
        try:
            response = (
                supabase.table("Institucion")
                .select(self.SELECT_FIELDS)
                .eq("id_institucion", id_institucion)
                .limit(1)
                .execute()
            )
        except APIError as exc:
            if not _is_missing_service_url_error(exc):
                raise
            response = (
                supabase.table("Institucion")
                .select(self.LEGACY_SELECT_FIELDS)
                .eq("id_institucion", id_institucion)
                .limit(1)
                .execute()
            )
        data = response.data or []
        return _with_missing_service_url(data)[0] if data else None

    def update(self, supabase: Client, id_institucion: int, payload: dict) -> dict | None:
        try:
            supabase.table("Institucion").update(payload).eq("id_institucion", id_institucion).execute()
        except APIError as exc:
            if "service_url" in payload and _is_missing_service_url_error(exc):
                raise ServiceUrlColumnMissingError from exc
            raise
        return self.get_by_id(supabase=supabase, id_institucion=id_institucion)

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


def _with_missing_service_url(rows: list[dict]) -> list[dict]:
    return [{**row, "service_url": row.get("service_url")} for row in rows]


def _is_missing_service_url_error(error: APIError) -> bool:
    error_text = str(error)
    return "service_url" in error_text and ("42703" in error_text or "does not exist" in error_text)
