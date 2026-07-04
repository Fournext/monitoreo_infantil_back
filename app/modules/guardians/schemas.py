import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.core.constants import GuardianStatus, ChildStatus

class GuardianBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = Field(default=None)

class GuardianCreate(GuardianBase):
    pass

class GuardianCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = Field(default=None)

class GuardianCreateResponse(BaseModel):
    id: uuid.UUID
    code: str
    temporary_pin: str
    full_name: str

class GuardianResponse(BaseModel):
    id: uuid.UUID
    code: str
    full_name: str
    phone: str | None = None
    email: EmailStr | None = None
    status: GuardianStatus

    class Config:
        from_attributes = True

class GuardianResetPinResponse(BaseModel):
    guardian_code: str
    temporary_pin: str
    must_change_pin: bool = True

class GuardianChildLinkRequest(BaseModel):
    daycare_code: str
    child_code: str
    relationship: str = Field(..., description="Relación: MADRE, PADRE, TUTOR, etc.")

class LinkDaycareRequest(BaseModel):
    daycare_code: str

class LinkChildRequest(BaseModel):
    daycare_code: str
    child_code: str
    relationship: str = Field(..., description="Relación: MADRE, PADRE, TUTOR, etc.")

class GuardianDaycareResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    address: str | None = None
    status: str

    class Config:
        from_attributes = True

class LinkedDaycareResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    address: str | None = None
    status: str

    class Config:
        from_attributes = True

class LocationSchema(BaseModel):
    latitude: float
    longitude: float
    accuracy: float | None = None
    is_inside_area: bool
    received_at: datetime

    class Config:
        from_attributes = True

class LinkedChildResponse(BaseModel):
    id: uuid.UUID
    code: str
    full_name: str
    age: int | None = None
    status: ChildStatus
    relationship: str
    daycare_code: str
    daycare_name: str
    has_active_alert: bool
    last_location: LocationSchema | None = None

    class Config:
        from_attributes = True

class GuardianChildResponse(BaseModel):
    child_code: str
    child_name: str
    child_age: int | None = None
    daycare_code: str
    daycare_name: str
    monitoring_status: str
    has_active_alert: bool
    last_location_at: datetime | None = None

    class Config:
        from_attributes = True

class GuardianChildrenListResponse(BaseModel):
    children: list[GuardianChildResponse]

class MonitoringChildSummary(BaseModel):
    child_code: str
    child_name: str
    child_age: int | None = None
    daycare_code: str
    daycare_name: str
    monitoring_status: str  # INSIDE_AREA, OUTSIDE_AREA, NO_LOCATION
    has_active_alert: bool
    last_location_at: datetime | None = None

    class Config:
        from_attributes = True

class GuardianMonitoringSummaryResponse(BaseModel):
    total_children: int
    total_daycares: int
    active_alerts: int
    children: list[MonitoringChildSummary]

class MonitoringSummaryResponse(BaseModel):
    total_children: int
    active_alerts: int
    children: list[MonitoringChildSummary]
