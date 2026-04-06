from supabase import Client


class PacienteRepository:
    _select_fields = (
        "id_paciente,tipo_documento,numero_documento,nombres,apellidos,fecha_nacimiento,"
        "telefono,correo,estado,fecha_creacion,id_usuario,id_eps"
    )

    def list(self, supabase: Client, limit: int = 20) -> list[dict]:
        response = (
            supabase.table("Paciente")
            .select(self._select_fields)
            .order("id_paciente")
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_by_id(self, supabase: Client, id_paciente: int) -> dict | None:
        response = (
            supabase.table("Paciente")
            .select(self._select_fields)
            .eq("id_paciente", id_paciente)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def create(self, supabase: Client, payload: dict) -> dict:
        response = (
            supabase.table("Paciente")
            .insert(payload)
            .execute()
        )
        data = response.data or []
        return data[0] if data else {}

    def update(self, supabase: Client, id_paciente: int, payload: dict) -> None:
        supabase.table("Paciente").update(payload).eq("id_paciente", id_paciente).execute()

    def delete(self, supabase: Client, id_paciente: int) -> None:
        supabase.table("Paciente").delete().eq("id_paciente", id_paciente).execute()
