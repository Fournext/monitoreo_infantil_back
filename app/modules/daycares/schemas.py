import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from app.core.constants import DaycareStatus

class DaycareBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str | None = Field(default=None, max_length=255)

class DaycareCreate(DaycareBase):
    pass

class DaycareResponse(DaycareBase):
    id: uuid.UUID
    code: str
    status: DaycareStatus
    has_area: bool
    area: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
