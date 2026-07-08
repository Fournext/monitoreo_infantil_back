import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.constants import ChildStatus
from app.utils.date_utils import BoliviaDateTime

class ChildBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    age: int | None = Field(default=None, ge=0, le=18)
    status: ChildStatus = ChildStatus.ACTIVE

class ChildCreate(ChildBase):
    daycare_id: uuid.UUID

class ChildUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    age: int | None = Field(default=None, ge=0, le=18)
    status: ChildStatus | None = Field(default=None)
    daycare_id: uuid.UUID | None = Field(default=None)

class ChildResponse(ChildBase):
    id: uuid.UUID
    code: str
    daycare_id: uuid.UUID
    created_at: BoliviaDateTime
    updated_at: BoliviaDateTime

    class Config:
        from_attributes = True
