from supabase import Client


class AuthAccessRepository:
    _paciente_fields = (
        "id_paciente,tipo_documento,numero_documento,nombres,apellidos,fecha_nacimiento,"
        "telefono,correo,estado,fecha_creacion,id_usuario,id_eps"
    )
    _usuario_fields = "id_usuario,rol,estado,fecha_creacion"

    def find_pacientes_by_phone(self, supabase: Client, telefono: str) -> list[dict]:
        response = (
            supabase.table("Paciente")
            .select(self._paciente_fields)
            .eq("telefono", telefono)
            .order("id_paciente")
            .execute()
        )
        return response.data or []

    def get_paciente_by_id(self, supabase: Client, id_paciente: int) -> dict | None:
        response = (
            supabase.table("Paciente")
            .select(self._paciente_fields)
            .eq("id_paciente", id_paciente)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def update_paciente(self, supabase: Client, id_paciente: int, payload: dict) -> dict | None:
        supabase.table("Paciente").update(payload).eq("id_paciente", id_paciente).execute()
        return self.get_paciente_by_id(supabase=supabase, id_paciente=id_paciente)

    def find_pacientes_by_user_id(self, supabase: Client, id_usuario: str) -> list[dict]:
        response = (
            supabase.table("Paciente")
            .select("id_paciente,estado,id_usuario")
            .eq("id_usuario", id_usuario)
            .order("id_paciente")
            .execute()
        )
        return response.data or []

    def get_usuario_by_id(self, supabase: Client, id_usuario: str) -> dict | None:
        response = (
            supabase.table("Usuario")
            .select(self._usuario_fields)
            .eq("id_usuario", id_usuario)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None

    def create_usuario(self, supabase: Client, payload: dict) -> dict:
        response = supabase.table("Usuario").insert(payload).execute()
        data = response.data or []
        return data[0] if data else {}

    def update_usuario(self, supabase: Client, id_usuario: str, payload: dict) -> dict | None:
        supabase.table("Usuario").update(payload).eq("id_usuario", id_usuario).execute()
        return self.get_usuario_by_id(supabase=supabase, id_usuario=id_usuario)
