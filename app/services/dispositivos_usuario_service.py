from supabase import Client
from app.repositories.dispositivos_usuario_repository import DispositivosUsuarioRepository


class DispositivosUsuarioService:

    def __init__(self):
        self.repo = DispositivosUsuarioRepository()

    def save_or_update_token(
        self,
        supabase: Client,
        *,
        id_usuario,
        token: str,
        plataforma: str | None = None
    ):
        return self.repo.upsert_token(
            supabase=supabase,
            id_usuario=id_usuario,
            token_dispositivo=token,
            plataforma=plataforma
        )