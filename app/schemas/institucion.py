from pydantic import BaseModel, ConfigDict


class InstitucionResponse(BaseModel):
    id_institucion: int
    nombre: str
    nit: str
    direccion: str | None = None
    telefono: str | None = None
    estado: str

    model_config = ConfigDict(from_attributes=True)
