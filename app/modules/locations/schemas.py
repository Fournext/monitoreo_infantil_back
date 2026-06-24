import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class LocationInput(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy: float | None = Field(default=None, ge=0.0)
    speed: float | None = Field(default=None, ge=0.0)
    heading: float | None = Field(default=None, ge=0.0, le=360.0)
    received_at: datetime

class LocationResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    daycare_id: uuid.UUID
    latitude: float
    longitude: float
    accuracy: float | None = None
    speed: float | None = None
    heading: float | None = None
    is_inside_area: bool
    received_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class LiveLocationPayload(BaseModel):
    child_code: str
    child_name: str
    daycare_code: str
    daycare_name: str
    latitude: float
    longitude: float
    accuracy: float | None = None
    is_inside_area: bool
    monitoring_status: str  # INSIDE_AREA, OUTSIDE_AREA
    received_at: datetime
