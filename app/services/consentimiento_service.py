from supabase import Client

from app.repositories.consentimiento_repository import ConsentimientoRepository
from app.schemas.consentimiento import AceptacionRequest


class ConsentimientoService:

    def __init__(
        self,
        repository: ConsentimientoRepository | None = None,
    ) -> None:
        self.repository = repository or ConsentimientoRepository()

    def get_documento_activo(self, supabase: Client) -> dict | None:
        return self.repository.get_documento_activo(supabase=supabase)

    def has_accepted_latest(
        self,
        supabase: Client,
        user_id: str,
    ) -> bool:
        documento = self.get_documento_activo(supabase)
        if not documento:
            return False

        return self.repository.exists_aceptacion(
            supabase=supabase,
            user_id=user_id,
            id_documento=documento["id_documento"],
        )

    def aceptar_documento(
        self,
        supabase: Client,
        user_id: str,
        payload: AceptacionRequest,
        ip: str | None,
    ) -> dict | None:

        documento = self.get_documento_activo(supabase)
        if not documento:
            return None

        data = {
            "id_usuario": user_id,
            "id_documento": documento["id_documento"],
            "dispositivo": payload.dispositivo,
            "ip": ip,
        }

        return self.repository.create_aceptacion(
            supabase=supabase,
            payload=data,
        )
