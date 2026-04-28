from datetime import date, datetime
from types import SimpleNamespace

from app.services.ips_mock_gateway import IpsMockGateway
from app.services.ips_route_resolver import IpsRouteResolver


class FakeExecuteResponse:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class FakeSupabaseQuery:
    def __init__(self, data: list[dict]) -> None:
        self.data = data

    def select(self, _fields: str):  # noqa: ANN001
        return self

    def execute(self) -> FakeExecuteResponse:
        return FakeExecuteResponse(self.data)


class FakeSupabase:
    def __init__(self, data: list[dict]) -> None:
        self.data = data

    def table(self, name: str) -> FakeSupabaseQuery:
        assert name == "Institucion"
        return FakeSupabaseQuery(self.data)


class DummyIpsClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def request(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        path = kwargs["path"]
        if path == "/fhir/PractitionerRole":
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "PractitionerRole",
                            "id": "7",
                            "practitioner": {"reference": "Practitioner/7", "display": "Dr. Demo"},
                            "specialty": [
                                {
                                    "coding": [
                                        {
                                            "system": "urn:medix:specialty",
                                            "code": "302",
                                            "display": "Cardiologia",
                                        }
                                    ],
                                    "text": "Cardiologia",
                                }
                            ],
                        }
                    }
                ],
            }
        if path == "/fhir/Organization":
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Organization",
                            "id": "1",
                            "active": True,
                            "identifier": [{"system": "urn:medix:nit", "value": "900123"}],
                            "name": "IPS Demo",
                            "telecom": [{"system": "phone", "value": "6017000000"}],
                            "address": [{"text": "Calle 1"}],
                        }
                    }
                ],
            }
        if path == "/fhir/Slot":
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Slot",
                            "id": "7-2026-04-10T10:00:00",
                            "schedule": {"reference": "Schedule/7"},
                            "status": "free",
                            "start": "2026-04-10T10:00:00",
                            "end": "2026-04-10T10:30:00",
                        }
                    }
                ],
            }
        if path == "/fhir/Patient":
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "1",
                            "active": True,
                            "identifier": [
                                {
                                    "system": "urn:medix:document:cc",
                                    "value": "123",
                                    "type": {"text": "CC"},
                                }
                            ],
                            "name": [{"family": "Demo", "given": ["Paciente"]}],
                            "birthDate": "2000-01-01",
                            "meta": {"lastUpdated": "2026-04-01T08:00:00"},
                        }
                    }
                ],
            }
        if path.startswith("/fhir/Appointment/"):
            return {
                "resourceType": "Appointment",
                "id": "10",
                "status": "booked",
                            "specialty": [
                                {
                                    "coding": [
                                        {
                                            "system": "urn:medix:specialty",
                                            "code": "302",
                                            "display": "Cardiologia",
                                        }
                                    ],
                        "text": "Cardiologia",
                    }
                ],
                "slot": [{"reference": "Slot/7-2026-04-10T10:00:00"}],
                "participant": [
                    {"actor": {"reference": "Patient/1"}, "status": "accepted"},
                    {"actor": {"reference": "Practitioner/7"}, "status": "accepted"},
                ],
                "created": "2026-04-01T08:00:00",
                "meta": {"lastUpdated": "2026-04-01T08:00:00"},
                "start": "2026-04-10T10:00:00",
                "end": "2026-04-10T10:30:00",
            }
        return {
            "resourceType": "Appointment",
            "id": "10",
            "status": "booked",
            "specialty": [
                {
                    "coding": [
                        {
                            "system": "urn:medix:specialty",
                            "code": "302",
                            "display": "Cardiologia",
                        }
                    ],
                    "text": "Cardiologia",
                }
            ],
            "slot": [{"reference": "Slot/7-2026-04-10T10:00:00"}],
            "participant": [
                {"actor": {"reference": "Patient/1"}, "status": "accepted"},
                {"actor": {"reference": "Practitioner/7"}, "status": "accepted"},
            ],
            "created": "2026-04-01T08:00:00",
            "meta": {"lastUpdated": "2026-04-01T08:00:00"},
            "start": "2026-04-10T10:00:00",
            "end": "2026-04-10T10:30:00",
        }


def build_gateway() -> tuple[IpsMockGateway, DummyIpsClient]:
    settings = SimpleNamespace(
        ips_routes_json='{"1":{"base_url":"http://ips","api_key":"key"}}',
        ips_timeout_seconds=10,
    )
    client = DummyIpsClient()
    resolver = IpsRouteResolver(settings=settings)
    return IpsMockGateway(client=client, settings=settings, route_resolver=resolver), client


def test_gateway_maps_ips_mock_requests() -> None:
    gateway, client = build_gateway()
    route = gateway.get_route(1)

    gateway.list_specialties(route)
    gateway.get_current_ips(route)
    gateway.list_providers(route, id_especialidad=302)
    gateway.get_provider_slots(route, 7, date(2026, 4, 10))
    gateway.create_appointment(route, 1, 7, datetime(2026, 4, 10, 10, 0, 0), id_especialidad=302)
    gateway.cancel_appointment(route, 10, "No puedo asistir")
    gateway.reschedule_appointment(route, 10, datetime(2026, 4, 11, 14, 0, 0))
    gateway.find_patient_by_document(route, "CC", "123")

    assert client.calls[0]["path"] == "/fhir/PractitionerRole"
    assert client.calls[0]["params"] is None
    assert client.calls[1]["path"] == "/fhir/Organization"
    assert client.calls[2]["params"] == {"specialty": 302}
    assert client.calls[3]["params"] == {"schedule": "Schedule/7", "start": "2026-04-10"}
    assert client.calls[4]["path"] == "/fhir/PractitionerRole"
    assert client.calls[5]["method"] == "POST"
    assert client.calls[5]["path"] == "/fhir/Appointment"
    assert client.calls[6]["path"] == "/fhir/Appointment/10"
    assert client.calls[7]["path"] == "/fhir/Appointment/10"
    assert client.calls[8]["path"] == "/fhir/Appointment/10"
    assert client.calls[9]["path"] == "/fhir/Patient"
    assert client.calls[9]["params"] == {"identifier": "urn:medix:document:cc|123"}


def test_route_resolver_prefers_database_service_url_and_keeps_api_key() -> None:
    settings = SimpleNamespace(
        ips_routes_json='{"1":{"base_url":"http://env-ips","api_key":"key"}}',
        ips_timeout_seconds=10,
    )
    resolver = IpsRouteResolver(settings=settings)
    supabase = FakeSupabase([{"id_institucion": 1, "service_url": "http://db-ips/"}])

    route = resolver.get_route(1, supabase=supabase)

    assert route.base_url == "http://db-ips"
    assert route.api_key == "key"


def test_route_resolver_keeps_env_fallback_when_database_url_is_empty() -> None:
    settings = SimpleNamespace(
        ips_routes_json='{"1":{"base_url":"http://env-ips","api_key":"key"}}',
        ips_timeout_seconds=10,
    )
    resolver = IpsRouteResolver(settings=settings)
    supabase = FakeSupabase([{"id_institucion": 1, "service_url": ""}])

    route = resolver.get_route(1, supabase=supabase)

    assert route.base_url == "http://env-ips"
