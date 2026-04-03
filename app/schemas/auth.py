from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AuthEligibilityReason = Literal[
    "PATIENT_NOT_FOUND",
    "PATIENT_INACTIVE",
    "USER_NOT_LINKED",
    "USER_INACTIVE",
    "AUTH_USER_NOT_FOUND",
    "PHONE_MISMATCH",
]


class EligiblePacienteSummary(BaseModel):
    id_paciente: int
    id_usuario: UUID | None = None
    telefono: str | None = None
    estado: str


class PhoneEligibilityResponse(BaseModel):
    authorized: bool
    reason: AuthEligibilityReason | None = None
    paciente: EligiblePacienteSummary | None = None


class GrantPatientAccessRequest(BaseModel):
    telefono: str = Field(min_length=8, max_length=20)
    rol: str = Field(default="PACIENTE", min_length=1, max_length=30)


class GrantPatientAccessResponse(BaseModel):
    id_paciente: int
    id_usuario: UUID
    telefono: str
    rol: str
    estado_usuario: str
    estado_paciente: str
    auth_user_created: bool
