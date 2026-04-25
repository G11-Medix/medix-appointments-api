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
        "nombre_prestador": "Dr. Juan Perez",
        "id_especialidad": 1,
        "fecha_hora_cupo": "2026-04-01T08:00:00",
        "estado": estado,
        "motivo_cancelacion": None if estado != "cancelled" else "Paciente no asiste",
        "fecha_creacion": "2026-03-31T10:00:00",
        "fecha_actualizacion": "2026-03-31T10:00:00",
    }


def _cita_ips_response(estado: str = "scheduled") -> dict:
    return {
        "id": 10,
        "nombre_paciente": "Ana Ruiz",
        "cedula_paciente": "123",
        "id_prestador": 1,
        "nombre_prestador": "Dr. Juan Perez",
        "especialidad": "Cardiologia",
        "fecha": "2026-04-01",
        "hora": "08:00:00",
        "estado_cita": estado,
        "motivo_cancelacion": None if estado != "cancelled" else "Paciente no asiste",
        "fecha_creacion": "2026-03-31T10:00:00",
        "fecha_actualizacion": "2026-03-31T10:00:00",
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    class FakeCitaService:
        def create_cita(self, id_institucion: int, payload, access_token: str | None = None):  # noqa: ANN001
            assert id_institucion == 1
            assert payload.tipo_documento == "CC"
            assert payload.numero_documento == "123"
            assert str(payload.fecha) == "2026-04-01"
            assert payload.hora.strftime("%H:%M:%S") == "08:00:00"
            assert access_token == "ok-token"
            return _cita_response()

        def get_cita(self, id_institucion: int, id_cita: int, access_token: str | None = None):
            if id_cita == 404:
                raise HTTPException(status_code=404, detail="Cita no encontrada")
            assert access_token == "ok-token"
            return _cita_response()

        def get_cita_ips(self, supabase, id_institucion: int, id_cita: int, access_token: str | None = None):  # noqa: ANN001
            if id_cita == 404:
                raise HTTPException(status_code=404, detail="Cita no encontrada")
            assert supabase is not None
            assert id_institucion == 1
            assert access_token == "ok-token"
            return _cita_ips_response()

        def get_cita_confirmacion(self, supabase, id_institucion: int, id_cita: int, access_token: str | None = None):  # noqa: ANN001
            assert supabase is not None
            assert id_institucion == 1
            assert id_cita == 10
            assert access_token == "ok-token"
            return {
                "doctor": "Dr. Juan Perez",
                "fecha": "2026-04-01T08:00:00",
                "institucion": "Medix Health Center",
                "direccion": "Bogota, Colombia",
                "latitud": 4.7110,
                "longitud": -74.0721,
                "estado": "scheduled",
                "recomendacion": {
                    "id": 1,
                    "created_at": "2026-04-01T10:00:00+00:00",
                    "institucion_id": 1,
                    "especialidad_id": 1,
                    "codigo": "CARDIO-PREP",
                    "recomendaciones": {"items": ["Llegar 20 minutos antes"]},
                    "prioridad": 2,
                    "activa": True,
                },
            }

        def list_citas(self, id_institucion: int, *, tipo_documento=None, cedula=None, desde=None, hasta=None, access_token: str | None = None):  # noqa: ANN001
            assert id_institucion == 1
            assert tipo_documento == "CC"
            assert cedula == "123"
            assert isinstance(desde, datetime)
            assert isinstance(hasta, datetime)
            assert access_token == "ok-token"
            return [_cita_response()]

        def list_citas_ips(self, supabase, id_institucion: int, *, tipo_documento=None, cedula=None, desde=None, hasta=None, access_token: str | None = None):  # noqa: ANN001
            assert supabase is not None
            assert id_institucion == 1
            assert tipo_documento == "CC"
            assert cedula == "123"
            assert isinstance(desde, datetime)
            assert isinstance(hasta, datetime)
            assert access_token == "ok-token"
            return [_cita_ips_response()]

        def update_cita(self, id_institucion: int, id_cita: int, payload, access_token: str | None = None):  # noqa: ANN001
            if id_cita == 409:
                raise HTTPException(status_code=409, detail="Solo las citas programadas pueden reprogramarse")
            assert id_institucion == 1
            assert payload.nueva_fecha_hora_cupo
            assert access_token == "ok-token"
            return _cita_response()

        def delete_cita(self, id_institucion: int, id_cita: int, payload, access_token: str | None = None):  # noqa: ANN001
            if id_cita == 502:
                raise HTTPException(status_code=502, detail="No fue posible conectar con la IPS")
            if id_cita == 504:
                raise HTTPException(status_code=504, detail="Timeout al consultar IPS")
            assert id_institucion == 1
            assert payload.motivo is not None
            assert access_token == "ok-token"
            return _cita_response(estado="cancelled")

        def list_citas_app_by_paciente_doc(self, supabase, id_paciente: int, access_token: str | None = None):  # noqa: ANN001
            assert id_paciente == 4
            assert access_token == "ok-token"
            assert supabase is not None
            return [
                {
                    "id": 10,
                    "id_institucion": 1,
                    "nombre_institucion": "Clinica Central",
                    "logo_url": "https://example.com/clinica-central.png",
                    "especialidad": "Medicina general",
                    "estado": "scheduled",
                    "fecha": "2026-04-01",
                    "hora": "08:00:00",
                }
            ]

    monkeypatch.setattr(cita_module, "get_access_token_from_state", lambda _request: "ok-token")
    app = FastAPI()
    app.dependency_overrides[cita_module.get_cita_service] = lambda: FakeCitaService()
    app.dependency_overrides[cita_module.get_supabase_client] = lambda: object()
    app.include_router(cita_module.router, prefix="/api")
    app.include_router(cita_module.patient_router, prefix="/api")
    return TestClient(app)


def test_cita_crud_happy_path(client: TestClient) -> None:
    create_resp = client.post(
        "/api/instituciones/1/citas/",
        json={
            "tipo_documento": "CC",
            "numero_documento": "123",
            "id_prestador": 1,
            "fecha": "2026-04-01",
            "hora": "08:00:00",
        },
    )
    assert create_resp.status_code == 201

    get_resp = client.get("/api/instituciones/1/citas/10")
    assert get_resp.status_code == 200
    assert get_resp.json() == _cita_ips_response()

    confirmation_resp = client.get("/api/instituciones/1/citas/10/confirmacion")
    assert confirmation_resp.status_code == 200
    assert confirmation_resp.json()["doctor"] == "Dr. Juan Perez"
    assert confirmation_resp.json()["recomendacion"]["codigo"] == "CARDIO-PREP"

    list_resp = client.get(
        "/api/instituciones/1/citas/",
        params={"tipo_documento": "CC", "cedula": "123", "desde": "2026-04-01T00:00:00", "hasta": "2026-04-30T23:59:59"},
    )
    assert list_resp.status_code == 200
    assert list_resp.json() == [_cita_ips_response()]

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


def test_patient_citas_route_passes_access_token(client: TestClient) -> None:
    response = client.get("/api/pacientes/4/citas")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 10,
            "id_institucion": 1,
            "nombre_ins": "Clinica Central",
            "logo_url": "https://example.com/clinica-central.png",
            "especialidad": "Medicina general",
            "estado": "scheduled",
            "fecha": "2026-04-01",
            "hora": "08:00:00",
        }
    ]
