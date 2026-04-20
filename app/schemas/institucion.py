from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)
