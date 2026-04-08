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

class CitaAppResponse(BaseModel):
    id: int
    nombre_ins: str
    especialidad: str
    fecha_hora_cupo: datetime
    
class CitaAppConfirmationResponse(BaseModel):
    doctorName: str
    fecha_hora_cupo: datetime
    especialidad: str
    clinicName: str
    address: str
    lat: float
    lon: float
    title: str | None
    message: str | None
    address: str = "SUCCESS"
