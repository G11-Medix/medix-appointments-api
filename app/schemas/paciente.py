from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PacienteBase(BaseModel):
    tipo_documento: str = Field(min_length=1, max_length=20)
    numero_documento: str = Field(min_length=1, max_length=20)
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    fecha_nacimiento: date
    telefono: str | None = Field(default=None, max_length=20)
    correo: str | None = Field(default=None, max_length=150)
    estado: str = Field(min_length=1, max_length=20)
    id_eps: int


class PacienteCreate(PacienteBase):
    model_config = ConfigDict(extra="forbid")


class PacienteUpdate(BaseModel):
    tipo_documento: str | None = Field(default=None, min_length=1, max_length=20)
    numero_documento: str | None = Field(default=None, min_length=1, max_length=20)
    nombres: str | None = Field(default=None, min_length=1, max_length=100)
    apellidos: str | None = Field(default=None, min_length=1, max_length=100)
    fecha_nacimiento: date | None = None
    telefono: str | None = Field(default=None, max_length=20)
    correo: str | None = Field(default=None, max_length=150)
    estado: str | None = Field(default=None, min_length=1, max_length=20)
    id_usuario: UUID | None = None
    id_eps: int | None = None


class PacienteResponse(PacienteBase):
    id_paciente: int
    fecha_creacion: datetime
    id_usuario: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    nombres: str
    apellidos: str
    documento: str
    eps: str
    correo: str
    telefono: str
    correo_verificado: bool = Field(default=True, serialization_alias="correoVerificado")
    telefono_verificado: bool = Field(default=True, serialization_alias="telefonoVerificado")

    model_config = ConfigDict(populate_by_name=True)
