from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import auth as auth_module
from app.api.dependencies.auth import AuthenticatedUserContext, require_active_user


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


@pytest.fixture
def secure_client() -> TestClient:
    app = FastAPI()

    @app.get("/secure")
    def secure(_auth: AuthenticatedUserContext = Depends(require_active_user)) -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_missing_token_returns_401(monkeypatch: pytest.MonkeyPatch, secure_client: TestClient) -> None:
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: FakeSupabase(users={}, token_to_user_id={}))

    response = secure_client.get("/secure")

    assert response.status_code == 401


def test_malformed_header_returns_401(monkeypatch: pytest.MonkeyPatch, secure_client: TestClient) -> None:
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: FakeSupabase(users={}, token_to_user_id={}))

    response = secure_client.get("/secure", headers={"Authorization": "Basic abc"})

    assert response.status_code == 401


def test_invalid_token_returns_401(monkeypatch: pytest.MonkeyPatch, secure_client: TestClient) -> None:
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: FakeSupabase(users={}, token_to_user_id={}))

    response = secure_client.get("/secure", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401


def test_valid_token_without_usuario_returns_403(monkeypatch: pytest.MonkeyPatch, secure_client: TestClient) -> None:
    user_id = str(uuid4())
    fake_supabase = FakeSupabase(users={}, token_to_user_id={"ok-token": user_id})
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: fake_supabase)

    response = secure_client.get("/secure", headers={"Authorization": "Bearer ok-token"})

    assert response.status_code == 403


def test_valid_token_with_inactive_usuario_returns_403(
    monkeypatch: pytest.MonkeyPatch,
    secure_client: TestClient,
) -> None:
    user_id = str(uuid4())
    fake_supabase = FakeSupabase(
        users={user_id: {"id_usuario": user_id, "rol": "PACIENTE", "estado": "INACTIVO"}},
        token_to_user_id={"ok-token": user_id},
    )
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: fake_supabase)

    response = secure_client.get("/secure", headers={"Authorization": "Bearer ok-token"})

    assert response.status_code == 403


def test_valid_token_with_active_usuario_allows_access(
    monkeypatch: pytest.MonkeyPatch,
    secure_client: TestClient,
) -> None:
    user_id = str(uuid4())
    fake_supabase = FakeSupabase(
        users={user_id: {"id_usuario": user_id, "rol": "PACIENTE", "estado": "ACTIVO"}},
        token_to_user_id={"ok-token": user_id},
    )
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: fake_supabase)

    response = secure_client.get("/secure", headers={"Authorization": "Bearer ok-token"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
