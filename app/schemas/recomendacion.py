from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecomendacionBase(BaseModel):
    institucion_id: int
    especialidad_id: int
    codigo: str | None = Field(default=None, max_length=255)
    recomendaciones: dict[str, Any] | list[Any]
    prioridad: int | None = 1
    activa: bool | None = True


class RecomendacionCreate(RecomendacionBase):
    pass


class RecomendacionUpdate(BaseModel):
    institucion_id: int | None = None
    especialidad_id: int | None = None
    codigo: str | None = Field(default=None, max_length=255)
    recomendaciones: dict[str, Any] | list[Any] | None = None
    prioridad: int | None = None
    activa: bool | None = None


class RecomendacionResponse(RecomendacionBase):
    id: int
    created_at: datetime
