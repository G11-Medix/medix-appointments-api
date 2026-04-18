from pydantic import BaseModel


class DocumentoLegalResponse(BaseModel):
    id_documento: int
    version: str
    contenido: str
    fecha_publicacion: str


class AceptacionRequest(BaseModel):
    id_documento: int
    dispositivo: str


class ConsentStatusResponse(BaseModel):
    accepted: bool