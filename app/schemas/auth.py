from typing import Literal
from uuid import UUID

from pydantic import BaseModel


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
