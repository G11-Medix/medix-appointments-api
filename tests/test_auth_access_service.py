from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.auth_access_service import AuthAccessService


class FakeAuthAdmin:
    def __init__(self, users_by_id: dict[str, object] | None = None) -> None:
        self.users_by_id = users_by_id or {}
        self.created_users: list[dict] = []

    def list_users(self, page: int = 1, per_page: int = 100):  # noqa: ANN001
        users = list(self.users_by_id.values())
        start = (page - 1) * per_page
        end = start + per_page
        return users[start:end]

    def get_user_by_id(self, uid: str):  # noqa: ANN001
        user = self.users_by_id.get(uid)
        if user is None:
            raise ValueError("not found")
        return SimpleNamespace(user=user)

    def create_user(self, attributes: dict):  # noqa: ANN001
        user_id = str(uuid4())
        user = SimpleNamespace(id=user_id, phone=attributes["phone"])
        self.users_by_id[user_id] = user
        self.created_users.append(attributes)
        return SimpleNamespace(user=user)


class FakeAdminSupabase:
    def __init__(self, users_by_id: dict[str, object] | None = None) -> None:
        self.auth = SimpleNamespace(admin=FakeAuthAdmin(users_by_id=users_by_id))


class FakeAuthAccessRepository:
    def __init__(self, pacientes: list[dict] | None = None, usuarios: dict[str, dict] | None = None) -> None:
        self.pacientes = [dict(paciente) for paciente in (pacientes or [])]
        self.usuarios = {key: dict(value) for key, value in (usuarios or {}).items()}
        self.created_usuarios: list[dict] = []
        self.updated_usuarios: list[tuple[str, dict]] = []

    def find_pacientes_by_phone(self, supabase, telefono: str) -> list[dict]:  # noqa: ANN001
        return [dict(p) for p in self.pacientes if p.get("telefono") == telefono]

    def get_paciente_by_id(self, supabase, id_paciente: int) -> dict | None:  # noqa: ANN001
        for paciente in self.pacientes:
            if int(paciente["id_paciente"]) == id_paciente:
                return dict(paciente)
        return None

    def update_paciente(self, supabase, id_paciente: int, payload: dict) -> dict | None:  # noqa: ANN001
        for paciente in self.pacientes:
            if int(paciente["id_paciente"]) == id_paciente:
                paciente.update(payload)
                return dict(paciente)
        return None

    def find_pacientes_by_user_id(self, supabase, id_usuario: str) -> list[dict]:  # noqa: ANN001
        return [dict(p) for p in self.pacientes if str(p.get("id_usuario") or "") == id_usuario]

    def get_usuario_by_id(self, supabase, id_usuario: str) -> dict | None:  # noqa: ANN001
        row = self.usuarios.get(id_usuario)
        return dict(row) if row else None

    def create_usuario(self, supabase, payload: dict) -> dict:  # noqa: ANN001
        self.usuarios[payload["id_usuario"]] = dict(payload)
        self.created_usuarios.append(dict(payload))
        return dict(payload)

    def update_usuario(self, supabase, id_usuario: str, payload: dict) -> dict | None:  # noqa: ANN001
        row = self.usuarios.get(id_usuario)
        if not row:
            return None
        row.update(payload)
        self.updated_usuarios.append((id_usuario, dict(payload)))
        return dict(row)


def _paciente(**overrides) -> dict:
    data = {
        "id_paciente": 1,
        "telefono": "573001234567",
        "estado": "ACTIVO",
        "id_usuario": str(uuid4()),
    }
    data.update(overrides)
    return data


def _usuario(id_usuario: str, **overrides) -> dict:
    data = {"id_usuario": id_usuario, "rol": "PACIENTE", "estado": "ACTIVO"}
    data.update(overrides)
    return data


def test_eligibility_patient_not_found() -> None:
    service = AuthAccessService(repository=FakeAuthAccessRepository())

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=FakeAdminSupabase(),
        telefono="+573001234567",
    )

    assert response.authorized is False
    assert response.reason == "PATIENT_NOT_FOUND"


def test_eligibility_patient_inactive() -> None:
    repository = FakeAuthAccessRepository(pacientes=[_paciente(estado="INACTIVO")])
    service = AuthAccessService(repository=repository)

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=FakeAdminSupabase(),
        telefono="+573001234567",
    )

    assert response.authorized is False
    assert response.reason == "PATIENT_INACTIVE"


def test_eligibility_user_not_linked() -> None:
    repository = FakeAuthAccessRepository(pacientes=[_paciente(id_usuario=None)])
    service = AuthAccessService(repository=repository)

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=FakeAdminSupabase(),
        telefono="+573001234567",
    )

    assert response.authorized is False
    assert response.reason == "USER_NOT_LINKED"


def test_eligibility_inactive_usuario() -> None:
    user_id = str(uuid4())
    repository = FakeAuthAccessRepository(
        pacientes=[_paciente(id_usuario=user_id)],
        usuarios={user_id: _usuario(user_id, estado="INACTIVO")},
    )
    service = AuthAccessService(repository=repository)

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=FakeAdminSupabase(),
        telefono="+573001234567",
    )

    assert response.authorized is False
    assert response.reason == "USER_INACTIVE"


def test_eligibility_auth_user_missing() -> None:
    user_id = str(uuid4())
    repository = FakeAuthAccessRepository(
        pacientes=[_paciente(id_usuario=user_id)],
        usuarios={user_id: _usuario(user_id)},
    )
    service = AuthAccessService(repository=repository)

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=FakeAdminSupabase(),
        telefono="+573001234567",
    )

    assert response.authorized is False
    assert response.reason == "AUTH_USER_NOT_FOUND"


def test_eligibility_phone_mismatch() -> None:
    user_id = str(uuid4())
    repository = FakeAuthAccessRepository(
        pacientes=[_paciente(id_usuario=user_id)],
        usuarios={user_id: _usuario(user_id)},
    )
    admin_supabase = FakeAdminSupabase(
        users_by_id={user_id: SimpleNamespace(id=user_id, phone="+573009999999")}
    )
    service = AuthAccessService(repository=repository)

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=admin_supabase,
        telefono="+573001234567",
    )

    assert response.authorized is False
    assert response.reason == "PHONE_MISMATCH"


def test_eligibility_authorized() -> None:
    user_id = str(uuid4())
    repository = FakeAuthAccessRepository(
        pacientes=[_paciente(id_usuario=user_id)],
        usuarios={user_id: _usuario(user_id)},
    )
    admin_supabase = FakeAdminSupabase(
        users_by_id={user_id: SimpleNamespace(id=user_id, phone="+573001234567")}
    )
    service = AuthAccessService(repository=repository)

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=admin_supabase,
        telefono="+573001234567",
    )

    assert response.authorized is True
    assert response.reason is None
    assert response.paciente is not None
    assert str(response.paciente.id_usuario) == user_id
    assert response.paciente.telefono == "573001234567"


def test_eligibility_accepts_phone_without_plus() -> None:
    user_id = str(uuid4())
    repository = FakeAuthAccessRepository(
        pacientes=[_paciente(id_usuario=user_id)],
        usuarios={user_id: _usuario(user_id)},
    )
    admin_supabase = FakeAdminSupabase(
        users_by_id={user_id: SimpleNamespace(id=user_id, phone="+573001234567")}
    )
    service = AuthAccessService(repository=repository)

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=admin_supabase,
        telefono="573001234567",
    )

    assert response.authorized is True
    assert response.paciente is not None
    assert response.paciente.telefono == "573001234567"


def test_eligibility_matches_db_without_plus_and_auth_with_plus() -> None:
    user_id = str(uuid4())
    repository = FakeAuthAccessRepository(
        pacientes=[_paciente(id_usuario=user_id, telefono="573001234567")],
        usuarios={user_id: _usuario(user_id)},
    )
    admin_supabase = FakeAdminSupabase(
        users_by_id={user_id: SimpleNamespace(id=user_id, phone="+573001234567")}
    )
    service = AuthAccessService(repository=repository)

    response = service.check_phone_login_eligibility(
        supabase=object(),
        admin_supabase=admin_supabase,
        telefono="+573001234567",
    )

    assert response.authorized is True
    assert response.paciente is not None
    assert response.paciente.telefono == "573001234567"


def test_grant_access_creates_auth_user_and_links_patient() -> None:
    repository = FakeAuthAccessRepository(pacientes=[_paciente(id_usuario=None, estado="INACTIVO")])
    admin_supabase = FakeAdminSupabase()
    service = AuthAccessService(repository=repository)

    response = service.grant_patient_access(
        supabase=object(),
        admin_supabase=admin_supabase,
        id_paciente=1,
        telefono="+573001234567",
    )

    assert response["id_paciente"] == 1
    assert response["telefono"] == "573001234567"
    assert response["estado_paciente"] == "ACTIVO"
    assert response["estado_usuario"] == "ACTIVO"
    assert response["auth_user_created"] is True
    assert repository.created_usuarios
    assert repository.get_paciente_by_id(object(), 1)["id_usuario"] == response["id_usuario"]
    assert admin_supabase.auth.admin.created_users[0]["phone"] == "+573001234567"


def test_grant_access_reuses_existing_auth_user_safely() -> None:
    repository = FakeAuthAccessRepository(pacientes=[_paciente(id_usuario=None)])
    auth_user_id = str(uuid4())
    admin_supabase = FakeAdminSupabase(
        users_by_id={auth_user_id: SimpleNamespace(id=auth_user_id, phone="+573001234567")}
    )
    service = AuthAccessService(repository=repository)

    response = service.grant_patient_access(
        supabase=object(),
        admin_supabase=admin_supabase,
        id_paciente=1,
        telefono="+573001234567",
    )

    assert response["id_usuario"] == auth_user_id
    assert response["auth_user_created"] is False
    assert repository.created_usuarios[0]["id_usuario"] == auth_user_id


def test_grant_access_rejects_phone_collision() -> None:
    repository = FakeAuthAccessRepository(
        pacientes=[
            _paciente(id_paciente=1, id_usuario=None),
            _paciente(id_paciente=2, id_usuario=None),
        ]
    )
    service = AuthAccessService(repository=repository)

    with pytest.raises(HTTPException) as exc_info:
        service.grant_patient_access(
            supabase=object(),
            admin_supabase=FakeAdminSupabase(),
            id_paciente=1,
            telefono="+573001234567",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "El teléfono ya está vinculado a otro paciente activo"


def test_grant_access_rejects_inconsistent_linked_user() -> None:
    user_id = str(uuid4())
    repository = FakeAuthAccessRepository(
        pacientes=[_paciente(id_usuario=user_id)],
        usuarios={},
    )
    service = AuthAccessService(repository=repository)

    with pytest.raises(HTTPException) as exc_info:
        service.grant_patient_access(
            supabase=object(),
            admin_supabase=FakeAdminSupabase(),
            id_paciente=1,
            telefono="+573001234567",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Paciente vinculado a un usuario local inexistente"


def test_grant_access_ensures_usuario_when_missing_local_row() -> None:
    repository = FakeAuthAccessRepository(pacientes=[_paciente(id_usuario=None)])
    auth_user_id = str(uuid4())
    admin_supabase = FakeAdminSupabase(
        users_by_id={auth_user_id: SimpleNamespace(id=auth_user_id, phone="+573001234567")}
    )
    service = AuthAccessService(repository=repository)

    response = service.grant_patient_access(
        supabase=object(),
        admin_supabase=admin_supabase,
        id_paciente=1,
        telefono="+573001234567",
        rol="PACIENTE",
    )

    assert response["id_usuario"] == auth_user_id
    assert repository.get_usuario_by_id(object(), auth_user_id) == {
        "id_usuario": auth_user_id,
        "rol": "PACIENTE",
        "estado": "ACTIVO",
    }
