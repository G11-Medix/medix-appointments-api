from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import auth as auth_module
from app.api.router import api_router
from app.api.routes import auth as auth_routes_module
from app.api.routes.auth import public_router as auth_public_router


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


class FakeAuthAccessService:
    def __init__(self) -> None:
        self.last_grant_payload: dict | None = None
        self.last_eligibility_phone: str | None = None

    def check_phone_login_eligibility(self, supabase, admin_supabase, telefono: str):  # noqa: ANN001
        self.last_eligibility_phone = telefono
        return {
            "authorized": True,
            "reason": None,
            "paciente": {
                "id_paciente": 123,
                "id_usuario": str(uuid4()),
                "telefono": telefono,
                "estado": "ACTIVO",
            },
        }

    def grant_patient_access(self, supabase, admin_supabase, id_paciente: int, telefono: str, rol: str):  # noqa: ANN001
        self.last_grant_payload = {
            "id_paciente": id_paciente,
            "telefono": telefono,
            "rol": rol,
        }
        return {
            "id_paciente": id_paciente,
            "id_usuario": str(uuid4()),
            "telefono": telefono,
            "rol": rol,
            "estado_usuario": "ACTIVO",
            "estado_paciente": "ACTIVO",
            "auth_user_created": True,
        }


@pytest.fixture
def auth_routes_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, FakeAuthAccessService]:
    user_id = str(uuid4())
    fake_supabase = FakeSupabase(
        users={user_id: {"id_usuario": user_id, "rol": "PACIENTE", "estado": "ACTIVO"}},
        token_to_user_id={"ok-token": user_id},
    )
    fake_service = FakeAuthAccessService()

    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: fake_supabase)

    app = FastAPI()
    app.dependency_overrides[auth_routes_module.get_auth_access_service] = lambda: fake_service
    app.dependency_overrides[auth_routes_module.get_supabase_client] = lambda: object()
    app.dependency_overrides[auth_routes_module.get_supabase_admin_client] = lambda: object()
    app.include_router(auth_public_router)
    app.include_router(api_router, prefix="/api")
    return TestClient(app), fake_service


def test_public_auth_eligibility_route_is_accessible_without_token(
    auth_routes_client: tuple[TestClient, FakeAuthAccessService],
) -> None:
    client, fake_service = auth_routes_client

    response = client.get("/auth/eligibility/+573001234567")

    assert response.status_code == 200
    assert response.json()["authorized"] is True
    assert set(response.json()["paciente"].keys()) == {"id_paciente", "id_usuario", "telefono", "estado"}
    assert fake_service.last_eligibility_phone == "+573001234567"


def test_public_auth_eligibility_route_accepts_phone_without_plus(
    auth_routes_client: tuple[TestClient, FakeAuthAccessService],
) -> None:
    client, fake_service = auth_routes_client

    response = client.get("/auth/eligibility/573001234567")

    assert response.status_code == 200
    assert response.json()["authorized"] is True
    assert fake_service.last_eligibility_phone == "573001234567"


def test_admin_grant_access_requires_admin_role(auth_routes_client: tuple[TestClient, FakeAuthAccessService]) -> None:
    client, fake_service = auth_routes_client

    response = client.post(
        "/api/admin/pacientes/12/grant-access",
        headers={"Authorization": "Bearer ok-token"},
        json={"telefono": "+573001234567", "rol": "PACIENTE"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Usuario sin permisos administrativos"
    assert fake_service.last_grant_payload is None
