from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import auth as auth_module
from app.api.routes import assistant as assistant_module
from app.api.routes.paciente import registration_router as paciente_registration_router
from app.api.router import api_router
from app.api.routes import cita as cita_module
from app.api.routes import institucion as institucion_module
from app.api.routes import paciente as paciente_module


class FakeAuthClient:
    def __init__(self, token_to_user_id: dict[str, str]) -> None:
        self.token_to_user_id = token_to_user_id

    def get_user(self, token: str):  # noqa: ANN001
        user_id = self.token_to_user_id.get(token)
        if not user_id:
            raise ValueError("invalid token")
        return SimpleNamespace(user=SimpleNamespace(id=user_id))


class FakeUsuarioQuery:
    def __init__(self, users: dict[str, dict]) -> None:
        self.users = users
        self._user_id = ""

    def select(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
        return self

    def eq(self, _field: str, value: str):
        self._user_id = value
        return self

    def limit(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
        return self

    def execute(self):
        row = self.users.get(self._user_id)
        return SimpleNamespace(data=[row] if row else [])


class FakeSupabase:
    def __init__(self, users: dict[str, dict], token_to_user_id: dict[str, str]) -> None:
        self._users = users
        self.auth = FakeAuthClient(token_to_user_id=token_to_user_id)

    def table(self, name: str) -> FakeUsuarioQuery:
        assert name == "Usuario"
        return FakeUsuarioQuery(self._users)


def _build_cita_response(estado: str = "scheduled") -> dict:
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
def auth_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str, object]:
    auth_user_id = str(uuid4())
    fake_supabase = FakeSupabase(
        users={auth_user_id: {"id_usuario": auth_user_id, "rol": "PACIENTE", "estado": "ACTIVO"}},
        token_to_user_id={"ok-token": auth_user_id},
    )
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: fake_supabase)

    class FakeInstitucionService:
        def list_instituciones(self, supabase, limit: int = 20):  # noqa: ANN001
            assert limit == 20
            return [
                {
                    "id_institucion": 1,
                    "nombre": "Hospital Demo",
                    "nit": "900000000-1",
                    "direccion": "Calle 1",
                    "telefono": "3000000000",
                    "estado": "ACTIVO",
                    "longitud": -74.0721,
                    "latitud": 4.711,
                    "logo_url": "https://example.com/logo.png",
                }
            ]

    class FakeEspecialidadService:
        def list_especialidades(self, supabase, limit: int = 50):  # noqa: ANN001
            assert limit == 50
            return [{"id_especialidad": 1, "nombre": "Cardiologia", "codigo_reps": 302}]

    class FakePacienteService:
        def __init__(self) -> None:
            self.last_create: dict | None = None
            self.last_update: dict | None = None

        def list_pacientes(self, supabase, limit: int = 20):  # noqa: ANN001
            assert limit == 20
            return []

        def get_paciente(self, supabase, id_paciente: int):  # noqa: ANN001
            if id_paciente == 404:
                return None
            return {
                "id_paciente": id_paciente,
                "tipo_documento": "CC",
                "numero_documento": "123",
                "nombres": "Ana",
                "apellidos": "Perez",
                "fecha_nacimiento": "2000-01-01",
                "telefono": "3000000000",
                "correo": "ana@example.com",
                "estado": "ACTIVO",
                "fecha_creacion": "2026-03-31T10:00:00",
                "id_usuario": auth_user_id,
                "id_eps": 1,
            }

        def create_paciente(self, supabase, payload, authenticated_user_id=None):  # noqa: ANN001
            self.last_create = {
                "authenticated_user_id": authenticated_user_id,
            }
            return {
                "id_paciente": 10,
                "tipo_documento": payload.tipo_documento,
                "numero_documento": payload.numero_documento,
                "nombres": payload.nombres,
                "apellidos": payload.apellidos,
                "fecha_nacimiento": payload.fecha_nacimiento.isoformat(),
                "telefono": payload.telefono,
                "correo": payload.correo,
                "estado": payload.estado,
                "fecha_creacion": "2026-03-31T10:00:00",
                "id_usuario": authenticated_user_id,
                "id_eps": payload.id_eps,
            }

        def update_paciente(self, supabase, id_paciente: int, payload, authenticated_user_id=None):  # noqa: ANN001
            self.last_update = {
                "id_paciente": id_paciente,
                "payload_id_usuario": str(payload.id_usuario) if payload.id_usuario else None,
                "authenticated_user_id": authenticated_user_id,
            }
            row = self.get_paciente(supabase=supabase, id_paciente=id_paciente)
            if not row:
                return None
            row["id_usuario"] = authenticated_user_id
            row["nombres"] = payload.nombres or row["nombres"]
            return row

        def delete_paciente(self, supabase, id_paciente: int):  # noqa: ANN001
            return None

    class FakeCitaService:
        def create_cita(self, id_institucion: int, payload, access_token=None):  # noqa: ANN001
            assert id_institucion == 1
            assert payload.id_paciente == 1
            assert access_token == "ok-token"
            return _build_cita_response()

        def get_cita(self, id_institucion: int, id_cita: int, access_token=None):  # noqa: ANN001
            assert id_institucion == 1
            assert id_cita == 10
            assert access_token == "ok-token"
            return _build_cita_response()

        def list_citas(self, id_institucion: int, *, id_paciente=None, desde=None, hasta=None, access_token=None):  # noqa: ANN001
            assert id_institucion == 1
            assert access_token == "ok-token"
            return [_build_cita_response()]

        def update_cita(self, id_institucion: int, id_cita: int, payload, access_token=None):  # noqa: ANN001
            assert id_institucion == 1
            assert id_cita == 10
            assert isinstance(payload.nueva_fecha_hora_cupo, datetime)
            assert access_token == "ok-token"
            return _build_cita_response()

        def delete_cita(self, id_institucion: int, id_cita: int, payload, access_token=None):  # noqa: ANN001
            assert id_institucion == 1
            assert id_cita == 10
            assert payload.motivo is not None
            assert access_token == "ok-token"
            return _build_cita_response(estado="cancelled")

    fake_paciente_service = FakePacienteService()

    app = FastAPI()
    app.dependency_overrides[assistant_module.get_especialidad_service] = lambda: FakeEspecialidadService()
    app.dependency_overrides[assistant_module.get_supabase_client] = lambda: object()
    app.dependency_overrides[institucion_module.get_institucion_service] = lambda: FakeInstitucionService()
    app.dependency_overrides[institucion_module.get_supabase_client] = lambda: object()
    app.dependency_overrides[paciente_module.get_paciente_service] = lambda: fake_paciente_service
    app.dependency_overrides[paciente_module.get_supabase_client] = lambda: object()
    app.dependency_overrides[cita_module.get_cita_service] = lambda: FakeCitaService()
    app.dependency_overrides[cita_module.get_supabase_client] = lambda: object()
    app.include_router(paciente_registration_router, prefix="/api")
    app.include_router(api_router, prefix="/api")
    client = TestClient(app)
    return client, auth_user_id, fake_paciente_service


def test_api_requires_token_in_each_router(auth_client: tuple[TestClient, str, object]) -> None:
    client, _, _service = auth_client

    institucion_resp = client.get("/api/instituciones/")
    paciente_resp = client.get("/api/pacientes/")
    cita_resp = client.get("/api/instituciones/1/citas/10")

    assert institucion_resp.status_code == 401
    assert paciente_resp.status_code == 401
    assert cita_resp.status_code == 401


def test_api_accepts_valid_token_in_representative_endpoints(auth_client: tuple[TestClient, str, object]) -> None:
    client, _, _service = auth_client
    headers = {"Authorization": "Bearer ok-token"}

    institucion_resp = client.get("/api/instituciones/", headers=headers)
    cita_resp = client.get("/api/instituciones/1/citas/10", headers=headers)
    especialidad_resp = client.get("/api/especialidades", headers=headers)

    assert institucion_resp.status_code == 200
    assert cita_resp.status_code == 200
    assert especialidad_resp.status_code == 200
    assert institucion_resp.json()[0] == {
        "id_institucion": 1,
        "nombre": "Hospital Demo",
        "nit": "900000000-1",
        "direccion": "Calle 1",
        "telefono": "3000000000",
        "estado": "ACTIVO",
        "longitud": -74.0721,
        "latitud": 4.711,
        "logo_url": "https://example.com/logo.png",
    }
    assert especialidad_resp.json()[0] == {
        "id_especialidad": 1,
        "nombre": "Cardiologia",
        "codigo_reps": 302,
    }


def test_paciente_create_forces_id_usuario_from_token(
    auth_client: tuple[TestClient, str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, auth_user_id, captured_service = auth_client
    headers = {"Authorization": "Bearer ok-token"}
    assert hasattr(captured_service, "last_create")

    response = client.post(
        "/api/pacientes/",
        headers=headers,
        json={
            "tipo_documento": "CC",
            "numero_documento": "123",
            "nombres": "Ana",
            "apellidos": "Perez",
            "fecha_nacimiento": "2000-01-01",
            "telefono": "3000000000",
            "correo": "ana@example.com",
            "estado": "ACTIVO",
            "id_eps": 1,
        },
    )

    assert response.status_code == 201
    assert response.json()["id_usuario"] == auth_user_id
    assert captured_service.last_create["authenticated_user_id"] == auth_user_id


def test_paciente_create_rejects_extra_id_usuario_field(auth_client: tuple[TestClient, str, object]) -> None:
    client, _, _service = auth_client

    response = client.post(
        "/api/pacientes/",
        headers={"Authorization": "Bearer ok-token"},
        json={
            "tipo_documento": "CC",
            "numero_documento": "123",
            "nombres": "Ana",
            "apellidos": "Perez",
            "fecha_nacimiento": "2000-01-01",
            "telefono": "3000000000",
            "correo": "ana@example.com",
            "estado": "ACTIVO",
            "id_eps": 1,
            "id_usuario": str(uuid4()),
        },
    )

    assert response.status_code == 422


def test_paciente_update_forces_id_usuario_from_token(auth_client: tuple[TestClient, str, object]) -> None:
    client, auth_user_id, captured_service = auth_client
    headers = {"Authorization": "Bearer ok-token"}
    attacker_user_id = str(uuid4())
    assert hasattr(captured_service, "last_update")

    response = client.put(
        "/api/pacientes/10",
        headers=headers,
        json={"nombres": "Ana Maria", "id_usuario": attacker_user_id},
    )

    assert response.status_code == 200
    assert response.json()["id_usuario"] == auth_user_id
    assert captured_service.last_update["payload_id_usuario"] == attacker_user_id
    assert captured_service.last_update["authenticated_user_id"] == auth_user_id


def test_paciente_create_allows_valid_token_without_existing_usuario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_user_id = str(uuid4())
    fake_supabase = FakeSupabase(
        users={},
        token_to_user_id={"ok-token": auth_user_id},
    )
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: fake_supabase)

    class FakePacienteService:
        def __init__(self) -> None:
            self.last_create: dict | None = None

        def create_paciente(self, supabase, payload, authenticated_user_id=None):  # noqa: ANN001
            self.last_create = {
                "authenticated_user_id": authenticated_user_id,
            }
            return {
                "id_paciente": 10,
                "tipo_documento": payload.tipo_documento,
                "numero_documento": payload.numero_documento,
                "nombres": payload.nombres,
                "apellidos": payload.apellidos,
                "fecha_nacimiento": payload.fecha_nacimiento.isoformat(),
                "telefono": payload.telefono,
                "correo": payload.correo,
                "estado": payload.estado,
                "fecha_creacion": "2026-03-31T10:00:00",
                "id_usuario": authenticated_user_id,
                "id_eps": payload.id_eps,
            }

    fake_paciente_service = FakePacienteService()

    app = FastAPI()
    app.dependency_overrides[paciente_module.get_paciente_service] = lambda: fake_paciente_service
    app.dependency_overrides[paciente_module.get_supabase_client] = lambda: object()
    app.include_router(paciente_registration_router, prefix="/api")
    client = TestClient(app)

    response = client.post(
        "/api/pacientes/",
        headers={"Authorization": "Bearer ok-token"},
        json={
            "tipo_documento": "CC",
            "numero_documento": "123",
            "nombres": "Ana",
            "apellidos": "Perez",
            "fecha_nacimiento": "2000-01-01",
            "telefono": "3000000000",
            "correo": "ana@example.com",
            "estado": "ACTIVO",
            "id_eps": 1,
        },
    )

    assert response.status_code == 201
    assert response.json()["id_usuario"] == auth_user_id
    assert fake_paciente_service.last_create["authenticated_user_id"] == auth_user_id
