import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.clients.ips_client import IpsClient
from app.core.config import Settings, get_settings
from app.schemas.cita import CitaCreate, CitaDelete, CitaUpdate


@dataclass(frozen=True)
class IpsRoute:
    base_url: str
    api_key: str


class CitaService:
    def __init__(self, client: IpsClient | None = None, settings: Settings | None = None) -> None:
        self.settings = settings
        self.client = client

    def create_cita(self, id_institucion: int, payload: CitaCreate) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._client().request(
            method="POST",
            base_url=route.base_url,
            api_key=route.api_key,
            path="/api/v1/citas",
            payload=payload.model_dump(mode="json"),
        )

    def get_cita(self, id_institucion: int, id_cita: int) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._client().request(
            method="GET",
            base_url=route.base_url,
            api_key=route.api_key,
            path=f"/api/v1/citas/{id_cita}",
        )

    def list_citas(
        self,
        id_institucion: int,
        *,
        id_paciente: int | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[dict[str, Any]]:
        route = self._resolve_route(id_institucion)
        params: dict[str, str | int] = {}
        if id_paciente is not None:
            params["id_paciente"] = id_paciente
        if desde is not None:
            params["desde"] = desde.isoformat()
        if hasta is not None:
            params["hasta"] = hasta.isoformat()

        response = self._client().request(
            method="GET",
            base_url=route.base_url,
            api_key=route.api_key,
            path="/api/v1/citas",
            params=params,
        )
        return response if isinstance(response, list) else []

    def update_cita(self, id_institucion: int, id_cita: int, payload: CitaUpdate) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._client().request(
            method="PATCH",
            base_url=route.base_url,
            api_key=route.api_key,
            path=f"/api/v1/citas/{id_cita}/reprogramar",
            payload=payload.model_dump(mode="json"),
        )

    def delete_cita(self, id_institucion: int, id_cita: int, payload: CitaDelete) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._client().request(
            method="PATCH",
            base_url=route.base_url,
            api_key=route.api_key,
            path=f"/api/v1/citas/{id_cita}/cancelar",
            payload=payload.model_dump(mode="json"),
        )

    def _resolve_route(self, id_institucion: int) -> IpsRoute:
        routes = _parse_routes(self._settings().ips_routes_json)
        route = routes.get(id_institucion)
        if route is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No hay configuración IPS para id_institucion={id_institucion}",
            )
        return route

    def _settings(self) -> Settings:
        if self.settings is None:
            self.settings = get_settings()
        return self.settings

    def _client(self) -> IpsClient:
        if self.client is None:
            self.client = IpsClient(timeout_seconds=self._settings().ips_timeout_seconds)
        return self.client


def _parse_routes(raw_json: str) -> dict[int, IpsRoute]:
    try:
        data = json.loads(raw_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="IPS_ROUTES_JSON no es un JSON válido",
        ) from exc

    if not isinstance(data, Mapping):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="IPS_ROUTES_JSON debe ser un objeto con id_institucion como llave",
        )

    routes: dict[int, IpsRoute] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not key.isdigit():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="IPS_ROUTES_JSON tiene llaves inválidas",
            )
        if not isinstance(value, Mapping):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="IPS_ROUTES_JSON tiene entradas inválidas",
            )

        base_url = value.get("base_url")
        api_key = value.get("api_key")
        if not isinstance(base_url, str) or not base_url.strip():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="IPS_ROUTES_JSON requiere base_url por institución",
            )
        if not isinstance(api_key, str) or not api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="IPS_ROUTES_JSON requiere api_key por institución",
            )

        routes[int(key)] = IpsRoute(base_url=base_url, api_key=api_key)
    return routes
