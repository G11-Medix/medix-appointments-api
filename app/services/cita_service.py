import logging
from datetime import datetime
from typing import Any

from supabase import Client

from app.clients.ips_client import IpsClient
from app.core.config import Settings, get_settings
from app.schemas.cita import CitaCreate, CitaDelete, CitaUpdate, CitaAppResponse
from app.services.institucion_service import InstitucionService
from app.services.ips_route_resolver import IpsRoute, IpsRouteResolver
from app.services.especialidad_service import EspecialidadService
from app.services.paciente_service import PacienteService

LOGGER = logging.getLogger(__name__)


class CitaService:
    def __init__(
        self,
        client: IpsClient | None = None,
        settings: Settings | None = None,
        institucion_service: InstitucionService | None = None,
        especialidad_service: EspecialidadService | None = None,
        paciente_service: PacienteService | None = None,
        route_resolver: IpsRouteResolver | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.institucion_service = institucion_service or InstitucionService()
        self.especialidad_service = especialidad_service or EspecialidadService()
        self.paciente_service = paciente_service or PacienteService()
        self.route_resolver = route_resolver or IpsRouteResolver(settings=settings)
        self.logger = logger or LOGGER

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
                    self.logger.warning("Institucion sin id valido en listado de citas: %s", inst)
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
            except Exception:
                self.logger.exception(
                    "Error obteniendo citas del paciente %s para la IPS %s",
                    id_paciente,
                    inst.get("id_institucion", "SIN_ID"),
                )
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
            id_paciente=id_paciente,
        )
        return [
            CitaAppResponse(
                id=row["id"],
                nombre_institucion=inst_map.get(
                    row.get("id_institucion"),
                    "Institución desconocida",
                ),
                especialidad=esp_map.get(
                    row.get("id_especialidad"),
                    "Especialidad desconocida",
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
        return self.route_resolver.get_route(id_institucion)

    def _settings(self) -> Settings:
        if self.settings is None:
            self.settings = get_settings()
        return self.settings

    def _client(self) -> IpsClient:
        if self.client is None:
            self.client = IpsClient(timeout_seconds=self._settings().ips_timeout_seconds)
        return self.client
    
    def list_all_citas_by_paciente_doc(
        self,
        supabase: Client,
        numero_documento: int,
    ) -> list[dict[str, Any]]:
        instituciones = self.institucion_service.list_instituciones(supabase)
        all_citas: list[dict[str, Any]] = []

        for inst in instituciones:
            try:
                id_institucion = inst.get("id_institucion") or inst.get("id")
                if not id_institucion:
                    self.logger.warning("Institucion sin id valido en listado de citas: %s", inst)
                    continue
                route = self._resolve_route(id_institucion)
                response = self._client().request(
                    method="GET",
                    base_url=route.base_url,
                    api_key=route.api_key,
                    path="/api/v1/citas",
                    params={"numero_documento": numero_documento},
                )

                if isinstance(response, list):
                    for cita in response:
                        cita["id_institucion"] = id_institucion

                    all_citas.extend(response)
            except Exception:
                self.logger.exception(
                    "Error obteniendo citas del paciente %s para la IPS %s",
                    numero_documento,
                    inst.get("id_institucion", "SIN_ID"),
                )
                continue

        return all_citas

    def list_citas_app_by_paciente_doc(
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

        paciente = self.paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
        if not paciente or not paciente.get("numero_documento"):
            return []
        rows = self.list_all_citas_by_paciente_doc(
            supabase=supabase,
            numero_documento=paciente["numero_documento"],
        )
        return [
            CitaAppResponse(
                id=row["id"],
                nombre_institucion=inst_map.get(
                    row.get("id_institucion"),
                    "Institución desconocida",
                ),
                especialidad=esp_map.get(
                    row.get("id_especialidad"),
                    "Especialidad desconocida",
                ),
                fecha_hora_cupo=row["fecha_hora_cupo"],
            )
            for row in rows
        ]
