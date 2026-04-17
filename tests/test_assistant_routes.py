from datetime import date, time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import auth as auth_module
from app.api.router import api_router
from app.api.routes import assistant as assistant_module
from app.api.routes import institucion as institucion_module
from app.api.routes import paciente as paciente_module


class FakeAuthClient:
    def __init__(self, token_to_user_id: dict[str, str]) -> None:
        self.token_to_user_id = token_to_user_id

    def get_user(self, token: str):
        user_id = self.token_to_user_id[token]
        return type("Resp", (), {"user": type("User", (), {"id": user_id})()})()


class FakeUsuarioQuery:
    def __init__(self, users: dict[str, dict]) -> None:
        self.users = users
        self._user_id = ""

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, _field: str, value: str):
        self._user_id = value
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        row = self.users.get(self._user_id)
        return type("Result", (), {"data": [row] if row else []})()


class FakeSupabase:
    def __init__(self, users: dict[str, dict], token_to_user_id: dict[str, str]) -> None:
        self._users = users
        self.auth = FakeAuthClient(token_to_user_id)

    def table(self, name: str):
        assert name == "Usuario"
        return FakeUsuarioQuery(self._users)


class FakeEspecialidadService:
    def list_especialidades(self, supabase, limit: int = 50):  # noqa: ANN001
        assert limit == 50
        assert supabase is not None
        return [{"id_especialidad": 1, "nombre": "Cardiologia", "codigo_reps": 302}]


class FakeAssistantService:
    def list_instituciones_by_especialidad(self, codigo_reps: int, access_token: str | None = None):
        assert codigo_reps == 302
        assert access_token == "ok-token"
        return [{"id_institucion": 1, "nombre": "IPS Demo", "estado": "ACTIVA", "especialidades": [302]}]

    def get_disponibilidad(
        self,
        id_institucion: int,
        codigo_reps: int,
        fecha_desde: date,
        dias: int,
        access_token: str | None = None,
    ):
        assert (id_institucion, codigo_reps, fecha_desde, dias) == (1, 302, date(2026, 4, 10), 7)
        assert access_token == "ok-token"
        return {
            "id_institucion": 1,
            "nombre_institucion": "IPS Demo",
            "codigo_reps": 302,
            "disponibilidad": [
                {
                    "fecha": "2026-04-10",
                    "slots": [
                        {
                            "hora": "10:00",
                            "fecha_hora": "2026-04-10T10:00:00",
                            "id_prestador": 5,
                            "nombre_prestador": "Dr. Perez",
                        }
                    ],
                }
            ],
        }

    def schedule_appointment(
        self,
        id_paciente: int,
        id_institucion: int,
        codigo_reps: int,
        fecha: date,
        hora: time,
        access_token: str | None = None,
    ):
        assert (id_paciente, id_institucion, codigo_reps, fecha, hora) == (
            12,
            1,
            302,
            date(2026, 4, 10),
            time(10, 0, 0),
        )
        assert access_token == "ok-token"
        return {
            "mensaje": "Cita agendada correctamente",
            "cita": {
                "id": 100,
                "id_paciente": 12,
                "id_prestador": 5,
                "id_especialidad": 1,
                "fecha_hora_cupo": "2026-04-10T10:00:00",
                "estado": "RESERVADA",
                "motivo_cancelacion": None,
                "fecha_creacion": "2026-04-01T08:00:00",
                "fecha_actualizacion": "2026-04-01T08:00:00",
            },
        }

    def cancel_appointment(self, id_cita: int, id_institucion: int, motivo: str | None, access_token: str | None = None):
        assert (id_cita, id_institucion, motivo) == (100, 1, "No puedo asistir")
        assert access_token == "ok-token"
        return {
            "mensaje": "Cita cancelada correctamente",
            "cita": {
                "id": 100,
                "id_paciente": 12,
                "id_prestador": 5,
                "id_especialidad": 1,
                "fecha_hora_cupo": "2026-04-10T10:00:00",
                "estado": "CANCELADA",
                "motivo_cancelacion": "No puedo asistir",
                "fecha_creacion": "2026-04-01T08:00:00",
                "fecha_actualizacion": "2026-04-01T08:00:00",
            },
        }

    def reschedule_appointment(
        self,
        id_cita: int,
        id_institucion: int,
        codigo_reps: int,
        nueva_fecha: date,
        nueva_hora: time,
        access_token: str | None = None,
    ):
        assert (id_cita, id_institucion, codigo_reps, nueva_fecha, nueva_hora) == (
            100,
            1,
            302,
            date(2026, 4, 11),
            time(14, 0, 0),
        )
        assert access_token == "ok-token"
        return {
            "mensaje": "Cita reprogramada correctamente",
            "cita": {
                "id": 100,
                "id_paciente": 12,
                "id_prestador": 5,
                "id_especialidad": 1,
                "fecha_hora_cupo": "2026-04-11T14:00:00",
                "estado": "RESERVADA",
                "motivo_cancelacion": None,
                "fecha_creacion": "2026-04-01T08:00:00",
                "fecha_actualizacion": "2026-04-01T08:00:00",
            },
        }

    def find_patient_by_document(self, tipo_documento: str, numero_documento: str, access_token: str | None = None):
        assert (tipo_documento, numero_documento) == ("CC", "123")
        assert access_token == "ok-token"
        return {
            "id_paciente": 12,
            "tipo_documento": "CC",
            "numero_documento": "123",
            "nombres": "Ana",
            "apellidos": "Perez",
            "fecha_nacimiento": "2000-01-01",
            "telefono": "3000000000",
            "correo": "ana@example.com",
            "estado": "ACTIVO",
            "fecha_creacion": "2026-04-01T08:00:00",
        }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    user_id = "11111111-1111-1111-1111-111111111111"
    fake_supabase = FakeSupabase(
        users={user_id: {"id_usuario": user_id, "rol": "PACIENTE", "estado": "ACTIVO"}},
        token_to_user_id={"ok-token": user_id},
    )
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: fake_supabase)

    app = FastAPI()
    fake_service = FakeAssistantService()
    app.dependency_overrides[assistant_module.get_assistant_service] = lambda: fake_service
    app.dependency_overrides[assistant_module.get_especialidad_service] = lambda: FakeEspecialidadService()
    app.dependency_overrides[assistant_module.get_supabase_client] = lambda: object()
    app.dependency_overrides[institucion_module.get_assistant_service] = lambda: fake_service
    app.dependency_overrides[paciente_module.get_assistant_service] = lambda: fake_service
    app.include_router(api_router, prefix="/api")
    return TestClient(app)


def test_assistant_endpoints(client: TestClient) -> None:
    headers = {"Authorization": "Bearer ok-token"}

    specialties = client.get("/api/especialidades", headers=headers)
    institutions = client.get("/api/instituciones", headers=headers, params={"codigo_reps": 302})
    availability = client.get(
        "/api/instituciones/1/disponibilidad",
        headers=headers,
        params={"codigo_reps": 302, "fecha_desde": "2026-04-10", "dias": 7},
    )
    patient = client.get(
        "/api/pacientes/buscar",
        headers=headers,
        params={"tipo_documento": "CC", "numero_documento": "123"},
    )
    scheduled = client.post(
        "/api/citas/agendar",
        headers=headers,
        json={
            "id_paciente": 12,
            "id_institucion": 1,
            "codigo_reps": 302,
            "fecha": "2026-04-10",
            "hora": "10:00:00",
        },
    )
    cancelled = client.patch(
        "/api/citas/100/cancelar",
        headers=headers,
        json={"id_institucion": 1, "motivo": "No puedo asistir"},
    )
    rescheduled = client.patch(
        "/api/citas/100/reprogramar",
        headers=headers,
        json={
            "id_institucion": 1,
            "codigo_reps": 302,
            "nueva_fecha": "2026-04-11",
            "nueva_hora": "14:00:00",
        },
    )

    assert specialties.status_code == 200
    assert institutions.status_code == 200
    assert availability.status_code == 200
    assert patient.status_code == 200
    assert scheduled.status_code == 201
    assert cancelled.status_code == 200
    assert rescheduled.status_code == 200
    assert specialties.json()[0] == {"id_especialidad": 1, "nombre": "Cardiologia", "codigo_reps": 302}
    assert institutions.json()[0]["estado"] == "ACTIVA"
    assert availability.json()["disponibilidad"][0]["slots"][0]["hora"] == "10:00"
    assert patient.json()["id_paciente"] == 12
    assert scheduled.json()["cita"]["estado"] == "RESERVADA"
    assert cancelled.json()["cita"]["estado"] == "CANCELADA"
