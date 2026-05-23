from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.api.middlewares import audit_middleware as audit_middleware_module
from app.api.middlewares.audit_middleware import build_audit_middleware
from app.services import audit_service as audit_service_module


def test_audit_middleware_reuses_request_state_id_usuario(monkeypatch) -> None:  # noqa: ANN001
    recorded_payloads: list[dict] = []

    def fake_record(self, supabase, tipo_accion, id_usuario, ip_origen, resultado, detalle):  # noqa: ANN001
        recorded_payloads.append(
            {
                "tipo_accion": tipo_accion,
                "id_usuario": id_usuario,
                "resultado": resultado,
                "detalle": detalle,
            }
        )

    def fail_if_called(self, supabase, authorization_header):  # noqa: ANN001
        raise AssertionError("get_id_usuario no debe llamarse cuando se usa request.state")

    monkeypatch.setattr(audit_service_module.AuditService, "record", fake_record)
    monkeypatch.setattr(audit_service_module.AuditService, "get_id_usuario", fail_if_called)

    app = FastAPI()
    app.middleware("http")(build_audit_middleware(supabase=object()))

    @app.get("/api/ping")
    def ping(request: Request) -> dict[str, str]:
        request.state.authenticated_user_id = "9de5d6b8-4af4-4ceb-92ff-ec8f0904b663"
        return {"message": "pong"}

    client = TestClient(app)
    response = client.get("/api/ping")

    assert response.status_code == 200
    assert len(recorded_payloads) == 1
    assert recorded_payloads[0]["id_usuario"] == "9de5d6b8-4af4-4ceb-92ff-ec8f0904b663"
    assert recorded_payloads[0]["resultado"] == "EXITO"


def test_audit_middleware_logs_when_record_fails(
    monkeypatch,
    caplog,
) -> None:  # noqa: ANN001
    def fail_record(self, supabase, tipo_accion, id_usuario, ip_origen, resultado, detalle):  # noqa: ANN001
        raise RuntimeError("db down")

    monkeypatch.setattr(audit_service_module.AuditService, "record", fail_record)

    app = FastAPI()
    app.middleware("http")(build_audit_middleware(supabase=object()))

    @app.get("/api/ping")
    def ping() -> dict[str, str]:
        return {"message": "pong"}

    with caplog.at_level("ERROR", logger=audit_middleware_module.__name__):
        response = TestClient(app).get("/api/ping")

    assert response.status_code == 200
    assert "No fue posible registrar auditoria" in caplog.text


def test_audit_middleware_does_not_log_token_user_id_for_forbidden_response(
    monkeypatch,
) -> None:  # noqa: ANN001
    recorded_payloads: list[dict] = []

    def fake_record(self, supabase, tipo_accion, id_usuario, ip_origen, resultado, detalle):  # noqa: ANN001
        recorded_payloads.append(
            {
                "tipo_accion": tipo_accion,
                "id_usuario": id_usuario,
                "resultado": resultado,
                "detalle": detalle,
            }
        )

    monkeypatch.setattr(audit_service_module.AuditService, "record", fake_record)

    app = FastAPI()
    app.middleware("http")(build_audit_middleware(supabase=object()))

    @app.get("/api/forbidden")
    def forbidden(request: Request) -> JSONResponse:
        request.state.authenticated_user_id = "ec6dd6db-db52-4c82-8492-00f3f011abcb"
        return JSONResponse({"detail": "Usuario no autorizado"}, status_code=403)

    response = TestClient(app).get("/api/forbidden")

    assert response.status_code == 403
    assert len(recorded_payloads) == 1
    assert recorded_payloads[0]["id_usuario"] is None
    assert recorded_payloads[0]["resultado"] == "ERROR"
