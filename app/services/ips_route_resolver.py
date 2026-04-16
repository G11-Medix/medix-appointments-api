import json
from collections.abc import Mapping
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class IpsRoute:
    id_institucion: int
    base_url: str
    api_key: str | None = None


class IpsRouteResolver:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    def list_routes(self) -> list[IpsRoute]:
        return list(_parse_routes(self._settings().ips_routes_json).values())

    def get_route(self, id_institucion: int) -> IpsRoute:
        route = _parse_routes(self._settings().ips_routes_json).get(id_institucion)
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
        if not isinstance(base_url, str) or not base_url.strip():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="IPS_ROUTES_JSON requiere base_url por institución",
            )

        route_id = int(key)
        routes[route_id] = IpsRoute(
            id_institucion=route_id,
            base_url=base_url,
            api_key=value.get("api_key") if isinstance(value.get("api_key"), str) and value.get("api_key") else None,
        )

    return routes
