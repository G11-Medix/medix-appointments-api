from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NatsCommandEnvelope(BaseModel):
    correlation_id: str
    operation: str | None = None
    access_token: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class NatsErrorPayload(BaseModel):
    code: int
    detail: str


class NatsResponseEnvelope(BaseModel):
    correlation_id: str
    success: bool
    data: Any | None = None
    error: NatsErrorPayload | None = None

    model_config = ConfigDict(extra="forbid")
