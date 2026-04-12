import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import eps as eps_module


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    class FakeEpsService:
        def list_eps(self, supabase, limit: int = 20):  # noqa: ANN001
            assert supabase == "fake-supabase"
            assert limit == 2
            return [
                {"id_eps": 1, "nombre": "Nueva EPS", "codigo": "EPS001", "estado": "ACTIVO"},
                {"id_eps": 2, "nombre": "Sura", "codigo": "EPS002", "estado": "ACTIVO"},
            ]

    app = FastAPI()
    app.dependency_overrides[eps_module.get_eps_service] = lambda: FakeEpsService()
    app.dependency_overrides[eps_module.get_supabase_client] = lambda: "fake-supabase"
    app.include_router(eps_module.router, prefix="/api")
    return TestClient(app)


def test_list_eps_returns_eps_collection(client: TestClient) -> None:
    response = client.get("/api/eps/", params={"limit": 2})

    assert response.status_code == 200
    assert response.json() == [
        {"id_eps": 1, "nombre": "Nueva EPS", "codigo": "EPS001", "estado": "ACTIVO"},
        {"id_eps": 2, "nombre": "Sura", "codigo": "EPS002", "estado": "ACTIVO"},
    ]
