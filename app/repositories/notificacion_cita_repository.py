from supabase import Client


class NotificacionCitaRepository:

    def upsert(self, supabase: Client, payload: dict) -> dict:
        response = (
            supabase.table("notificaciones_citas")
            .upsert(
                payload,
                on_conflict="id_paciente,id_institucion,fecha_cita,id_especialidad"
            )
            .execute()
        )
        data = response.data or []
        return data[0] if data else {}

    def delete(
        self,
        supabase: Client,
        *,
        id_paciente: int,
        id_institucion: int,
        fecha_cita: str, 
        id_especialidad: int | None,  
    ) -> None:

        query = (
            supabase.table("notificaciones_citas")
            .delete()
            .eq("id_paciente", id_paciente)
            .eq("id_institucion", id_institucion)
            .eq("fecha_cita", fecha_cita)
        )

        
        if id_especialidad is None:
            query = query.is_("id_especialidad", "null")
        else:
            query = query.eq("id_especialidad", id_especialidad)

        query.execute()