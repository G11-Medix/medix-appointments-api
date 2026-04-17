from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CitaCreate(BaseModel):
    tipo_documento: str = Field(min_length=1, max_length=20)
    numero_documento: str = Field(min_length=1, max_length=20)
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

class CitaAppResponse(BaseModel):
    id: int
    nombre_institucion: str = Field(serialization_alias="nombre_ins")
    especialidad: str
    fecha_hora_cupo: datetime

    model_config = ConfigDict(populate_by_name=True)
