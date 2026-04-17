from datetime import date, datetime, time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.cita import CitaCreate, CitaDelete, CitaUpdate
from app.services.cita_service import CitaService


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
                            "id": "2",
                            "practitioner": {"reference": "Practitioner/2", "display": "Dr. Demo"},
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
        if path == "/fhir/Patient":
            identifier = (kwargs.get("params") or {}).get("identifier")
            if identifier == "urn:medix:document:cc|123":
                return {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "entry": [
                        {
                            "resource": {
                                "resourceType": "Patient",
                                "id": "5",
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
            return {"resourceType": "Bundle", "type": "searchset", "entry": []}
        if path == "/fhir/Appointment" and kwargs["method"] == "GET":
            return {
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
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
                            "participant": [
                                {"actor": {"reference": "Patient/5"}, "status": "accepted"},
                                {"actor": {"reference": "Practitioner/2"}, "status": "accepted"},
                            ],
                            "created": "2026-03-31T10:00:00",
                            "meta": {"lastUpdated": "2026-03-31T10:00:00"},
                            "start": "2026-04-01T08:00:00",
                            "end": "2026-04-01T08:30:00",
                        }
                    }
                ],
            }
        if path == "/fhir/Appointment" and kwargs["method"] == "POST":
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
                "participant": [
                    {"actor": {"reference": "Patient/1"}, "status": "accepted"},
                    {"actor": {"reference": "Practitioner/2"}, "status": "accepted"},
                ],
                "created": "2026-03-31T10:00:00",
                "meta": {"lastUpdated": "2026-03-31T10:00:00"},
                "start": "2026-04-01T08:00:00",
                "end": "2026-04-01T08:30:00",
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
            "participant": [
                {"actor": {"reference": "Patient/1"}, "status": "accepted"},
                {"actor": {"reference": "Practitioner/2"}, "status": "accepted"},
            ],
            "created": "2026-03-31T10:00:00",
            "meta": {"lastUpdated": "2026-03-31T10:00:00"},
            "start": "2026-04-01T08:00:00",
            "end": "2026-04-01T08:30:00",
        }


def build_service(routes_json: str, client: DummyIpsClient | None = None) -> CitaService:
    settings = SimpleNamespace(
        ips_routes_json=routes_json,
        ips_timeout_seconds=10,
    )
    return CitaService(client=client or DummyIpsClient(), settings=settings)


def test_create_cita_uses_institucion_route() -> None:
    client = DummyIpsClient()
    service = build_service('{"1":{"base_url":"http://localhost:4011","api_key":"ips-csh-key"}}', client)

    service.create_cita(
        id_institucion=1,
        payload=CitaCreate(
            tipo_documento="CC",
            numero_documento="123",
            id_prestador=2,
            fecha=date(2026, 4, 1),
            hora=time(8, 0, 0),
        ),
    )

    assert client.calls[0]["path"] == "/fhir/Patient"
    assert client.calls[1]["path"] == "/fhir/PractitionerRole"
    assert client.calls[2]["method"] == "POST"
    assert client.calls[2]["base_url"] == "http://localhost:4011"
    assert client.calls[2]["extra_headers"]["Accept"] == "application/fhir+json"
    assert client.calls[2]["path"] == "/fhir/Appointment"
    assert client.calls[2]["payload"]["slot"][0]["reference"] == "Slot/2-2026-04-01T08:00:00"


def test_update_delete_map_to_reprogramar_cancelar() -> None:
    client = DummyIpsClient()
    service = build_service('{"2":{"base_url":"http://localhost:4012","api_key":"ips-hnh-key"}}', client)

    service.update_cita(
        id_institucion=2,
        id_cita=25,
        payload=CitaUpdate(nueva_fecha_hora_cupo=datetime(2026, 4, 2, 9, 0, 0)),
    )
    service.delete_cita(
        id_institucion=2,
        id_cita=25,
        payload=CitaDelete(motivo="Paciente no asiste"),
    )

    assert client.calls[0]["path"] == "/fhir/Appointment/25"
    assert client.calls[1]["path"] == "/fhir/Appointment/25"
    assert client.calls[2]["path"] == "/fhir/Appointment/25"
    assert client.calls[0]["method"] == "GET"
    assert client.calls[1]["method"] == "PATCH"
    assert client.calls[2]["method"] == "PATCH"


def test_list_citas_filters_by_range_without_sending_exact_date() -> None:
    client = DummyIpsClient()
    service = build_service('{"3":{"base_url":"http://localhost:4013","api_key":"ips-cpc-key"}}', client)
    desde = datetime(2026, 4, 1, 0, 0, 0)
    hasta = datetime(2026, 4, 30, 23, 59, 59)

    rows = service.list_citas(id_institucion=3, tipo_documento="CC", cedula="123", desde=desde, hasta=hasta)

    assert client.calls[0]["path"] == "/fhir/Patient"
    assert client.calls[0]["params"] == {"identifier": "urn:medix:document:cc|123"}
    assert client.calls[1]["path"] == "/fhir/Appointment"
    assert client.calls[1]["params"] == {"patient": "Patient/5"}
    assert len(rows) == 1


def test_list_citas_returns_empty_when_outside_requested_range() -> None:
    client = DummyIpsClient()
    service = build_service('{"3":{"base_url":"http://localhost:4013","api_key":"ips-cpc-key"}}', client)
    desde = datetime(2026, 4, 2, 0, 0, 0)
    hasta = datetime(2026, 4, 30, 23, 59, 59)

    rows = service.list_citas(id_institucion=3, tipo_documento="CC", cedula="123", desde=desde, hasta=hasta)

    assert rows == []


def test_missing_route_returns_404() -> None:
    service = build_service('{"1":{"base_url":"http://localhost:4011","api_key":"ips-csh-key"}}')

    with pytest.raises(HTTPException) as exc:
        service.get_cita(id_institucion=9, id_cita=1)

    assert exc.value.status_code == 404


def test_invalid_routes_json_returns_500() -> None:
    service = build_service("{invalid-json")

    with pytest.raises(HTTPException) as exc:
        service.get_cita(id_institucion=1, id_cita=1)

    assert exc.value.status_code == 500


def test_list_citas_app_by_paciente_doc_uses_fhir_patient_lookup() -> None:
    client = DummyIpsClient()

    class FakeInstitucionService:
        def list_instituciones(self, supabase):  # noqa: ANN001
            return [{"id_institucion": 3, "nombre": "IPS Demo"}]

    class FakeEspecialidadService:
        def list_especialidades(self, supabase):  # noqa: ANN001
            return [{"id_especialidad": 302, "nombre": "Cardiologia"}]

    class FakePacienteService:
        def get_paciente(self, supabase, id_paciente: int):  # noqa: ANN001
            assert id_paciente == 5
            return {"id_paciente": 5, "tipo_documento": "CC", "numero_documento": "123"}

    service = CitaService(
        client=client,
        settings=SimpleNamespace(
            ips_routes_json='{"3":{"base_url":"http://localhost:4013","api_key":"ips-cpc-key"}}',
            ips_timeout_seconds=10,
        ),
        institucion_service=FakeInstitucionService(),
        especialidad_service=FakeEspecialidadService(),
        paciente_service=FakePacienteService(),
    )

    rows = service.list_citas_app_by_paciente_doc(
        supabase=object(),
        id_paciente=5,
        access_token="ok-token",
    )

    assert len(rows) == 1
    assert rows[0].id == 10
    assert rows[0].nombre_institucion == "IPS Demo"
    assert rows[0].especialidad == "Cardiologia"
    assert rows[0].fecha.isoformat() == "2026-04-01"
    assert rows[0].hora.isoformat() == "08:00:00"
    assert client.calls[0]["path"] == "/fhir/Patient"
    assert client.calls[0]["params"] == {"identifier": "urn:medix:document:cc|123"}
    assert client.calls[1]["path"] == "/fhir/Appointment"
    assert client.calls[1]["params"] == {"patient": "Patient/5"}
    assert client.calls[1]["extra_headers"]["Authorization"] == "Bearer ok-token"
