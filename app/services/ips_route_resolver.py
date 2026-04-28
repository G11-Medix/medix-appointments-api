import json
from collections.abc import Mapping
from dataclasses import dataclass

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class IpsRoute:
    id_institucion: int
    base_url: str
    api_key: str | None = None


class IpsRouteResolver:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    def list_routes(self, supabase: Client | None = None) -> list[IpsRoute]:
        return list(self._routes(supabase=supabase).values())

    def get_route(self, id_institucion: int, supabase: Client | None = None) -> IpsRoute:
        route = self._routes(supabase=supabase).get(id_institucion)
        if route is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No hay configuración IPS para id_institucion={id_institucion}",
            )
        return route

    def _routes(self, supabase: Client | None = None) -> dict[int, IpsRoute]:
        routes = _parse_routes(self._settings().ips_routes_json)
        if supabase is None or not hasattr(supabase, "table"):
            return routes

        try:
            response = (
                supabase.table("Institucion")
                .select("id_institucion,service_url")
                .execute()
            )
        except APIError as exc:
            if _is_missing_service_url_error(exc):
                return routes
            raise
        for row in response.data or []:
            raw_id = row.get("id_institucion")
            service_url = row.get("service_url")
            if raw_id is None or not isinstance(service_url, str) or not service_url.strip():
                continue

            id_institucion = int(raw_id)
            existing_route = routes.get(id_institucion)
            routes[id_institucion] = IpsRoute(
                id_institucion=id_institucion,
                base_url=service_url.strip().rstrip("/"),
                api_key=existing_route.api_key if existing_route else None,
            )
        return routes

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


def _is_missing_service_url_error(error: APIError) -> bool:
    error_text = str(error)
    return "service_url" in error_text and ("42703" in error_text or "does not exist" in error_text)
