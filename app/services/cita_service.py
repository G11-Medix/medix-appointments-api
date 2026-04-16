import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from supabase import Client

from app.clients.ips_client import IpsClient
from app.core.config import Settings, get_settings
from app.schemas.cita import CitaCreate, CitaDelete, CitaUpdate, CitaAppResponse
from app.services.institucion_service import InstitucionService
from app.services.ips_mock_gateway import IpsMockGateway
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

    def create_cita(self, id_institucion: int, payload: CitaCreate, access_token: str | None = None) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._gateway().create_appointment(
            route=route,
            id_paciente=payload.id_paciente,
            id_prestador=payload.id_prestador,
            fecha_hora_cupo=payload.fecha_hora_cupo,
            id_especialidad=getattr(payload, "id_especialidad", None),
            access_token=access_token,
        )

    def get_cita(self, id_institucion: int, id_cita: int, access_token: str | None = None) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._gateway().get_appointment(route=route, id_cita=id_cita, access_token=access_token)

    def list_citas(
        self,
        id_institucion: int,
        *,
        id_paciente: int | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        access_token: str | None = None,
    ) -> list[dict[str, Any]]:
        route = self._resolve_route(id_institucion)
        response = self._gateway().list_appointments(
            route=route,
            id_paciente=id_paciente,
            desde=desde,
            access_token=access_token,
        )
        if hasta is not None:
            return [row for row in response if datetime.fromisoformat(str(row["fecha_hora_cupo"])) <= hasta]
        return response if isinstance(response, list) else []

    def list_all_citas_by_paciente(
        self,
        supabase: Client,
        id_paciente: int,
        access_token: str | None = None,
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
                response = self._gateway().list_appointments(
                    route=route,
                    id_paciente=id_paciente,
                    access_token=access_token,
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
        access_token: str | None = None,
    ) -> list[CitaAppResponse]:
        instituciones = self.institucion_service.list_instituciones(supabase)
        inst_map = {
            inst["id_institucion"]: inst["nombre"]
            for inst in instituciones
        }
        especialidades = self.especialidad_service.list_especialidades(supabase)
        esp_map = {
            int(esp["codigo_reps"]): esp["nombre"]
            for esp in especialidades
            if esp.get("codigo_reps") is not None
        }
        esp_map.update({
            int(esp["id_especialidad"]): esp["nombre"]
            for esp in especialidades
            if esp.get("id_especialidad") is not None
        })
        rows = self.list_all_citas_by_paciente(
            supabase=supabase,
            id_paciente=id_paciente,
            access_token=access_token,
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

    def update_cita(
        self,
        id_institucion: int,
        id_cita: int,
        payload: CitaUpdate,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._gateway().reschedule_appointment(
            route=route,
            id_cita=id_cita,
            nueva_fecha_hora_cupo=payload.nueva_fecha_hora_cupo,
            access_token=access_token,
        )

    def delete_cita(
        self,
        id_institucion: int,
        id_cita: int,
        payload: CitaDelete,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._gateway().cancel_appointment(
            route=route,
            id_cita=id_cita,
            motivo=payload.motivo,
            access_token=access_token,
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

    def _gateway(self) -> IpsMockGateway:
        return IpsMockGateway(
            client=self._client(),
            settings=self._settings(),
            route_resolver=self.route_resolver,
        )
    
    def list_all_citas_by_paciente_doc(
        self,
        supabase: Client,
        tipo_documento: str,
        numero_documento: str,
        access_token: str | None = None,
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
                patient = self._gateway().find_patient_by_document(
                    route=route,
                    tipo_documento=tipo_documento,
                    numero_documento=numero_documento,
                    access_token=access_token,
                )
                response = self._gateway().list_appointments(
                    route=route,
                    id_paciente=int(patient["id_paciente"]),
                    access_token=access_token,
                )

                if isinstance(response, list):
                    for cita in response:
                        cita["id_institucion"] = id_institucion

                    all_citas.extend(response)
            except HTTPException as exc:
                if exc.status_code == status.HTTP_404_NOT_FOUND:
                    self.logger.info(
                        "Paciente %s %s no encontrado en IPS %s",
                        tipo_documento,
                        numero_documento,
                        id_institucion,
                    )
                    continue
                self.logger.exception(
                    "Error obteniendo citas del paciente %s %s para la IPS %s",
                    tipo_documento,
                    numero_documento,
                    inst.get("id_institucion", "SIN_ID"),
                )
                continue
            except Exception:
                self.logger.exception(
                    "Error obteniendo citas del paciente %s %s para la IPS %s",
                    tipo_documento,
                    numero_documento,
                    inst.get("id_institucion", "SIN_ID"),
                )
                continue

        return all_citas

    def list_citas_app_by_paciente_doc(
        self,
        supabase: Client,
        id_paciente: int,
        access_token: str | None = None,
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
        if not paciente or not paciente.get("numero_documento") or not paciente.get("tipo_documento"):
            return []
        rows = self.list_all_citas_by_paciente_doc(
            supabase=supabase,
            tipo_documento=str(paciente["tipo_documento"]),
            numero_documento=paciente["numero_documento"],
            access_token=access_token,
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
