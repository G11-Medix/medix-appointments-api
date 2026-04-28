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

        def get_eps(self, supabase, id_eps: int):  # noqa: ANN001
            assert supabase == "fake-supabase"
            if id_eps == 404:
                return None
            return {"id_eps": id_eps, "nombre": "Nueva EPS", "codigo": "EPS001", "estado": "ACTIVO"}

        def list_related_ips(self, supabase, id_eps: int):  # noqa: ANN001
            assert supabase == "fake-supabase"
            assert id_eps == 1
            return [
                {
                    "id_institucion": 10,
                    "nombre": "Clinica Colsanitas",
                    "nit": "900123456",
                    "direccion": "Calle 1 # 2-3",
                    "telefono": "6011234567",
                    "estado": "ACTIVO",
                    "longitud": -74.1,
                    "latitud": 4.6,
                    "logo_url": "https://example.com/logo.png",
                    "service_url": None,
                }
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


def test_list_eps_related_ips_returns_collection(client: TestClient) -> None:
    response = client.get("/api/eps/1/ips")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id_institucion": 10,
            "nombre": "Clinica Colsanitas",
            "nit": "900123456",
            "direccion": "Calle 1 # 2-3",
            "telefono": "6011234567",
            "estado": "ACTIVO",
            "longitud": -74.1,
            "latitud": 4.6,
            "logo_url": "https://example.com/logo.png",
            "service_url": None,
        }
    ]


def test_list_eps_related_ips_returns_404_when_eps_does_not_exist(client: TestClient) -> None:
    response = client.get("/api/eps/404/ips")

    assert response.status_code == 404
    assert response.json() == {"detail": "EPS no encontrada"}
