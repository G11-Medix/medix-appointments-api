from datetime import date, datetime
from types import SimpleNamespace

from app.services.eps_mock_gateway import EpsMockGateway
from app.services.ips_route_resolver import IpsRouteResolver


class DummyIpsClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def request(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        path = kwargs["path"]
        if path == "/api/v1/especialidades":
            return [{"id": 1, "nombre": "Cardiologia"}]
        if path == "/api/v1/ips/actual":
            return {"id_ips": 1, "nombre": "IPS Demo", "estado": "ACTIVO"}
        if path == "/api/v1/prestadores":
            return [{"id": 7, "nombre_completo": "Dr. Demo", "id_especialidad": 1}]
        if path.startswith("/api/v1/prestadores/"):
            return [
                {
                    "id_prestador": 7,
                    "fecha_hora": "2026-04-10T10:00:00",
                    "disponible": True,
                    "bloqueado": False,
                }
            ]
        return {
            "id": 10,
            "id_paciente": 1,
            "id_prestador": 7,
            "id_especialidad": 1,
            "fecha_hora_cupo": "2026-04-10T10:00:00",
            "estado": "scheduled",
            "motivo_cancelacion": None,
            "fecha_creacion": "2026-04-01T08:00:00",
            "fecha_actualizacion": "2026-04-01T08:00:00",
        }


def build_gateway() -> tuple[EpsMockGateway, DummyIpsClient]:
    settings = SimpleNamespace(
        ips_routes_json='{"1":{"base_url":"http://ips","api_key":"key"}}',
        ips_timeout_seconds=10,
    )
    client = DummyIpsClient()
    resolver = IpsRouteResolver(settings=settings)
    return EpsMockGateway(client=client, settings=settings, route_resolver=resolver), client


def test_gateway_maps_eps_requests() -> None:
    gateway, client = build_gateway()
    route = gateway.get_route(1)

    gateway.list_specialties(route)
    gateway.get_current_ips(route)
    gateway.list_providers(route, id_especialidad=1)
    gateway.get_provider_slots(route, 7, date(2026, 4, 10))
    gateway.create_appointment(route, 1, 7, datetime(2026, 4, 10, 10, 0, 0))
    gateway.cancel_appointment(route, 10, "No puedo asistir")
    gateway.reschedule_appointment(route, 10, datetime(2026, 4, 11, 14, 0, 0))
    gateway.find_patient_by_document(route, "CC", "123")

    assert client.calls[0]["path"] == "/api/v1/especialidades"
    assert client.calls[1]["path"] == "/api/v1/ips/actual"
    assert client.calls[2]["params"] == {"id_especialidad": 1}
    assert client.calls[3]["params"] == {"fecha": "2026-04-10"}
    assert client.calls[4]["method"] == "POST"
    assert client.calls[5]["path"] == "/api/v1/citas/10/cancelar"
    assert client.calls[6]["path"] == "/api/v1/citas/10/reprogramar"
    assert client.calls[7]["path"] == "/api/v1/pacientes/CC/123"
