import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.constants import DaycareStatus
from app.shared.geo.schemas import GeoJSONPolygon

class DaycareBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str | None = Field(default=None, max_length=255)

class DaycareCreate(DaycareBase):
    pass
#esto aumente
class DaycareUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    status: DaycareStatus | None = Field(default=None)

class DaycareResponse(DaycareBase):
    id: uuid.UUID
    code: str
    status: DaycareStatus
    has_area: bool
    area: GeoJSONPolygon | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

