from time import perf_counter

import httpx
from fastapi import HTTPException, status
from supabase import Client

from app.core.config import Settings, get_settings
from app.repositories.institucion_repository import (
    InstitucionRepository,
    ServiceUrlColumnMissingError,
)
from app.schemas.institucion import InstitucionHealthResponse, InstitucionUpdate


class InstitucionService:
    def __init__(
        self,
        repository: InstitucionRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository or InstitucionRepository()
        self.settings = settings

    def list_instituciones(self, supabase: Client, limit: int = 20) -> list[dict]:
        return self.repository.list(supabase=supabase, limit=limit)

    def get_institucion(self, supabase: Client, id_institucion: int) -> dict | None:
        return self.repository.get_by_id(supabase=supabase, id_institucion=id_institucion)

    def update_institucion(
        self,
        supabase: Client,
        id_institucion: int,
        payload: InstitucionUpdate,
    ) -> dict | None:
        update_data = payload.model_dump(exclude_unset=True)
        try:
            return self.repository.update(
                supabase=supabase,
                id_institucion=id_institucion,
                payload=update_data,
            )
        except ServiceUrlColumnMissingError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La columna Institucion.service_url no existe. Aplica la migracion antes de guardar la URL del servicio.",
            ) from exc

    def list_related_especialidades(self, supabase: Client, id_institucion: int) -> list[dict]:
        return self.repository.list_related_especialidades(supabase=supabase, id_institucion=id_institucion)

    def check_health(self, supabase: Client, id_institucion: int) -> InstitucionHealthResponse | None:
        institucion = self.get_institucion(supabase=supabase, id_institucion=id_institucion)
        if not institucion:
            return None

        service_url = institucion.get("service_url")
        if not isinstance(service_url, str) or not service_url.strip():
            return InstitucionHealthResponse(
                id_institucion=id_institucion,
                status="NOT_CONFIGURED",
                service_url=None,
                message="La institucion no tiene service_url configurada.",
            )

        normalized_url = service_url.strip()
        started_at = perf_counter()
        checked_url = _health_probe_url(normalized_url)
        try:
            response = httpx.get(checked_url, timeout=self._settings().ips_timeout_seconds)
        except httpx.TimeoutException:
            return InstitucionHealthResponse(
                id_institucion=id_institucion,
                status="DOWN",
                service_url=normalized_url,
                latency_ms=_elapsed_ms(started_at),
                message="Timeout al consultar el servicio.",
            )
        except httpx.RequestError as exc:
            return InstitucionHealthResponse(
                id_institucion=id_institucion,
                status="DOWN",
                service_url=normalized_url,
                latency_ms=_elapsed_ms(started_at),
                message=str(exc) or "No fue posible conectar con el servicio.",
            )

        status_value = "UP" if 200 <= response.status_code < 300 else "DOWN"
        return InstitucionHealthResponse(
            id_institucion=id_institucion,
            status=status_value,
            service_url=normalized_url,
            status_code=response.status_code,
            latency_ms=_elapsed_ms(started_at),
            message=(
                f"Servicio disponible en {checked_url}."
                if status_value == "UP"
                else f"El servicio respondio con error en {checked_url}."
            ),
        )

    def _settings(self) -> Settings:
        if self.settings is None:
            self.settings = get_settings()
        return self.settings


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def _health_probe_url(service_url: str) -> str:
    normalized_url = service_url.rstrip("/")
    if "/fhir" in normalized_url:
        return normalized_url
    return f"{normalized_url}/fhir/health"
