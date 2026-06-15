from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class MaxWebhookPayload(BaseModel):
    user_id: str = Field(min_length=1)
    text: str
