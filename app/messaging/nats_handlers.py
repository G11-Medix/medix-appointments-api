from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import TypeAdapter
from supabase import Client

from app.api.dependencies.auth import AuthenticatedUserContext, authenticate_active_user_token
from app.schemas.cita import (
    CitaAppResponse,
    CitaConfirmacionResponse,
    CitaCreate,
    CitaDelete,
    CitaIpsResponse,
    CitaResponse,
    CitaUpdate,
)
from app.schemas.assistant import (
    AssistantAvailabilityResponse,
    AssistantInstitutionResponse,
    AssistantPatientResponse,
)
from app.schemas.especialidad import EspecialidadResponse
from app.schemas.institucion import InstitucionResponse
from app.schemas.paciente import PacienteResponse
from app.services.assistant_appointments_service import AssistantAppointmentsService
from app.services.cita_service import CitaService
from app.services.eps_service import EpsService
from app.services.especialidad_service import EspecialidadService
from app.services.institucion_service import InstitucionService
from app.services.paciente_service import PacienteService


class NatsApiHandlers:
    def __init__(
        self,
        *,
        supabase: Client,
        assistant_service: AssistantAppointmentsService | None = None,
        cita_service: CitaService | None = None,
        paciente_service: PacienteService | None = None,
        eps_service: EpsService | None = None,
        institucion_service: InstitucionService | None = None,
        especialidad_service: EspecialidadService | None = None,
    ) -> None:
        self.supabase = supabase
        self.assistant_service = assistant_service or AssistantAppointmentsService()
        self.cita_service = cita_service or CitaService()
        self.paciente_service = paciente_service or PacienteService()
        self.eps_service = eps_service or EpsService()
        self.institucion_service = institucion_service or InstitucionService()
        self.especialidad_service = especialidad_service or EspecialidadService()
        self._ips_list_adapter = TypeAdapter(list[CitaIpsResponse])
        self._app_list_adapter = TypeAdapter(list[CitaAppResponse])
        self._especialidad_list_adapter = TypeAdapter(list[EspecialidadResponse])
        self._institucion_list_adapter = TypeAdapter(list[InstitucionResponse])

    def authenticate(self, access_token: str) -> AuthenticatedUserContext:
        return authenticate_active_user_token(access_token, supabase=self.supabase)

    def handle_assistant_find_patient(self, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        response = self.assistant_service.find_patient_by_document(
            tipo_documento=str(payload["tipo_documento"]),
            numero_documento=str(payload["numero_documento"]),
            access_token=access_token,
        )
        return self._dump_model(response)

    def handle_list_especialidades(self, payload: dict[str, Any], access_token: str) -> list[dict[str, Any]]:
        limit = int(payload.get("limit", 50))
        rows = self.especialidad_service.list_especialidades(supabase=self.supabase, limit=limit)
        return self._dump_models(rows, self._especialidad_list_adapter)

    def handle_list_instituciones(self, payload: dict[str, Any], access_token: str) -> list[dict[str, Any]]:
        codigo_reps = payload.get("codigo_reps")
        if codigo_reps is not None:
            return self.handle_assistant_list_instituciones(payload, access_token)

        limit = int(payload.get("limit", 20))
        rows = self.institucion_service.list_instituciones(supabase=self.supabase, limit=limit)
        return self._dump_models(rows, self._institucion_list_adapter)

    def handle_assistant_list_instituciones(self, payload: dict[str, Any], access_token: str) -> list[dict[str, Any]]:
        codigo_reps = int(payload["codigo_reps"])
        rows = self.assistant_service.list_instituciones_by_especialidad(
            codigo_reps,
            access_token=access_token,
        )
        id_paciente = payload.get("id_paciente")
        if id_paciente is not None:
            paciente = self.paciente_service.get_paciente(supabase=self.supabase, id_paciente=int(id_paciente))
            if not paciente:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
            id_eps = paciente.get("id_eps")
            if id_eps is None:
                rows = []
            else:
                related_instituciones = self.eps_service.list_related_ips(supabase=self.supabase, id_eps=int(id_eps))
                related_ids = {
                    int(row["id_institucion"])
                    for row in related_instituciones
                    if row.get("id_institucion") is not None
                }
                rows = [row for row in rows if self._institution_id(row) in related_ids]
        return jsonable_encoder(rows)

    def handle_assistant_get_disponibilidad(self, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        response = self.assistant_service.get_disponibilidad(
            id_institucion=int(payload["id_institucion"]),
            codigo_reps=int(payload["codigo_reps"]),
            fecha_desde=self._parse_date(payload["fecha_desde"]),
            dias=int(payload["dias"]),
            access_token=access_token,
        )
        return self._dump_model(response)

    def handle_get_paciente(self, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        row = self.paciente_service.get_paciente(supabase=self.supabase, id_paciente=int(payload["id_paciente"]))
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
        return self._validate_and_dump(PacienteResponse, row)

    def handle_cita_create(self, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        response = self.cita_service.create_cita(
            id_institucion=int(payload["id_institucion"]),
            payload=CitaCreate.model_validate(payload["payload"]),
            access_token=access_token,
        )
        return self._validate_and_dump(CitaResponse, response)

    def handle_cita_get(self, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        response = self.cita_service.get_cita_ips(
            supabase=self.supabase,
            id_institucion=int(payload["id_institucion"]),
            id_cita=int(payload["id_cita"]),
            access_token=access_token,
        )
        return self._dump_model(response)

    def handle_cita_list(self, payload: dict[str, Any], access_token: str) -> list[dict[str, Any]]:
        rows = self.cita_service.list_citas_ips(
            supabase=self.supabase,
            id_institucion=int(payload["id_institucion"]),
            tipo_documento=self._optional_str(payload.get("tipo_documento")),
            cedula=self._optional_str(payload.get("cedula")),
            desde=self._parse_optional_datetime(payload.get("desde")),
            hasta=self._parse_optional_datetime(payload.get("hasta")),
            access_token=access_token,
        )
        return self._dump_models(rows, self._ips_list_adapter)

    def handle_cita_confirmacion(self, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        response = self.cita_service.get_cita_confirmacion(
            supabase=self.supabase,
            id_institucion=int(payload["id_institucion"]),
            id_cita=int(payload["id_cita"]),
            access_token=access_token,
        )
        return self._validate_and_dump(CitaConfirmacionResponse, response)

    def handle_cita_cancelar(self, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        response = self.cita_service.delete_cita(
            id_institucion=int(payload["id_institucion"]),
            id_cita=int(payload["id_cita"]),
            payload=CitaDelete.model_validate(payload["payload"]),
            access_token=access_token,
        )
        return self._validate_and_dump(CitaResponse, response)

    def handle_cita_reprogramar(self, payload: dict[str, Any], access_token: str) -> dict[str, Any]:
        response = self.cita_service.update_cita(
            id_institucion=int(payload["id_institucion"]),
            id_cita=int(payload["id_cita"]),
            payload=CitaUpdate.model_validate(payload["payload"]),
            access_token=access_token,
        )
        return self._validate_and_dump(CitaResponse, response)

    def handle_cita_listar_por_paciente(self, payload: dict[str, Any], access_token: str) -> list[dict[str, Any]]:
        rows = self.cita_service.list_citas_app_by_paciente_doc(
            supabase=self.supabase,
            id_paciente=int(payload["id_paciente"]),
            access_token=access_token,
        )
        return self._dump_models(rows, self._app_list_adapter)

    @staticmethod
    def _dump_model(model: Any) -> dict[str, Any]:
        return jsonable_encoder(model)

    @staticmethod
    def _dump_models(models: list[Any], adapter: TypeAdapter[Any]) -> list[dict[str, Any]]:
        validated = adapter.validate_python(models)
        return jsonable_encoder(adapter.dump_python(validated, mode="json"))

    @staticmethod
    def _validate_and_dump(model_type: type[Any], value: Any) -> dict[str, Any]:
        return jsonable_encoder(model_type.model_validate(value))

    @staticmethod
    def _parse_date(value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        return date.fromisoformat(str(value))

    @staticmethod
    def _parse_optional_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _institution_id(row: AssistantInstitutionResponse | dict[str, Any]) -> int | None:
        if isinstance(row, dict):
            value = row.get("id_institucion")
        else:
            value = row.id_institucion
        return int(value) if value is not None else None
