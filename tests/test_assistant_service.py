from datetime import date, datetime, time

import pytest
from fastapi import HTTPException

from app.services.assistant_appointments_service import AssistantAppointmentsService
from app.services.ips_route_resolver import IpsRoute


class FakeGateway:
    def __init__(self) -> None:
        self.routes = [
            IpsRoute(id_institucion=1, base_url="http://ips-1", api_key="k1"),
            IpsRoute(id_institucion=2, base_url="http://ips-2", api_key="k2"),
        ]
        self.create_calls: list[tuple[int, int, int, datetime]] = []
        self.cancel_calls: list[tuple[int, int, str | None]] = []
        self.reschedule_calls: list[tuple[int, int, datetime]] = []

    def list_routes(self) -> list[IpsRoute]:
        return self.routes

    def get_route(self, id_institucion: int) -> IpsRoute:
        for route in self.routes:
            if route.id_institucion == id_institucion:
                return route
        raise HTTPException(status_code=404, detail="No route")

    def list_specialties(self, route: IpsRoute) -> list[dict]:
        if route.id_institucion == 1:
            return [{"id": 1, "nombre": "Cardiologia"}]
        return [{"id": 1, "nombre": "Cardiologia"}, {"id": 2, "nombre": "Pediatria"}]

    def get_current_ips(self, route: IpsRoute) -> dict:
        return {"id_ips": route.id_institucion, "nombre": f"IPS {route.id_institucion}", "estado": "ACTIVO"}

    def list_providers(self, route: IpsRoute, id_especialidad: int | None = None) -> list[dict]:
        if id_especialidad == 1 and route.id_institucion == 1:
            return [
                {"id": 5, "nombre_completo": "Dr. Perez", "id_especialidad": 1},
                {"id": 4, "nombre_completo": "Dra. Gomez", "id_especialidad": 1},
            ]
        return []

    def get_provider_slots(self, route: IpsRoute, id_prestador: int, fecha: date) -> list[dict]:
        if fecha != date(2026, 4, 10):
            return []
        return [
            {
                "id_prestador": id_prestador,
                "fecha_hora": f"{fecha.isoformat()}T10:00:00",
                "disponible": True,
                "bloqueado": False,
            },
            {
                "id_prestador": id_prestador,
                "fecha_hora": f"{fecha.isoformat()}T11:00:00",
                "disponible": False,
                "bloqueado": False,
            },
        ]

    def create_appointment(self, route: IpsRoute, id_paciente: int, id_prestador: int, fecha_hora_cupo: datetime) -> dict:
        self.create_calls.append((route.id_institucion, id_paciente, id_prestador, fecha_hora_cupo))
        return {
            "id": 100,
            "id_paciente": id_paciente,
            "id_prestador": id_prestador,
            "id_especialidad": 1,
            "fecha_hora_cupo": fecha_hora_cupo.isoformat(),
            "estado": "scheduled",
            "motivo_cancelacion": None,
            "fecha_creacion": "2026-04-01T08:00:00",
            "fecha_actualizacion": "2026-04-01T08:00:00",
        }

    def cancel_appointment(self, route: IpsRoute, id_cita: int, motivo: str | None) -> dict:
        self.cancel_calls.append((route.id_institucion, id_cita, motivo))
        return {
            "id": id_cita,
            "id_paciente": 12,
            "id_prestador": 5,
            "id_especialidad": 1,
            "fecha_hora_cupo": "2026-04-10T10:00:00",
            "estado": "cancelled",
            "motivo_cancelacion": motivo,
            "fecha_creacion": "2026-04-01T08:00:00",
            "fecha_actualizacion": "2026-04-01T09:00:00",
        }

    def reschedule_appointment(self, route: IpsRoute, id_cita: int, nueva_fecha_hora_cupo: datetime) -> dict:
        self.reschedule_calls.append((route.id_institucion, id_cita, nueva_fecha_hora_cupo))
        return {
            "id": id_cita,
            "id_paciente": 12,
            "id_prestador": 4,
            "id_especialidad": 1,
            "fecha_hora_cupo": nueva_fecha_hora_cupo.isoformat(),
            "estado": "scheduled",
            "motivo_cancelacion": None,
            "fecha_creacion": "2026-04-01T08:00:00",
            "fecha_actualizacion": "2026-04-01T09:00:00",
        }

    def find_patient_by_document(self, route: IpsRoute, tipo_documento: str, numero_documento: str) -> dict:
        if route.id_institucion == 1:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        return {
            "id_paciente": 12,
            "tipo_documento": tipo_documento,
            "numero_documento": numero_documento,
            "nombres": "Ana",
            "apellidos": "Perez",
            "fecha_nacimiento": "2000-01-01",
            "telefono": "3000000000",
            "correo": "ana@example.com",
            "estado": "ACTIVO",
            "fecha_creacion": "2026-04-01T08:00:00",
        }


def test_list_specialties_deduplicates() -> None:
    rows = AssistantAppointmentsService(gateway=FakeGateway()).list_specialties()

    assert [row.id for row in rows] == [1, 2]


def test_list_instituciones_by_especialidad_filters_ips_without_providers() -> None:
    rows = AssistantAppointmentsService(gateway=FakeGateway()).list_instituciones_by_especialidad(1)

    assert len(rows) == 1
    assert rows[0].estado == "ACTIVA"


def test_get_disponibilidad_groups_and_filters() -> None:
    response = AssistantAppointmentsService(gateway=FakeGateway()).get_disponibilidad(1, 1, date(2026, 4, 10), 1)

    assert response.nombre_institucion == "IPS 1"
    assert [slot.id_prestador for slot in response.disponibilidad[0].slots] == [4, 5]
    assert all(slot.hora == "10:00" for slot in response.disponibilidad[0].slots)


def test_schedule_appointment_uses_deterministic_provider() -> None:
    gateway = FakeGateway()
    response = AssistantAppointmentsService(gateway=gateway).schedule_appointment(
        id_paciente=12,
        id_institucion=1,
        id_especialidad=1,
        fecha=date(2026, 4, 10),
        hora=time(10, 0, 0),
    )

    assert gateway.create_calls[0][2] == 4
    assert response.cita.estado == "RESERVADA"


def test_schedule_appointment_fails_when_slot_missing() -> None:
    with pytest.raises(HTTPException) as exc:
        AssistantAppointmentsService(gateway=FakeGateway()).schedule_appointment(
            id_paciente=12,
            id_institucion=1,
            id_especialidad=1,
            fecha=date(2026, 4, 10),
            hora=time(9, 0, 0),
        )

    assert exc.value.status_code == 404


def test_cancel_reschedule_and_find_patient() -> None:
    gateway = FakeGateway()
    service = AssistantAppointmentsService(gateway=gateway)

    cancelled = service.cancel_appointment(9, 1, "No puedo asistir")
    rescheduled = service.reschedule_appointment(9, 1, 1, date(2026, 4, 10), time(10, 0, 0))
    patient = service.find_patient_by_document("CC", "123")

    assert cancelled.cita.estado == "CANCELADA"
    assert rescheduled.cita.estado == "RESERVADA"
    assert patient.id_paciente == 12
