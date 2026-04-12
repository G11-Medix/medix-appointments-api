from datetime import date, datetime, time

from pydantic import BaseModel, Field


class AssistantSpecialtyResponse(BaseModel):
    id: int
    nombre: str


class AssistantInstitutionResponse(BaseModel):
    id_institucion: int
    nombre: str
    estado: str
    especialidades: list[int]


class AssistantAvailabilitySlot(BaseModel):
    hora: str
    fecha_hora: datetime
    id_prestador: int
    nombre_prestador: str


class AssistantAvailabilityDay(BaseModel):
    fecha: date
    slots: list[AssistantAvailabilitySlot]


class AssistantAvailabilityResponse(BaseModel):
    id_institucion: int
    nombre_institucion: str
    id_especialidad: int
    disponibilidad: list[AssistantAvailabilityDay]


class AssistantScheduleAppointmentRequest(BaseModel):
    id_paciente: int
    id_institucion: int
    id_especialidad: int
    fecha: date
    hora: time


class AssistantCancelAppointmentRequest(BaseModel):
    id_institucion: int
    motivo: str | None = Field(default=None, max_length=200)


class AssistantRescheduleAppointmentRequest(BaseModel):
    id_institucion: int
    id_especialidad: int
    nueva_fecha: date
    nueva_hora: time


class AssistantAppointmentResponse(BaseModel):
    id: int
    id_paciente: int
    id_prestador: int
    id_especialidad: int
    fecha_hora_cupo: datetime
    estado: str
    motivo_cancelacion: str | None = None
    fecha_creacion: datetime | None = None
    fecha_actualizacion: datetime | None = None


class AssistantAppointmentActionResponse(BaseModel):
    mensaje: str
    cita: AssistantAppointmentResponse


class AssistantPatientResponse(BaseModel):
    id_paciente: int
    tipo_documento: str
    numero_documento: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    telefono: str | None = None
    correo: str | None = None
    estado: str
    fecha_creacion: datetime
