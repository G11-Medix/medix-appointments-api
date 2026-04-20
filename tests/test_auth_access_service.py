from types import SimpleNamespace
from uuid import uuid4

from app.services.auth_access_service import AuthAccessService


class FakeAuthAdmin:
    def __init__(self, users_by_id: dict[str, object] | None = None) -> None:
        self.users_by_id = users_by_id or {}

    def get_user_by_id(self, uid: str):  # noqa: ANN001
        user = self.users_by_id.get(uid)
        if user is None:
            raise ValueError("not found")
        return SimpleNamespace(user=user)


class FakeAdminSupabase:
    def __init__(self, users_by_id: dict[str, object] | None = None) -> None:
        self.auth = SimpleNamespace(admin=FakeAuthAdmin(users_by_id=users_by_id))


class FakeAuthAccessRepository:
    def __init__(self, pacientes: list[dict] | None = None, usuarios: dict[str, dict] | None = None) -> None:
        self.pacientes = [dict(paciente) for paciente in (pacientes or [])]
        self.usuarios = {key: dict(value) for key, value in (usuarios or {}).items()}

    def find_pacientes_by_phone(self, supabase, telefono: str) -> list[dict]:  # noqa: ANN001
        return [dict(p) for p in self.pacientes if p.get("telefono") == telefono]

    def get_usuario_by_id(self, supabase, id_usuario: str) -> dict | None:  # noqa: ANN001
        row = self.usuarios.get(id_usuario)
        return dict(row) if row else None


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
