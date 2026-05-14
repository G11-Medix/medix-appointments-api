from supabase import Client


class NotificacionCitaRepository:

    def find_one(self, supabase: Client, payload: dict):
        query = (
            supabase.table("notificaciones_citas")
            .select("*")
            .eq("id_paciente", payload["id_paciente"])
            .eq("id_institucion", payload["id_institucion"])
            .eq("id_especialidad", payload["id_especialidad"])
        )
        '''
        if payload["id_especialidad"] is None:
            query = query.is_("id_especialidad", "null")
        else:
            query = query.eq("id_especialidad", payload["id_especialidad"])
        '''
        res = query.limit(1).execute()
        
        return res.data[0] if res.data else None
        

    def insert(self, supabase: Client, payload: dict):

        response = (
            supabase.table("notificaciones_citas")
            .insert(payload)
            .execute()
        )

        print("INSERT RESPONSE:", response)

        return response.data


    def update(self, supabase: Client, id_row: int, payload: dict):

        response = (
            supabase.table("notificaciones_citas")
            .update(payload)
            .eq("id", id_row)
            .execute()
        )

        print("UPDATE RESPONSE:", response)

        return response.data

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