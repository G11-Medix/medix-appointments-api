import logging

from supabase import Client

from app.repositories.notificacion_cita_repository import NotificacionCitaRepository
from app.repositories.paciente_repository import PacienteRepository
from app.repositories.especialidad_repository import EspecialidadRepository

LOGGER = logging.getLogger(__name__)


class NotificacionCitaService:

    def __init__(self):
        self.repo = NotificacionCitaRepository()
        self.paciente_repo = PacienteRepository()
        self.especialidad_repo = EspecialidadRepository()

    def guardar_notificacion(self, supabase: Client, cita: dict):
        paciente = self._get_paciente_local(supabase, cita)
        if not paciente:
            raise Exception("Paciente no encontrado")

        if not paciente.get("id_usuario"):
            raise Exception("El paciente no tiene usuario asociado")

        especialidad = self._get_especialidad_local(supabase, cita)

        payload = {
            "id_cita": cita["id"],
            "id_paciente": paciente["id_paciente"],
            "id_institucion": cita["id_institucion"],
            "id_especialidad": especialidad["id_especialidad"] if especialidad else None,
            "telefono": paciente.get("telefono"),
            "fecha_cita": cita["fecha_hora_cupo"],
            "id_usuario": paciente["id_usuario"],
            "recordatorio_24h_enviado": False,
            "recordatorio_1h_enviado": False,
        }

        existente = self.repo.find_one(supabase, payload)

        if existente:
            result = self.repo.update(supabase, existente["id"], payload)
            LOGGER.debug("Notificacion de cita actualizada: %s", result)
            return result

        result = self.repo.insert(supabase, payload)
        LOGGER.debug("Notificacion de cita creada: %s", result)
        return result

    def eliminar_notificacion(
        self,
        supabase: Client,
        cita: dict,
    ):
        return self.repo.delete(
            supabase,
            id_cita=cita["id"],
            id_institucion=cita["id_institucion"],
        )

    def _get_paciente_local(self, supabase: Client, cita: dict) -> dict | None:
        tipo_documento = cita.get("tipo_documento")
        numero_documento = cita.get("numero_documento") or cita.get("cedula")

        if not tipo_documento or not numero_documento:
            raise Exception("La cita no incluye tipo y numero de documento del paciente")

        return self.paciente_repo.get_by_document(
            supabase,
            tipo_documento=str(tipo_documento),
            numero_documento=str(numero_documento),
        )

    def _get_especialidad_local(self, supabase: Client, cita: dict) -> dict | None:
        codigo_reps = cita.get("id_especialidad")

        if codigo_reps is None:
            return None

        especialidad = self.especialidad_repo.get_by_codigo_reps(
            supabase,
            codigo_reps=int(codigo_reps),
        )

        if not especialidad:
            raise Exception("Especialidad no encontrada")

        return especialidad
