from datetime import date

from fastapi import HTTPException

from app.services.assistant_appointments_service import AssistantAppointmentsService
from app.services.ips_route_resolver import IpsRoute


class FakeGateway:
    def __init__(self) -> None:
        self.routes = [
            IpsRoute(id_institucion=1, base_url="http://ips-1"),
            IpsRoute(id_institucion=2, base_url="http://ips-2"),
        ]

    def list_routes(self) -> list[IpsRoute]:
        return self.routes

    def get_route(self, id_institucion: int) -> IpsRoute:
        for route in self.routes:
            if route.id_institucion == id_institucion:
                return route
        raise HTTPException(status_code=404, detail="No route")

    def list_specialties(self, route: IpsRoute, access_token: str | None = None) -> list[dict]:
        if route.id_institucion == 1:
            return [{"id": 302, "nombre": "Cardiologia"}]
        return [{"id": 302, "nombre": "Cardiologia"}, {"id": 335, "nombre": "Pediatria"}]

    def get_current_ips(self, route: IpsRoute, access_token: str | None = None) -> dict:
        return {"id_ips": route.id_institucion, "nombre": f"IPS {route.id_institucion}", "estado": "ACTIVO"}

    def list_providers(self, route: IpsRoute, id_especialidad: int | None = None, access_token: str | None = None) -> list[dict]:
        if id_especialidad == 302 and route.id_institucion == 1:
            return [
                {"id": 5, "nombre_completo": "Dr. Perez", "id_especialidad": 302},
                {"id": 4, "nombre_completo": "Dra. Gomez", "id_especialidad": 302},
            ]
        return []

    def get_provider_slots(
        self,
        route: IpsRoute,
        id_prestador: int,
        fecha: date,
        access_token: str | None = None,
    ) -> list[dict]:
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

    def find_patient_by_document(
        self,
        route: IpsRoute,
        tipo_documento: str,
        numero_documento: str,
        access_token: str | None = None,
    ) -> dict:
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

    assert [row.id for row in rows] == [302, 335]


def test_list_instituciones_by_especialidad_filters_ips_without_providers() -> None:
    rows = AssistantAppointmentsService(gateway=FakeGateway()).list_instituciones_by_especialidad(302)

    assert len(rows) == 1
    assert rows[0].estado == "ACTIVA"


def test_get_disponibilidad_groups_and_filters() -> None:
    response = AssistantAppointmentsService(gateway=FakeGateway()).get_disponibilidad(1, 302, date(2026, 4, 10), 1)

    assert response.nombre_institucion == "IPS 1"
    assert [slot.id_prestador for slot in response.disponibilidad[0].slots] == [4, 5]
    assert all(slot.hora == "10:00" for slot in response.disponibilidad[0].slots)


def test_find_patient_by_document_returns_first_match() -> None:
    patient = AssistantAppointmentsService(gateway=FakeGateway()).find_patient_by_document("CC", "123")

    assert patient.id_paciente == 12
