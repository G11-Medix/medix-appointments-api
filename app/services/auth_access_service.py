import logging
import re
from typing import Any

from fastapi import HTTPException, status
from supabase import Client
from supabase_auth.types import AdminUserAttributes

from app.repositories.auth_access_repository import AuthAccessRepository
from app.schemas.auth import PhoneEligibilityResponse

LOGGER = logging.getLogger(__name__)
PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")


class AuthAccessService:
    def __init__(
        self,
        repository: AuthAccessRepository | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository or AuthAccessRepository()
        self.logger = logger or LOGGER

    def check_phone_login_eligibility(
        self,
        supabase: Client,
        admin_supabase: Client,
        telefono: str,
    ) -> PhoneEligibilityResponse:
        telefono_auth = self.normalize_phone(telefono)
        telefono_db = self.normalize_phone_for_database(telefono)
        pacientes = self._find_pacientes_by_phone_variants(
            supabase=supabase,
            telefono=telefono,
        )
        if not pacientes:
            return PhoneEligibilityResponse(authorized=False, reason="PATIENT_NOT_FOUND")

        activos = [paciente for paciente in pacientes if self._is_active(paciente.get("estado"))]
        if not activos:
            return PhoneEligibilityResponse(authorized=False, reason="PATIENT_INACTIVE")
        if len(activos) > 1:
            self.logger.warning(
                "Se detectaron múltiples pacientes activos para el teléfono %s; se rechaza elegibilidad",
                telefono_db,
            )
            return PhoneEligibilityResponse(authorized=False, reason="PATIENT_NOT_FOUND")

        paciente = activos[0]
        id_usuario = paciente.get("id_usuario")
        if not id_usuario:
            return PhoneEligibilityResponse(authorized=False, reason="USER_NOT_LINKED")

        usuario = self.repository.get_usuario_by_id(supabase=supabase, id_usuario=str(id_usuario))
        if not usuario or not self._is_active(usuario.get("estado")):
            return PhoneEligibilityResponse(authorized=False, reason="USER_INACTIVE")

        auth_user = self._get_auth_user_by_id(admin_supabase=admin_supabase, user_id=str(id_usuario))
        if auth_user is None:
            return PhoneEligibilityResponse(authorized=False, reason="AUTH_USER_NOT_FOUND")

        auth_phone = self._normalize_phone_from_auth(auth_user)
        paciente_phone = self.normalize_phone_for_database(str(paciente.get("telefono") or telefono_db))
        if auth_phone is None or self.normalize_phone_for_database(auth_phone) != paciente_phone:
            return PhoneEligibilityResponse(authorized=False, reason="PHONE_MISMATCH")

        return PhoneEligibilityResponse(
            authorized=True,
            reason=None,
            paciente={
                "id_paciente": int(paciente["id_paciente"]),
                "id_usuario": str(id_usuario),
                "telefono": str(paciente.get("telefono") or telefono_db),
                "estado": str(paciente.get("estado") or ""),
            },
        )

    def grant_patient_access(
        self,
        supabase: Client,
        admin_supabase: Client,
        id_paciente: int,
        telefono: str,
        rol: str = "PACIENTE",
    ) -> dict[str, Any]:
        telefono_auth = self.normalize_phone(telefono)
        telefono_db = self.normalize_phone_for_database(telefono)
        rol_normalizado = str(rol or "PACIENTE").upper()

        paciente = self.repository.get_paciente_by_id(supabase=supabase, id_paciente=id_paciente)
        if not paciente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

        self._validate_phone_collision(
            supabase=supabase,
            telefono=telefono,
            id_paciente=id_paciente,
        )

        id_usuario_actual = paciente.get("id_usuario")
        auth_user_created = False
        auth_user = None

        if id_usuario_actual:
            usuario = self.repository.get_usuario_by_id(supabase=supabase, id_usuario=str(id_usuario_actual))
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Paciente vinculado a un usuario local inexistente",
                )

            auth_user = self._get_auth_user_by_id(admin_supabase=admin_supabase, user_id=str(id_usuario_actual))
            if auth_user is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Paciente vinculado a un usuario auth inexistente",
                )

            auth_phone = self._normalize_phone_from_auth(auth_user)
            if auth_phone is None or self.normalize_phone_for_database(auth_phone) != telefono_db:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El usuario auth vinculado tiene un teléfono diferente",
                )

            self._ensure_usuario(
                supabase=supabase,
                id_usuario=str(id_usuario_actual),
                rol=rol_normalizado,
            )
            paciente_actualizado = self.repository.update_paciente(
                supabase=supabase,
                id_paciente=id_paciente,
                payload={
                    "telefono": telefono_db,
                    "estado": "ACTIVO",
                    "id_usuario": str(id_usuario_actual),
                },
            )
            if not paciente_actualizado:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo actualizar el paciente",
                )
            return self._build_grant_response(
                paciente=paciente_actualizado,
                id_usuario=str(id_usuario_actual),
                rol=rol_normalizado,
                auth_user_created=auth_user_created,
            )

        auth_user = self._find_auth_user_by_phone(admin_supabase=admin_supabase, telefono=telefono_auth)
        if auth_user is None:
            auth_user = self._create_auth_user(admin_supabase=admin_supabase, telefono=telefono_auth)
            auth_user_created = True

        auth_user_id = self._extract_auth_user_id(auth_user)
        if not auth_user_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Supabase Auth no devolvió un id de usuario",
            )

        self._validate_user_collision(
            supabase=supabase,
            id_usuario=auth_user_id,
            id_paciente=id_paciente,
        )
        self._ensure_usuario(supabase=supabase, id_usuario=auth_user_id, rol=rol_normalizado)

        # No hay transacción distribuida entre Auth y PostgREST; dejamos el orden seguro
        # y registramos el error en logs si el vínculo local falla tras crear el auth user.
        try:
            paciente_actualizado = self.repository.update_paciente(
                supabase=supabase,
                id_paciente=id_paciente,
                payload={
                    "telefono": telefono_db,
                    "estado": "ACTIVO",
                    "id_usuario": auth_user_id,
                },
            )
        except Exception:
            self.logger.exception(
                "Fallo al vincular paciente %s con auth user %s tras provisión",
                id_paciente,
                auth_user_id,
            )
            raise

        if not paciente_actualizado:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo actualizar el paciente",
            )

        return self._build_grant_response(
            paciente=paciente_actualizado,
            id_usuario=auth_user_id,
            rol=rol_normalizado,
            auth_user_created=auth_user_created,
        )

    def normalize_phone(self, telefono: str) -> str:
        telefono_normalizado = str(telefono or "").strip()
        if telefono_normalizado and not telefono_normalizado.startswith("+"):
            telefono_normalizado = f"+{telefono_normalizado}"
        if not PHONE_RE.fullmatch(telefono_normalizado):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El teléfono debe estar en formato E.164",
            )
        return telefono_normalizado

    def normalize_phone_for_database(self, telefono: str) -> str:
        return self.normalize_phone(telefono).removeprefix("+")

    def _find_auth_user_by_phone(self, admin_supabase: Client, telefono: str) -> Any | None:
        page = 1
        per_page = 100
        while True:
            users = admin_supabase.auth.admin.list_users(page=page, per_page=per_page)
            if not users:
                return None

            for user in users:
                if self._normalize_phone_from_auth(user) == telefono:
                    return user

            if len(users) < per_page:
                return None
            page += 1

    def _create_auth_user(self, admin_supabase: Client, telefono: str) -> Any:
        response = admin_supabase.auth.admin.create_user(
            AdminUserAttributes(
                phone=telefono,
                phone_confirm=True,
                user_metadata={"provisioned_by": "medix-appointments-api"},
            )
        )
        return getattr(response, "user", response)

    def _get_auth_user_by_id(self, admin_supabase: Client, user_id: str) -> Any | None:
        try:
            response = admin_supabase.auth.admin.get_user_by_id(user_id)
        except Exception:
            return None
        return getattr(response, "user", None)

    def _ensure_usuario(self, supabase: Client, id_usuario: str, rol: str) -> dict | None:
        usuario = self.repository.get_usuario_by_id(supabase=supabase, id_usuario=id_usuario)
        payload = {"rol": rol, "estado": "ACTIVO"}
        if usuario:
            return self.repository.update_usuario(supabase=supabase, id_usuario=id_usuario, payload=payload)
        payload["id_usuario"] = id_usuario
        return self.repository.create_usuario(supabase=supabase, payload=payload)

    def _validate_phone_collision(self, supabase: Client, telefono: str, id_paciente: int) -> None:
        pacientes = self._find_pacientes_by_phone_variants(supabase=supabase, telefono=telefono)
        collisions = [
            paciente
            for paciente in pacientes
            if int(paciente["id_paciente"]) != id_paciente and self._is_active(paciente.get("estado"))
        ]
        if collisions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El teléfono ya está vinculado a otro paciente activo",
            )

    def _validate_user_collision(self, supabase: Client, id_usuario: str, id_paciente: int) -> None:
        data = self.repository.find_pacientes_by_user_id(supabase=supabase, id_usuario=id_usuario)
        collisions = [
            paciente
            for paciente in data
            if int(paciente["id_paciente"]) != id_paciente and self._is_active(paciente.get("estado"))
        ]
        if collisions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario auth ya está vinculado a otro paciente activo",
            )

    def _build_grant_response(
        self,
        paciente: dict[str, Any],
        id_usuario: str,
        rol: str,
        auth_user_created: bool,
    ) -> dict[str, Any]:
        return {
            "id_paciente": int(paciente["id_paciente"]),
            "id_usuario": id_usuario,
            "telefono": str(paciente.get("telefono") or ""),
            "rol": rol,
            "estado_usuario": "ACTIVO",
            "estado_paciente": str(paciente.get("estado") or ""),
            "auth_user_created": auth_user_created,
        }

    @staticmethod
    def _is_active(value: Any) -> bool:
        return str(value or "").upper() == "ACTIVO"

    def _normalize_phone_from_auth(self, auth_user: Any) -> str | None:
        phone = getattr(auth_user, "phone", None)
        if phone is None and isinstance(auth_user, dict):
            phone = auth_user.get("phone")
        if not phone:
            return None
        telefono = str(phone).strip()
        if not PHONE_RE.fullmatch(telefono):
            return None
        return self.normalize_phone(telefono)

    def _find_pacientes_by_phone_variants(self, supabase: Client, telefono: str) -> list[dict]:
        candidatos = {
            self.normalize_phone(telefono),
            self.normalize_phone_for_database(telefono),
        }
        encontrados: dict[int, dict] = {}
        for candidato in candidatos:
            for paciente in self.repository.find_pacientes_by_phone(supabase=supabase, telefono=candidato):
                encontrados[int(paciente["id_paciente"])] = paciente
        return list(encontrados.values())

    @staticmethod
    def _extract_auth_user_id(auth_user: Any) -> str | None:
        user_id = getattr(auth_user, "id", None)
        if user_id is None and isinstance(auth_user, dict):
            user_id = auth_user.get("id")
        return str(user_id) if user_id else None
