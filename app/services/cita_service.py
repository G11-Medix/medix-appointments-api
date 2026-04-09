import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from supabase import Client

from fastapi import HTTPException, status

from app.clients.ips_client import IpsClient
from app.core.config import Settings, get_settings
from app.schemas.cita import CitaCreate, CitaDelete, CitaUpdate, CitaAppResponse
from app.services.institucion_service import InstitucionService
from app.services.especialidad_service import EspecialidadService


@dataclass(frozen=True)
class IpsRoute:
    base_url: str
    api_key: str


class CitaService:
    def __init__(self, client: IpsClient | None = None, settings: Settings | None = None, institucion_service: InstitucionService | None = None, especialidad_service: EspecialidadService | None = None) -> None:
        self.settings = settings
        self.client = client
        self.institucion_service = institucion_service or InstitucionService()
        self.especialidad_service = especialidad_service or EspecialidadService()

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
    
    def list_all_citas_by_paciente(
        self,
        supabase: Client,
        id_paciente: int,
    ) -> list[dict[str, Any]]:

        instituciones = self.institucion_service.list_instituciones(supabase)

        all_citas: list[dict[str, Any]] = []

        for inst in instituciones:
            try:
                
                id_institucion = inst.get("id_institucion") or inst.get("id")

                if not id_institucion:
                    print(f"Institución sin id válido: {inst}")
                    continue

               
                route = self._resolve_route(id_institucion)

                response = self._client().request(
                    method="GET",
                    base_url=route.base_url,
                    api_key=route.api_key,
                    path="/api/v1/citas",
                    params={"id_paciente": id_paciente},
                )

                if isinstance(response, list):
                    for cita in response:
                        cita["id_institucion"] = id_institucion

                    all_citas.extend(response)

            except Exception as e:
                print(f"Error en IPS {inst.get('id_institucion', 'SIN_ID')}: {e}")
                continue

        return all_citas
    
    def list_citas_app_by_paciente(
        self,
        supabase: Client,
        id_paciente: int,
    ) -> list[CitaAppResponse]:

        
        instituciones = self.institucion_service.list_instituciones(supabase)

        inst_map = {
            inst["id_institucion"]: inst["nombre"]
            for inst in instituciones
        }

       
        especialidades = self.especialidad_service.list_especialidades(supabase)

        esp_map = {
            esp["id_especialidad"]: esp["nombre"]
            for esp in especialidades
        }

        
        rows = self.list_all_citas_by_paciente(
            supabase=supabase,
            id_paciente=id_paciente
        )

        
        return [
            CitaAppResponse(
                id=row["id"],
                nombre_ins=inst_map.get(
                    row.get("id_institucion"),
                    "Institución desconocida"
                ),
                especialidad=esp_map.get(
                    row.get("id_especialidad"),
                    "Especialidad desconocida"
                ),
                fecha_hora_cupo=row["fecha_hora_cupo"],
            )
            for row in rows
        ]

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
