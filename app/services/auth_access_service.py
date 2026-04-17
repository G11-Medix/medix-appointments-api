import logging
import re
from typing import Any

from fastapi import HTTPException, status
from supabase import Client
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

    def _get_auth_user_by_id(self, admin_supabase: Client, user_id: str) -> Any | None:
        try:
            response = admin_supabase.auth.admin.get_user_by_id(user_id)
        except Exception:
            return None
        return getattr(response, "user", None)

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
