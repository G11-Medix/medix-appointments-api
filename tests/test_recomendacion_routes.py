from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.routes import recomendacion as recomendacion_module


def _recomendacion_row(**overrides):
    row = {
        "id": 1,
        "created_at": "2026-04-01T10:00:00+00:00",
        "institucion_id": 10,
        "especialidad_id": 20,
        "codigo": "CARDIO-PREP",
        "recomendaciones": {"items": ["Llegar 20 minutos antes"]},
        "prioridad": 2,
        "activa": True,
    }
    row.update(overrides)
    return row


def test_recomendaciones_crud_routes() -> None:
    class FakeRecomendacionService:
        def list_recomendaciones(self, supabase, *, institucion_id=None, especialidad_id=None, activa=None, limit=50):  # noqa: ANN001
            assert supabase == "fake-supabase"
            assert institucion_id == 10
            assert especialidad_id == 20
            assert activa is True
            assert limit == 10
            return [_recomendacion_row()]

        def get_recomendacion(self, supabase, id_recomendacion: int):  # noqa: ANN001
            assert supabase == "fake-supabase"
            assert id_recomendacion == 1
            return _recomendacion_row()

        def create_recomendacion(self, supabase, payload):  # noqa: ANN001
            assert supabase == "fake-supabase"
            assert payload.institucion_id == 10
            assert payload.especialidad_id == 20
            return _recomendacion_row()

        def update_recomendacion(self, supabase, id_recomendacion: int, payload):  # noqa: ANN001
            assert supabase == "fake-supabase"
            assert id_recomendacion == 1
            assert payload.prioridad == 3
            return _recomendacion_row(prioridad=3)

        def delete_recomendacion(self, supabase, id_recomendacion: int):  # noqa: ANN001
            assert supabase == "fake-supabase"
            assert id_recomendacion == 1
            return _recomendacion_row(activa=False)

    app = FastAPI()
    app.dependency_overrides[recomendacion_module.get_recomendacion_service] = lambda: FakeRecomendacionService()
    app.dependency_overrides[recomendacion_module.get_supabase_client] = lambda: "fake-supabase"
    app.include_router(recomendacion_module.router, prefix="/api")
    client = TestClient(app)

    list_response = client.get(
        "/api/recomendaciones/",
        params={"institucion_id": 10, "especialidad_id": 20, "activa": True, "limit": 10},
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["codigo"] == "CARDIO-PREP"

    get_response = client.get("/api/recomendaciones/1")
    assert get_response.status_code == 200
    assert get_response.json()["recomendaciones"] == {"items": ["Llegar 20 minutos antes"]}

    create_response = client.post(
        "/api/recomendaciones/",
        json={
            "institucion_id": 10,
            "especialidad_id": 20,
            "codigo": "CARDIO-PREP",
            "recomendaciones": {"items": ["Llegar 20 minutos antes"]},
            "prioridad": 2,
            "activa": True,
        },
    )
    assert create_response.status_code == 201

    update_response = client.put("/api/recomendaciones/1", json={"prioridad": 3})
    assert update_response.status_code == 200
    assert update_response.json()["prioridad"] == 3

    delete_response = client.delete("/api/recomendaciones/1")
    assert delete_response.status_code == 200
    assert delete_response.json()["activa"] is False


def test_get_recomendacion_route_propagates_404() -> None:
    class FakeRecomendacionService:
        def get_recomendacion(self, supabase, id_recomendacion: int):  # noqa: ANN001
            raise HTTPException(status_code=404, detail="Recomendacion no encontrada")

    app = FastAPI()
    app.dependency_overrides[recomendacion_module.get_recomendacion_service] = lambda: FakeRecomendacionService()
    app.dependency_overrides[recomendacion_module.get_supabase_client] = lambda: "fake-supabase"
    app.include_router(recomendacion_module.router, prefix="/api")
    client = TestClient(app)

    response = client.get("/api/recomendaciones/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Recomendacion no encontrada"}
