from datetime import datetime
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
        return {
            "id": 10,
            "id_paciente": 1,
            "id_prestador": 1,
            "id_especialidad": 1,
            "fecha_hora_cupo": "2026-04-01T08:00:00",
            "estado": "scheduled",
            "motivo_cancelacion": None,
            "fecha_creacion": "2026-03-31T10:00:00",
            "fecha_actualizacion": "2026-03-31T10:00:00",
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
        payload=CitaCreate(id_paciente=1, id_prestador=2, fecha_hora_cupo=datetime(2026, 4, 1, 8, 0, 0)),
    )

    assert client.calls[0]["method"] == "POST"
    assert client.calls[0]["base_url"] == "http://localhost:4011"
    assert client.calls[0]["api_key"] == "ips-csh-key"
    assert client.calls[0]["path"] == "/api/v1/citas"


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

    assert client.calls[0]["path"] == "/api/v1/citas/25/reprogramar"
    assert client.calls[1]["path"] == "/api/v1/citas/25/cancelar"
    assert client.calls[0]["method"] == "PATCH"
    assert client.calls[1]["method"] == "PATCH"


def test_list_citas_sends_query_params() -> None:
    client = DummyIpsClient()
    service = build_service('{"3":{"base_url":"http://localhost:4013","api_key":"ips-cpc-key"}}', client)
    desde = datetime(2026, 4, 1, 0, 0, 0)
    hasta = datetime(2026, 4, 30, 23, 59, 59)

    service.list_citas(id_institucion=3, id_paciente=5, desde=desde, hasta=hasta)

    assert client.calls[0]["path"] == "/api/v1/citas"
    assert client.calls[0]["params"] == {
        "id_paciente": 5,
        "desde": "2026-04-01T00:00:00",
        "hasta": "2026-04-30T23:59:59",
    }


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
