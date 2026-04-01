from datetime import datetime

from pydantic import BaseModel, Field


class CitaCreate(BaseModel):
    id_paciente: int
    id_prestador: int
    fecha_hora_cupo: datetime


class CitaUpdate(BaseModel):
    nueva_fecha_hora_cupo: datetime


class CitaDelete(BaseModel):
    motivo: str | None = Field(default=None, max_length=200)


class CitaResponse(BaseModel):
    id: int
    id_paciente: int
    id_prestador: int
    id_especialidad: int
    fecha_hora_cupo: datetime
    estado: str
    motivo_cancelacion: str | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime
