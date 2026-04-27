from datetime import datetime

import pytest
from fastapi import HTTPException

from app.messaging.nats_handlers import NatsApiHandlers


class FakeAssistantService:
    def list_instituciones_by_especialidad(self, codigo_reps: int, access_token: str | None = None):
        assert codigo_reps == 302
        assert access_token == "ok-token"
        return [
            {"id_institucion": 1, "nombre": "IPS Demo", "estado": "ACTIVA", "especialidades": [302]},
            {"id_institucion": 2, "nombre": "IPS Aliada", "estado": "ACTIVA", "especialidades": [302]},
        ]


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


class FakePacienteService:
    def get_paciente(self, supabase, id_paciente: int):  # noqa: ANN001
        assert supabase is not None
        if id_paciente == 999:
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


class FakeCitaService:
    def list_citas_ips(self, supabase, id_institucion: int, **kwargs):  # noqa: ANN001
        assert supabase is not None
        assert id_institucion == 1
        assert kwargs["access_token"] == "ok-token"
        assert kwargs["desde"] == datetime(2026, 4, 1, 0, 0, 0)
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


def build_handlers() -> NatsApiHandlers:
    return NatsApiHandlers(
        supabase=object(),
        assistant_service=FakeAssistantService(),
        cita_service=FakeCitaService(),
        paciente_service=FakePacienteService(),
        eps_service=FakeEpsService(),
        institucion_service=FakeInstitucionService(),
        especialidad_service=FakeEspecialidadService(),
    )


def test_handle_assistant_list_instituciones_applies_patient_filter() -> None:
    handlers = build_handlers()

    response = handlers.handle_assistant_list_instituciones(
        {"codigo_reps": 302, "id_paciente": 5},
        "ok-token",
    )

    assert response == [
        {"id_institucion": 2, "nombre": "IPS Aliada", "estado": "ACTIVA", "especialidades": [302]}
    ]


def test_handle_assistant_list_instituciones_raises_404_for_missing_patient() -> None:
    handlers = build_handlers()

    with pytest.raises(HTTPException) as exc_info:
        handlers.handle_assistant_list_instituciones({"codigo_reps": 302, "id_paciente": 999}, "ok-token")

    assert exc_info.value.status_code == 404


def test_handle_cita_list_normalizes_datetime_filters() -> None:
    handlers = build_handlers()

    response = handlers.handle_cita_list(
        {
            "id_institucion": 1,
            "tipo_documento": "CC",
            "cedula": "123",
            "desde": "2026-04-01T00:00:00",
            "hasta": "2026-04-30T23:59:59",
        },
        "ok-token",
    )

    assert response[0]["id"] == 10


def test_handle_list_especialidades_returns_expected_shape() -> None:
    handlers = build_handlers()

    response = handlers.handle_list_especialidades({}, "ok-token")

    assert response == [{"id_especialidad": 1, "nombre": "Cardiologia", "codigo_reps": 302}]


def test_handle_list_instituciones_without_codigo_reps_uses_catalog_service() -> None:
    handlers = build_handlers()

    response = handlers.handle_list_instituciones({}, "ok-token")

    assert response[0]["id_institucion"] == 1
    assert response[0]["nombre"] == "IPS Demo"


def test_handle_get_paciente_returns_expected_shape() -> None:
    handlers = build_handlers()

    response = handlers.handle_get_paciente({"id_paciente": 5}, "ok-token")

    assert response["id_paciente"] == 5
    assert response["numero_documento"] == "123"
