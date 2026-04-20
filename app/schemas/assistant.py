from datetime import date, datetime

from pydantic import BaseModel


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
    codigo_reps: int
    disponibilidad: list[AssistantAvailabilityDay]
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
