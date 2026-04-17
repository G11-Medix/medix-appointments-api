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
