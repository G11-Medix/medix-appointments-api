from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import HTTPException, status

from app.schemas.assistant import (
    AssistantAppointmentActionResponse,
    AssistantAppointmentResponse,
    AssistantAvailabilityDay,
    AssistantAvailabilityResponse,
    AssistantAvailabilitySlot,
    AssistantInstitutionResponse,
    AssistantPatientResponse,
    AssistantSpecialtyResponse,
)
from app.services.ips_mock_gateway import IpsMockGateway
from app.services.ips_route_resolver import IpsRoute


class AssistantAppointmentsService:
    def __init__(self, gateway: IpsMockGateway | None = None) -> None:
        self.gateway = gateway or IpsMockGateway()

    def list_specialties(self, access_token: str | None = None) -> list[AssistantSpecialtyResponse]:
        by_id: dict[int, AssistantSpecialtyResponse] = {}
        for route in self.gateway.list_routes():
            for row in self.gateway.list_specialties(route, access_token=access_token):
                specialty_id = int(row["id"])
                if specialty_id not in by_id:
                    by_id[specialty_id] = AssistantSpecialtyResponse(
                        id=specialty_id,
                        nombre=str(row["nombre"]),
                    )
        return list(by_id.values())

    def list_instituciones_by_especialidad(
        self,
        codigo_reps: int,
        access_token: str | None = None,
    ) -> list[AssistantInstitutionResponse]:
        instituciones: list[AssistantInstitutionResponse] = []
        for route in self.gateway.list_routes():
            providers = self.gateway.list_providers(route, id_especialidad=codigo_reps, access_token=access_token)
            if not providers:
                continue

            current_ips = self.gateway.get_current_ips(route, access_token=access_token)
            instituciones.append(
                AssistantInstitutionResponse(
                    id_institucion=route.id_institucion,
                    nombre=str(current_ips.get("nombre") or f"IPS {route.id_institucion}"),
                    estado=_map_institution_status(str(current_ips.get("estado") or "")),
                    especialidades=[codigo_reps],
                )
            )
        return instituciones

    def get_disponibilidad(
        self,
        id_institucion: int,
        codigo_reps: int,
        fecha_desde: date,
        dias: int,
        access_token: str | None = None,
    ) -> AssistantAvailabilityResponse:
        if dias < 1:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="dias debe ser mayor a 0")

        route = self.gateway.get_route(id_institucion)
        current_ips = self.gateway.get_current_ips(route, access_token=access_token)
        provider_rows = self.gateway.list_providers(route, id_especialidad=codigo_reps, access_token=access_token)
        provider_names = {int(row["id"]): str(row["nombre_completo"]) for row in provider_rows}

        slots_by_date: dict[date, list[AssistantAvailabilitySlot]] = defaultdict(list)
        for offset in range(dias):
            target_date = fecha_desde + timedelta(days=offset)
            for provider_id, provider_name in provider_names.items():
                for row in self.gateway.get_provider_slots(route, provider_id, target_date, access_token=access_token):
                    if not bool(row.get("disponible")) or bool(row.get("bloqueado")):
                        continue
                    fecha_hora = _parse_datetime(row["fecha_hora"])
                    slots_by_date[target_date].append(
                        AssistantAvailabilitySlot(
                            hora=fecha_hora.strftime("%H:%M"),
                            fecha_hora=fecha_hora,
                            id_prestador=provider_id,
                            nombre_prestador=provider_name,
                        )
                    )

        disponibilidad = [
            AssistantAvailabilityDay(
                fecha=target_date,
                slots=sorted(
                    slots_by_date[target_date],
                    key=lambda item: (item.fecha_hora, item.id_prestador),
                ),
            )
            for target_date in sorted(slots_by_date)
        ]
        return AssistantAvailabilityResponse(
            id_institucion=id_institucion,
            nombre_institucion=str(current_ips.get("nombre") or f"IPS {id_institucion}"),
            codigo_reps=codigo_reps,
            disponibilidad=disponibilidad,
        )

    def schedule_appointment(
        self,
        id_paciente: int,
        id_institucion: int,
        codigo_reps: int,
        fecha: date,
        hora: time,
        access_token: str | None = None,
    ) -> AssistantAppointmentActionResponse:
        route = self.gateway.get_route(id_institucion)
        slot = self._find_exact_slot(route, codigo_reps, fecha, hora, access_token=access_token)
        cita = self.gateway.create_appointment(
            route=route,
            id_paciente=id_paciente,
            id_prestador=slot.id_prestador,
            fecha_hora_cupo=slot.fecha_hora,
            access_token=access_token,
        )
        return AssistantAppointmentActionResponse(
            mensaje="Cita agendada correctamente",
            cita=_to_assistant_appointment(cita, map_status=True),
        )

    def cancel_appointment(
        self,
        id_cita: int,
        id_institucion: int,
        motivo: str | None,
        access_token: str | None = None,
    ) -> AssistantAppointmentActionResponse:
        route = self.gateway.get_route(id_institucion)
        cita = self.gateway.cancel_appointment(route=route, id_cita=id_cita, motivo=motivo, access_token=access_token)
        return AssistantAppointmentActionResponse(
            mensaje="Cita cancelada correctamente",
            cita=_to_assistant_appointment(cita, map_status=True),
        )

    def reschedule_appointment(
        self,
        id_cita: int,
        id_institucion: int,
        codigo_reps: int,
        nueva_fecha: date,
        nueva_hora: time,
        access_token: str | None = None,
    ) -> AssistantAppointmentActionResponse:
        route = self.gateway.get_route(id_institucion)
        slot = self._find_exact_slot(route, codigo_reps, nueva_fecha, nueva_hora, access_token=access_token)
        cita = self.gateway.reschedule_appointment(
            route=route,
            id_cita=id_cita,
            nueva_fecha_hora_cupo=slot.fecha_hora,
            access_token=access_token,
        )
        return AssistantAppointmentActionResponse(
            mensaje="Cita reprogramada correctamente",
            cita=_to_assistant_appointment(cita, map_status=True),
        )

    def find_patient_by_document(
        self,
        tipo_documento: str,
        numero_documento: str,
        access_token: str | None = None,
    ) -> AssistantPatientResponse:
        for route in self.gateway.list_routes():
            try:
                row = self.gateway.find_patient_by_document(
                    route,
                    tipo_documento,
                    numero_documento,
                    access_token=access_token,
                )
                return AssistantPatientResponse.model_validate(row)
            except HTTPException as exc:
                if exc.status_code == status.HTTP_404_NOT_FOUND:
                    continue
                raise
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    def _find_exact_slot(
        self,
        route: IpsRoute,
        codigo_reps: int,
        fecha: date,
        hora: time,
        access_token: str | None = None,
    ) -> AssistantAvailabilitySlot:
        disponibilidad = self.get_disponibilidad(
            id_institucion=route.id_institucion,
            codigo_reps=codigo_reps,
            fecha_desde=fecha,
            dias=1,
            access_token=access_token,
        )
        target_hour = hora.strftime("%H:%M")
        candidates = [
            slot
            for day in disponibilidad.disponibilidad
            for slot in day.slots
            if day.fecha == fecha and slot.hora == target_hour
        ]
        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay disponibilidad para la fecha y hora solicitadas",
            )
        return sorted(candidates, key=lambda item: (item.fecha_hora, item.id_prestador))[0]


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _map_institution_status(value: str) -> str:
    return "ACTIVA" if value.upper() == "ACTIVO" else value


def _map_appointment_status(value: str) -> str:
    normalized = str(value or "").lower()
    if normalized == "scheduled":
        return "RESERVADA"
    if normalized == "cancelled":
        return "CANCELADA"
    return str(value or "")


def _to_assistant_appointment(payload: dict[str, Any], *, map_status: bool) -> AssistantAppointmentResponse:
    row = dict(payload)
    if map_status:
        row["estado"] = _map_appointment_status(str(row.get("estado") or ""))
    return AssistantAppointmentResponse.model_validate(row)
