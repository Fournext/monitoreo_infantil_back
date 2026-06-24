import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.constants import ChildStatus

class ChildBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    age: int | None = Field(default=None, ge=0, le=18)
    status: ChildStatus = ChildStatus.ACTIVE

class ChildCreate(ChildBase):
    daycare_id: uuid.UUID

class ChildResponse(ChildBase):
    id: uuid.UUID
    code: str
    daycare_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
