from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class CitaCreate(BaseModel):
    tipo_documento: str = Field(min_length=1, max_length=20)
    numero_documento: str = Field(min_length=1, max_length=20)
    id_prestador: int
    fecha: date
    hora: time


class CitaUpdate(BaseModel):
    nueva_fecha_hora_cupo: datetime


class CitaDelete(BaseModel):
    motivo: str | None = Field(default=None, max_length=200)


class CitaResponse(BaseModel):
    id: int
    id_paciente: int
    id_prestador: int
    nombre_prestador: str | None = None
    id_especialidad: int
    fecha_hora_cupo: datetime
    estado: str
    motivo_cancelacion: str | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class CitaIpsResponse(BaseModel):
    id: int
    nombre_paciente: str
    cedula_paciente: str
    nombre_prestador: str | None = None
    especialidad: str
    fecha: date
    hora: time
    estado_cita: str
    motivo_cancelacion: str | None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class CitaConfirmacionResponse(BaseModel):
    doctor: str
    fecha: datetime
    institucion: str
    direccion: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    estado: str

class CitaAppResponse(BaseModel):
    id: int
    id_institucion: int
    nombre_institucion: str = Field(serialization_alias="nombre_ins")
    logo_url: str | None = None
    especialidad: str
    estado: str
    fecha: date | None = None
    hora: time | None = None

    model_config = ConfigDict(populate_by_name=True)
