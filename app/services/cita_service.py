import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from supabase import Client

from app.clients.ips_client import IpsClient
from app.core.config import Settings, get_settings
from app.schemas.cita import CitaCreate, CitaDelete, CitaIpsResponse, CitaUpdate, CitaAppResponse
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
        patient = self._gateway().find_patient_by_document(
            route=route,
            tipo_documento=payload.tipo_documento,
            numero_documento=payload.numero_documento,
            access_token=access_token,
        )
        return self._gateway().create_appointment(
            route=route,
            id_paciente=int(patient["id_paciente"]),
            id_prestador=payload.id_prestador,
            fecha_hora_cupo=datetime.combine(payload.fecha, payload.hora),
            id_especialidad=getattr(payload, "id_especialidad", None),
            access_token=access_token,
        )

    def get_cita(self, id_institucion: int, id_cita: int, access_token: str | None = None) -> dict[str, Any]:
        route = self._resolve_route(id_institucion)
        return self._gateway().get_appointment(route=route, id_cita=id_cita, access_token=access_token)

    def get_cita_ips(
        self,
        supabase: Client,
        id_institucion: int,
        id_cita: int,
        access_token: str | None = None,
    ) -> CitaIpsResponse:
        route = self._resolve_route(id_institucion)
        row = self._gateway().get_appointment(route=route, id_cita=id_cita, access_token=access_token)
        return self._build_cita_ips_response(
            route=route,
            row=row,
            especialidades_map=self._build_especialidades_map(supabase),
            access_token=access_token,
        )

    def get_cita_confirmacion(
        self,
        supabase: Client,
        id_institucion: int,
        id_cita: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        cita = self.get_cita(id_institucion=id_institucion, id_cita=id_cita, access_token=access_token)
        institucion = self.institucion_service.get_institucion(supabase=supabase, id_institucion=id_institucion)
        if not institucion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institucion no encontrada")

        return {
            "doctor": str(cita.get("nombre_prestador") or f"Prestador {cita['id_prestador']}"),
            "fecha": cita["fecha_hora_cupo"],
            "institucion": institucion["nombre"],
            "direccion": institucion.get("direccion"),
            "latitud": institucion.get("latitud"),
            "longitud": institucion.get("longitud"),
            "estado": cita["estado"],
        }

    def list_citas(
        self,
        id_institucion: int,
        *,
        tipo_documento: str | None = None,
        cedula: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        access_token: str | None = None,
    ) -> list[dict[str, Any]]:
        route = self._resolve_route(id_institucion)
        id_paciente: int | None = None
        if cedula is not None:
            patient = self._gateway().find_patient_by_document(
                route=route,
                tipo_documento=tipo_documento or "CC",
                numero_documento=cedula,
                access_token=access_token,
            )
            id_paciente = int(patient["id_paciente"])
        response = self._gateway().list_appointments(
            route=route,
            id_paciente=id_paciente,
            access_token=access_token,
        )
        rows = response if isinstance(response, list) else []
        if desde is None and hasta is None:
            return rows
        return [
            row for row in rows
            if self._appointment_in_range(row, desde=desde, hasta=hasta)
        ]

    def list_citas_ips(
        self,
        supabase: Client,
        id_institucion: int,
        *,
        tipo_documento: str | None = None,
        cedula: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        access_token: str | None = None,
    ) -> list[CitaIpsResponse]:
        route = self._resolve_route(id_institucion)
        especialidades_map = self._build_especialidades_map(supabase)
        rows = self.list_citas(
            id_institucion=id_institucion,
            tipo_documento=tipo_documento,
            cedula=cedula,
            desde=desde,
            hasta=hasta,
            access_token=access_token,
        )
        patient_cache: dict[int, dict[str, Any]] = {}
        return [
            self._build_cita_ips_response(
                route=route,
                row=row,
                especialidades_map=especialidades_map,
                access_token=access_token,
                patient_cache=patient_cache,
            )
            for row in rows
        ]

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
        inst_map = _build_institucion_map(instituciones)
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

        def _build_cita_app_response(row: dict[str, Any]) -> CitaAppResponse:
            institucion = _get_institucion(row, inst_map)
            return CitaAppResponse(
                id=row["id"],
                id_institucion=int(row["id_institucion"]),
                nombre_institucion=institucion.get("nombre", "Institución desconocida"),
                logo_url=institucion.get("logo_url"),
                especialidad=esp_map.get(
                    row.get("id_especialidad"),
                    "Especialidad desconocida",
                ),
                estado=row["estado"],
                fecha_hora_cupo=row["fecha_hora_cupo"],
            )

        return [
            _build_cita_app_response(row)
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

    def _build_especialidades_map(self, supabase: Client) -> dict[int, str]:
        especialidades = self.especialidad_service.list_especialidades(supabase)
        esp_map = {
            int(esp["codigo_reps"]): str(esp["nombre"])
            for esp in especialidades
            if esp.get("codigo_reps") is not None
        }
        esp_map.update({
            int(esp["id_especialidad"]): str(esp["nombre"])
            for esp in especialidades
            if esp.get("id_especialidad") is not None
        })
        return esp_map

    def _build_cita_ips_response(
        self,
        *,
        route: IpsRoute,
        row: dict[str, Any],
        especialidades_map: dict[int, str],
        access_token: str | None = None,
        patient_cache: dict[int, dict[str, Any]] | None = None,
    ) -> CitaIpsResponse:
        fecha_hora = _parse_optional_datetime(row.get("fecha_hora_cupo"))
        if fecha_hora is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="La IPS respondio una cita sin fecha/hora valida",
            )

        patient = self._get_patient_for_appointment(
            route=route,
            row=row,
            access_token=access_token,
            patient_cache=patient_cache,
        )
        specialty_id = row.get("id_especialidad")
        specialty_name = row.get("nombre_especialidad")
        if not specialty_name and specialty_id is not None:
            specialty_name = especialidades_map.get(int(specialty_id), None)

        return CitaIpsResponse(
            id=int(row["id"]),
            nombre_paciente=_patient_full_name(patient),
            cedula_paciente=str(patient.get("numero_documento") or ""),
            id_prestador=int(row.get("id_prestador") or 0),
            nombre_prestador=row.get("nombre_prestador"),
            especialidad=str(specialty_name or "Especialidad desconocida"),
            fecha=fecha_hora.date(),
            hora=fecha_hora.time(),
            estado_cita=str(row.get("estado") or ""),
            motivo_cancelacion=row.get("motivo_cancelacion"),
            fecha_creacion=_parse_optional_datetime(row.get("fecha_creacion")) or fecha_hora,
            fecha_actualizacion=_parse_optional_datetime(row.get("fecha_actualizacion")) or fecha_hora,
        )

    def _get_patient_for_appointment(
        self,
        *,
        route: IpsRoute,
        row: dict[str, Any],
        access_token: str | None = None,
        patient_cache: dict[int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        id_paciente = int(row.get("id_paciente") or 0)
        if id_paciente <= 0:
            return {}
        if patient_cache is not None and id_paciente in patient_cache:
            return patient_cache[id_paciente]
        try:
            patient = self._gateway().get_patient(
                route=route,
                id_paciente=id_paciente,
                access_token=access_token,
            )
        except HTTPException as exc:
            if exc.status_code != status.HTTP_404_NOT_FOUND:
                raise
            patient = {}
        if patient_cache is not None:
            patient_cache[id_paciente] = patient
        return patient

    @staticmethod
    def _appointment_in_range(
        row: dict[str, Any],
        *,
        desde: datetime | None,
        hasta: datetime | None,
    ) -> bool:
        fecha_hora = datetime.fromisoformat(str(row["fecha_hora_cupo"]))
        if desde is not None and fecha_hora < desde:
            return False
        if hasta is not None and fecha_hora > hasta:
            return False
        return True
    
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
        inst_map = _build_institucion_map(instituciones)
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

        def _build_cita_app_response(row: dict[str, Any]) -> CitaAppResponse:
            fecha_hora = _parse_optional_datetime(row.get("fecha_hora_cupo"))
            institucion = _get_institucion(row, inst_map)
            return CitaAppResponse(
                id=row["id"],
                id_institucion=int(row["id_institucion"]),
                nombre_institucion=institucion.get("nombre", "Institución desconocida"),
                logo_url=institucion.get("logo_url"),
                especialidad=esp_map.get(
                    row.get("id_especialidad"),
                    "Especialidad desconocida",
                ),
                estado=row["estado"],
                fecha=fecha_hora.date() if fecha_hora else None,
                hora=fecha_hora.time() if fecha_hora else None,
            )

        paciente = self.paciente_service.get_paciente(supabase=supabase, id_paciente=id_paciente)
        if not paciente or not paciente.get("numero_documento") or not paciente.get("tipo_documento"):
            return []
        rows = self.list_all_citas_by_paciente_doc(
            supabase=supabase,
            tipo_documento=str(paciente["tipo_documento"]),
            numero_documento=paciente["numero_documento"],
            access_token=access_token,
        )
        return [_build_cita_app_response(row) for row in rows]


def _build_institucion_map(instituciones: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {
        int(inst["id_institucion"]): inst
        for inst in instituciones
        if inst.get("id_institucion") is not None
    }


def _get_institucion(row: dict[str, Any], inst_map: dict[int, dict[str, Any]]) -> dict[str, Any]:
    id_institucion = row.get("id_institucion")
    if id_institucion is None:
        return {}
    return inst_map.get(int(id_institucion), {})


def _patient_full_name(patient: dict[str, Any]) -> str:
    full_name = f"{patient.get('nombres') or ''} {patient.get('apellidos') or ''}".strip()
    return full_name or "Paciente desconocido"


def _parse_optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    value_str = str(value).strip()
    if not value_str:
        return None
    return datetime.fromisoformat(value_str)
