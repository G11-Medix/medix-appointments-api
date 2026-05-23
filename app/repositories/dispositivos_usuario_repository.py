from typing import Any
from supabase import Client


class DispositivosUsuarioRepository:
    TABLE = "dispositivos_usuario"

    SELECT_FIELDS = "id,id_usuario,token_dispositivo,plataforma,actualizado_en"

    def upsert_token(
        self,
        supabase: Client,
        *,
        id_usuario,
        token_dispositivo: str,
        plataforma: str | None = None,
    ) -> dict[str, Any]:

        # 1. Intentar actualizar si ya existe token
        existing = (
            supabase.table(self.TABLE)
            .select(self.SELECT_FIELDS)
            .eq("token_dispositivo", token_dispositivo)
            .execute()
        )

        if existing.data:
            # actualizar
            response = (
                supabase.table(self.TABLE)
                .update({
                    "id_usuario": str(id_usuario),
                    "plataforma": plataforma
                })
                .eq("token_dispositivo", token_dispositivo)
                .execute()
            )
        else:
            # insertar nuevo
            response = (
                supabase.table(self.TABLE)
                .insert({
                    "id_usuario": str(id_usuario),
                    "token_dispositivo": token_dispositivo,
                    "plataforma": plataforma
                })
                .execute()
            )

        return (response.data or [{}])[0]