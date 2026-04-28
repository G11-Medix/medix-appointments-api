from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InstitucionResponse(BaseModel):
    id_institucion: int
    nombre: str
    nit: str
    direccion: str | None = None
    telefono: str | None = None
    estado: str
    longitud: float | None = None
    latitud: float | None = None
    logo_url: str | None = None
    service_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InstitucionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1)
    nit: str | None = Field(default=None, min_length=1)
    direccion: str | None = None
    telefono: str | None = None
    estado: str | None = Field(default=None, min_length=1)
    longitud: float | None = None
    latitud: float | None = None
    logo_url: str | None = None
    service_url: str | None = None

    @field_validator("logo_url", "service_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("La URL debe iniciar con http:// o https://")
        return normalized.rstrip("/")

    @field_validator("nombre", "nit", "estado", "direccion", "telefono")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class InstitucionHealthResponse(BaseModel):
    id_institucion: int
    status: Literal["UP", "DOWN", "NOT_CONFIGURED"]
    service_url: str | None = None
    status_code: int | None = None
    latency_ms: int | None = None
    message: str
