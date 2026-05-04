import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import institucion as institucion_module


@pytest.fixture
def client() -> TestClient:
    class FakeInstitucionService:
        def get_institucion(self, supabase, id_institucion: int):  # noqa: ANN001
            assert supabase == "fake-supabase"
            if id_institucion == 404:
                return None
            return {
                "id_institucion": id_institucion,
                "nombre": "Clinica Central",
                "nit": "900000000",
                "direccion": "Calle 1",
                "telefono": "3000000000",
                "estado": "ACTIVO",
                "longitud": -74.1,
                "latitud": 4.6,
                "logo_url": None,
                "service_url": "http://ips-central",
            }

        def update_institucion(self, supabase, id_institucion: int, payload):  # noqa: ANN001
            assert supabase == "fake-supabase"
            if id_institucion == 404:
                return None
            data = self.get_institucion(supabase=supabase, id_institucion=id_institucion)
            data.update(payload.model_dump(exclude_unset=True))
            return data

        def check_health(self, supabase, id_institucion: int):  # noqa: ANN001
            assert supabase == "fake-supabase"
            if id_institucion == 404:
                return None
            if id_institucion == 2:
                return {
                    "id_institucion": id_institucion,
                    "status": "NOT_CONFIGURED",
                    "service_url": None,
                    "status_code": None,
                    "latency_ms": None,
                    "message": "La institucion no tiene service_url configurada.",
                }
            return {
                "id_institucion": id_institucion,
                "status": "UP",
                "service_url": "http://ips-central",
                "status_code": 200,
                "latency_ms": 12,
                "message": "Servicio disponible.",
            }

        def list_related_especialidades(self, supabase, id_institucion: int):  # noqa: ANN001
            assert supabase == "fake-supabase"
            assert id_institucion == 1
            return [
                {"id_especialidad": 1, "nombre": "Cardiologia", "codigo_reps": 302},
                {"id_especialidad": 2, "nombre": "Pediatria", "codigo_reps": 410},
            ]

    app = FastAPI()
    app.dependency_overrides[institucion_module.get_institucion_service] = lambda: FakeInstitucionService()
    app.dependency_overrides[institucion_module.get_supabase_client] = lambda: "fake-supabase"
    app.include_router(institucion_module.router, prefix="/api")
    return TestClient(app)


def test_list_institucion_related_especialidades_returns_collection(client: TestClient) -> None:
    response = client.get("/api/instituciones/1/especialidades")

    assert response.status_code == 200
    assert response.json() == [
        {"id_especialidad": 1, "nombre": "Cardiologia", "codigo_reps": 302},
        {"id_especialidad": 2, "nombre": "Pediatria", "codigo_reps": 410},
    ]


def test_list_institucion_related_especialidades_returns_404_when_institucion_does_not_exist(client: TestClient) -> None:
    response = client.get("/api/instituciones/404/especialidades")

    assert response.status_code == 404
    assert response.json() == {"detail": "Institucion no encontrada"}


def test_update_institucion_returns_updated_row(client: TestClient) -> None:
    response = client.put(
        "/api/instituciones/1",
        json={"nombre": "Clinica Norte", "service_url": "http://ips-norte/"},
    )

    assert response.status_code == 200
    assert response.json()["nombre"] == "Clinica Norte"
    assert response.json()["service_url"] == "http://ips-norte"


def test_update_institucion_returns_404_when_missing(client: TestClient) -> None:
    response = client.put("/api/instituciones/404", json={"nombre": "No existe"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Institucion no encontrada"}


def test_update_institucion_rejects_invalid_service_url(client: TestClient) -> None:
    response = client.put("/api/instituciones/1", json={"service_url": "ftp://ips"})

    assert response.status_code == 422


def test_check_institucion_health_returns_status(client: TestClient) -> None:
    response = client.get("/api/instituciones/1/health")

    assert response.status_code == 200
    assert response.json() == {
        "id_institucion": 1,
        "status": "UP",
        "service_url": "http://ips-central",
        "status_code": 200,
        "latency_ms": 12,
        "message": "Servicio disponible.",
    }


def test_check_institucion_health_returns_not_configured(client: TestClient) -> None:
    response = client.get("/api/instituciones/2/health")

    assert response.status_code == 200
    assert response.json()["status"] == "NOT_CONFIGURED"


def test_check_institucion_health_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/instituciones/404/health")

    assert response.status_code == 404
