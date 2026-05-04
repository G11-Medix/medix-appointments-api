from datetime import date, datetime

import pytest
from fastapi import HTTPException

from app.messaging.nats_handlers import NatsApiHandlers
from app.messaging.nats_server import NatsRequestReplyServer


class FakeAssistantService:
    def list_instituciones_by_especialidad(self, codigo_reps: int, access_token: str | None = None):
        assert codigo_reps == 302
        assert access_token == "ok-token"
        return [
            {"id_institucion": 1, "nombre": "IPS Demo", "estado": "ACTIVA", "especialidades": [302]},
            {"id_institucion": 2, "nombre": "IPS Aliada", "estado": "ACTIVA", "especialidades": [302]},
        ]

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
            "disponibilidad": [],
        }

    def find_patient_by_document(self, tipo_documento: str, numero_documento: str, access_token: str | None = None):
        if numero_documento == "404":
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        assert (tipo_documento, numero_documento, access_token) == ("CC", "123", "ok-token")
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


class FakeEspecialidadService:
    def list_especialidades(self, supabase, limit: int = 50):  # noqa: ANN001
        assert supabase is not None
        assert limit == 50
        return [{"id_especialidad": 1, "nombre": "Cardiologia", "codigo_reps": 302}]


class FakeInstitucionService:
    def list_instituciones(self, supabase, limit: int = 20):  # noqa: ANN001
        assert supabase is not None
        assert limit == 20
        return [
            {
                "id_institucion": 1,
                "nombre": "IPS Demo",
                "nit": "900000001",
                "direccion": "Calle 1",
                "telefono": "3000000000",
                "estado": "ACTIVO",
                "longitud": -74.0,
                "latitud": 4.0,
                "logo_url": None,
            }
        ]


class FakeCitaService:
    def create_cita(self, id_institucion: int, payload, access_token: str | None = None):  # noqa: ANN001
        assert id_institucion == 1
        assert payload.numero_documento == "123"
        assert access_token == "ok-token"
        return {
            "id": 10,
            "id_paciente": 1,
            "id_prestador": payload.id_prestador,
            "nombre_prestador": "Dr. Demo",
            "id_especialidad": 302,
            "fecha_hora_cupo": "2026-04-10T10:00:00",
            "estado": "scheduled",
            "motivo_cancelacion": None,
            "fecha_creacion": "2026-04-01T08:00:00",
            "fecha_actualizacion": "2026-04-01T08:00:00",
        }

    def get_cita_ips(self, supabase, id_institucion: int, id_cita: int, access_token: str | None = None):  # noqa: ANN001
        assert supabase is not None
        assert (id_institucion, id_cita, access_token) == (1, 10, "ok-token")
        return {
            "id": 10,
            "nombre_paciente": "Ana Perez",
            "cedula_paciente": "123",
            "id_prestador": 2,
            "nombre_prestador": "Dr. Demo",
            "especialidad": "Cardiologia",
            "fecha": "2026-04-10",
            "hora": "10:00:00",
            "estado_cita": "scheduled",
            "motivo_cancelacion": None,
            "fecha_creacion": "2026-04-01T08:00:00",
            "fecha_actualizacion": "2026-04-01T08:00:00",
        }

    def list_citas_ips(self, supabase, id_institucion: int, **kwargs):  # noqa: ANN001
        assert supabase is not None
        assert id_institucion == 1
        assert kwargs["access_token"] == "ok-token"
        assert isinstance(kwargs["desde"], datetime)
        return [
            {
                "id": 10,
                "nombre_paciente": "Ana Perez",
                "cedula_paciente": "123",
                "id_prestador": 2,
                "nombre_prestador": "Dr. Demo",
                "especialidad": "Cardiologia",
                "fecha": "2026-04-10",
                "hora": "10:00:00",
                "estado_cita": "scheduled",
                "motivo_cancelacion": None,
                "fecha_creacion": "2026-04-01T08:00:00",
                "fecha_actualizacion": "2026-04-01T08:00:00",
            }
        ]

    def get_cita_confirmacion(self, supabase, id_institucion: int, id_cita: int, access_token: str | None = None):  # noqa: ANN001
        assert supabase is not None
        assert (id_institucion, id_cita, access_token) == (1, 10, "ok-token")
        return {
            "doctor": "Dr. Demo",
            "fecha": "2026-04-10T10:00:00",
            "institucion": "IPS Demo",
            "direccion": "Calle 1",
            "latitud": 4.6,
            "longitud": -74.1,
            "estado": "scheduled",
        }

    def delete_cita(self, id_institucion: int, id_cita: int, payload, access_token: str | None = None):  # noqa: ANN001
        if id_cita == 404:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        assert payload.motivo == "Paciente no asiste"
        assert access_token == "ok-token"
        return self.create_cita(id_institucion, type("Payload", (), {"numero_documento": "123", "id_prestador": 2})(), access_token)

    def update_cita(self, id_institucion: int, id_cita: int, payload, access_token: str | None = None):  # noqa: ANN001
        assert payload.nueva_fecha_hora_cupo == datetime(2026, 4, 11, 14, 0, 0)
        assert access_token == "ok-token"
        return self.create_cita(id_institucion, type("Payload", (), {"numero_documento": "123", "id_prestador": 2})(), access_token)

    def list_citas_app_by_paciente_doc(self, supabase, id_paciente: int, access_token: str | None = None):  # noqa: ANN001
        assert supabase is not None
        assert (id_paciente, access_token) == (4, "ok-token")
        return [
            {
                "id": 10,
                "id_institucion": 1,
                "nombre_ins": "IPS Demo",
                "logo_url": None,
                "especialidad": "Cardiologia",
                "estado": "scheduled",
                "fecha": "2026-04-10",
                "hora": "10:00:00",
            }
        ]


class FakePacienteService:
    def get_paciente(self, supabase, id_paciente: int):  # noqa: ANN001
        assert supabase is not None
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
            "id_usuario": None,
            "id_eps": 7,
        }


class FakeEpsService:
    def list_related_ips(self, supabase, id_eps: int):  # noqa: ANN001
        assert supabase is not None
        assert id_eps == 7
        return [{"id_institucion": 2}]


def build_server() -> NatsRequestReplyServer:
    handlers = NatsApiHandlers(
        supabase=object(),
        assistant_service=FakeAssistantService(),
        cita_service=FakeCitaService(),
        paciente_service=FakePacienteService(),
        eps_service=FakeEpsService(),
        institucion_service=FakeInstitucionService(),
        especialidad_service=FakeEspecialidadService(),
    )
    handlers.authenticate = lambda access_token: access_token  # type: ignore[method-assign]
    return NatsRequestReplyServer(handlers=handlers)


def _command(operation: str, payload: dict) -> bytes:
    import json

    return json.dumps(
        {
            "correlation_id": "corr-123",
            "operation": operation,
            "access_token": "ok-token",
            "payload": payload,
        }
    ).encode("utf-8")


@pytest.mark.anyio
async def test_nats_server_handles_successful_request_reply() -> None:
    server = build_server()

    response = await server.handle_message(
        "assistant.buscar_paciente",
        _command("assistant.buscar_paciente", {"tipo_documento": "CC", "numero_documento": "123"}),
    )

    assert response.success is True
    assert response.correlation_id == "corr-123"
    assert response.data["id_paciente"] == 12
    assert response.error is None


@pytest.mark.anyio
async def test_nats_server_returns_http_errors_in_reply() -> None:
    server = build_server()

    response = await server.handle_message(
        "citas.cancelar",
        _command(
            "citas.cancelar",
            {
                "id_institucion": 1,
                "id_cita": 404,
                "payload": {"motivo": "Paciente no asiste"},
            },
        ),
    )

    assert response.success is False
    assert response.error is not None
    assert response.error.code == 404
    assert response.error.detail == "Cita no encontrada"


@pytest.mark.anyio
async def test_nats_server_validates_operation_matches_subject() -> None:
    server = build_server()

    response = await server.handle_message(
        "assistant.disponibilidad",
        _command("assistant.buscar_paciente", {"tipo_documento": "CC", "numero_documento": "123"}),
    )

    assert response.success is False
    assert response.error is not None
    assert response.error.code == 400


@pytest.mark.anyio
async def test_nats_server_supports_endpoint_style_subjects() -> None:
    server = build_server()

    especialidades = await server.handle_message(
        "especialidades.listar",
        _command("especialidades.listar", {}),
    )
    paciente = await server.handle_message(
        "pacientes.obtener",
        _command("pacientes.obtener", {"id_paciente": 5}),
    )
    instituciones = await server.handle_message(
        "instituciones.listar",
        _command("instituciones.listar", {}),
    )

    assert especialidades.success is True
    assert especialidades.data[0]["codigo_reps"] == 302
    assert paciente.success is True
    assert paciente.data["id_paciente"] == 5
    assert instituciones.success is True
    assert instituciones.data[0]["id_institucion"] == 1
