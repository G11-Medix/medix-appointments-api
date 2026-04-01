from datetime import datetime

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.routes import cita as cita_module


def _cita_response(estado: str = "scheduled") -> dict:
    return {
        "id": 10,
        "id_paciente": 1,
        "id_prestador": 1,
        "id_especialidad": 1,
        "fecha_hora_cupo": "2026-04-01T08:00:00",
        "estado": estado,
        "motivo_cancelacion": None if estado != "cancelled" else "Paciente no asiste",
        "fecha_creacion": "2026-03-31T10:00:00",
        "fecha_actualizacion": "2026-03-31T10:00:00",
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    class FakeCitaService:
        def create_cita(self, id_institucion: int, payload):  # noqa: ANN001
            assert id_institucion == 1
            assert payload.id_paciente == 1
            return _cita_response()

        def get_cita(self, id_institucion: int, id_cita: int):
            if id_cita == 404:
                raise HTTPException(status_code=404, detail="Cita no encontrada")
            return _cita_response()

        def list_citas(self, id_institucion: int, *, id_paciente=None, desde=None, hasta=None):  # noqa: ANN001
            assert id_institucion == 1
            assert id_paciente == 1
            assert isinstance(desde, datetime)
            assert isinstance(hasta, datetime)
            return [_cita_response()]

        def update_cita(self, id_institucion: int, id_cita: int, payload):  # noqa: ANN001
            if id_cita == 409:
                raise HTTPException(status_code=409, detail="Solo las citas programadas pueden reprogramarse")
            assert id_institucion == 1
            assert payload.nueva_fecha_hora_cupo
            return _cita_response()

        def delete_cita(self, id_institucion: int, id_cita: int, payload):  # noqa: ANN001
            if id_cita == 502:
                raise HTTPException(status_code=502, detail="No fue posible conectar con la IPS")
            if id_cita == 504:
                raise HTTPException(status_code=504, detail="Timeout al consultar IPS")
            assert id_institucion == 1
            assert payload.motivo is not None
            return _cita_response(estado="cancelled")

    monkeypatch.setattr(cita_module, "cita_service", FakeCitaService())
    app = FastAPI()
    app.include_router(cita_module.router, prefix="/api")
    return TestClient(app)


def test_cita_crud_happy_path(client: TestClient) -> None:
    create_resp = client.post(
        "/api/instituciones/1/citas/",
        json={"id_paciente": 1, "id_prestador": 1, "fecha_hora_cupo": "2026-04-01T08:00:00"},
    )
    assert create_resp.status_code == 201

    get_resp = client.get("/api/instituciones/1/citas/10")
    assert get_resp.status_code == 200

    list_resp = client.get(
        "/api/instituciones/1/citas/",
        params={"id_paciente": 1, "desde": "2026-04-01T00:00:00", "hasta": "2026-04-30T23:59:59"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    update_resp = client.put(
        "/api/instituciones/1/citas/10",
        json={"nueva_fecha_hora_cupo": "2026-04-02T09:00:00"},
    )
    assert update_resp.status_code == 200

    delete_resp = client.request(
        "DELETE",
        "/api/instituciones/1/citas/10",
        json={"motivo": "Paciente no asiste"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["estado"] == "cancelled"


def test_route_propagates_404_409(client: TestClient) -> None:
    not_found = client.get("/api/instituciones/1/citas/404")
    assert not_found.status_code == 404

    conflict = client.put(
        "/api/instituciones/1/citas/409",
        json={"nueva_fecha_hora_cupo": "2026-04-02T09:00:00"},
    )
    assert conflict.status_code == 409


def test_route_propagates_502_504(client: TestClient) -> None:
    bad_gateway = client.request(
        "DELETE",
        "/api/instituciones/1/citas/502",
        json={"motivo": "Paciente no asiste"},
    )
    assert bad_gateway.status_code == 502

    timeout = client.request(
        "DELETE",
        "/api/instituciones/1/citas/504",
        json={"motivo": "Paciente no asiste"},
    )
    assert timeout.status_code == 504
