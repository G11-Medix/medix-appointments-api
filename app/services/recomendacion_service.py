from typing import Any

from fastapi import HTTPException, status
from supabase import Client

from app.repositories.recomendacion_repository import RecomendacionRepository
from app.schemas.recomendacion import RecomendacionCreate, RecomendacionUpdate


class RecomendacionService:
    def __init__(self, repository: RecomendacionRepository | None = None) -> None:
        self.repository = repository or RecomendacionRepository()

    def list_recomendaciones(
        self,
        supabase: Client,
        *,
        institucion_id: int | None = None,
        especialidad_id: int | None = None,
        activa: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self.repository.list(
            supabase=supabase,
            institucion_id=institucion_id,
            especialidad_id=especialidad_id,
            activa=activa,
            limit=limit,
        )

    def get_recomendacion(self, supabase: Client, id_recomendacion: int) -> dict[str, Any]:
        row = self.repository.get_by_id(supabase=supabase, id_recomendacion=id_recomendacion)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recomendacion no encontrada")
        return row

    def get_active_for_context(
        self,
        supabase: Client,
        *,
        institucion_id: int,
        especialidad_id: int,
    ) -> dict[str, Any] | None:
        return self.repository.get_active_for_context(
            supabase=supabase,
            institucion_id=institucion_id,
            especialidad_id=especialidad_id,
        )

    def create_recomendacion(self, supabase: Client, payload: RecomendacionCreate) -> dict[str, Any]:
        return self.repository.create(
            supabase=supabase,
            payload=payload.model_dump(),
        )

    def update_recomendacion(
        self,
        supabase: Client,
        id_recomendacion: int,
        payload: RecomendacionUpdate,
    ) -> dict[str, Any]:
        update_payload = payload.model_dump(exclude_unset=True)
        if not update_payload:
            return self.get_recomendacion(supabase=supabase, id_recomendacion=id_recomendacion)
        row = self.repository.update(
            supabase=supabase,
            id_recomendacion=id_recomendacion,
            payload=update_payload,
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recomendacion no encontrada")
        return row

    def delete_recomendacion(self, supabase: Client, id_recomendacion: int) -> dict[str, Any]:
        row = self.repository.delete(supabase=supabase, id_recomendacion=id_recomendacion)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recomendacion no encontrada")
        return row
