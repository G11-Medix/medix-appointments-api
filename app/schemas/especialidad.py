from pydantic import BaseModel, ConfigDict


class EspecialidadResponse(BaseModel):
    id_especialidad: int
    nombre: str
    codigo_reps: int | None = None

    model_config = ConfigDict(from_attributes=True)
