from supabase import Client
from fastapi import HTTPException, status

from app.repositories.notificacion_cita_repository import NotificacionCitaRepository
from app.repositories.paciente_repository import PacienteRepository


class NotificacionCitaService:

    def __init__(self):
        self.repo = NotificacionCitaRepository()
        self.paciente_repo = PacienteRepository()

    def guardar_notificacion(
        self,
        supabase: Client,
        cita: dict,
    ):
        paciente = self.paciente_repo.get_by_id(
            supabase,
            cita["id_paciente"]
        )

        if not paciente:
            raise Exception("Paciente no encontrado")

        if not paciente.get("id_usuario"):
            raise Exception("El paciente no tiene usuario asociado")

        payload = {
            "id_paciente": cita["id_paciente"],
            "id_institucion": cita["id_institucion"],
            "id_especialidad": cita.get("id_especialidad"),
            "telefono": paciente.get("telefono"),
            "fecha_cita": cita["fecha_hora_cupo"],
            "id_usuario": paciente["id_usuario"], 
            "recordatorio_24h_enviado": False,
            "recordatorio_1h_enviado": False,
        }

        return self.repo.upsert(supabase, payload)


    def eliminar_notificacion(
        self,
        supabase: Client,
        cita: dict,
    ):
        return self.repo.delete(
            supabase,
            id_paciente=cita["id_paciente"],
            id_institucion=cita["id_institucion"],
            fecha_cita=cita["fecha_hora_cupo"],
            id_especialidad=cita.get("id_especialidad"),
        )