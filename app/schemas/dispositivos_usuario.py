from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class DispositivoUsuarioCreate(BaseModel):
    id_usuario: UUID
    token_dispositivo: str
    plataforma: str | None = None


class DispositivoUsuarioUpdate(BaseModel):
    token_dispositivo: str
    plataforma: str | None = None


class DispositivoUsuarioResponse(BaseModel):
    id: int
    id_usuario: UUID
    token_dispositivo: str
    plataforma: str | None
    actualizado_en: datetime