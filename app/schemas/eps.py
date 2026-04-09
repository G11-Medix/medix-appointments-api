from pydantic import BaseModel, ConfigDict


class EpsResponse(BaseModel):
    id_eps: int
    nombre: str
    codigo: str
    estado: str

    model_config = ConfigDict(from_attributes=True)
