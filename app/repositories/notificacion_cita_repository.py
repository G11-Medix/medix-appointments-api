from supabase import Client


class NotificacionCitaRepository:

    def find_one(self, supabase: Client, payload: dict):

        res = (
            supabase.table("notificaciones_citas")
            .select("*")
            .eq("id_cita", payload["id_cita"])
            .eq("id_institucion", payload["id_institucion"])
            .limit(1)
            .execute()
        )

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
        id_cita: int,
        id_institucion: int,
    ):

        (
            supabase.table("notificaciones_citas")
            .delete()
            .eq("id_cita", id_cita)
            .eq("id_institucion", id_institucion)
            .execute()
        )