import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.constants import PairingCodeStatus, DeviceType

class PairingCodeCreate(BaseModel):
    child_code: str = Field(..., min_length=3)
    expires_in_minutes: int = Field(default=10, ge=5, le=60)

class PairingCodeResponse(BaseModel):
    pairing_code: str
    child_code: str
    child_name: str
    daycare_code: str
    daycare_name: str
    expires_at: datetime
    qr_payload: str

class PairingCodeListResponse(BaseModel):
    code: str
    status: PairingCodeStatus
    expires_at: datetime
    used_at: datetime | None = None
    child_code: str
    child_name: str
    daycare_code: str
    daycare_name: str

    class Config:
        from_attributes = True

class PairDeviceRequest(BaseModel):
    pairing_code: str = Field(..., min_length=5)
    device_identifier: str = Field(..., min_length=3)
    platform: str = Field(default="android")

class DeviceMiniResponse(BaseModel):
    device_code: str | None = None
    device_type: DeviceType

class AssignmentResponse(BaseModel):
    child_code: str
    child_name: str
    daycare_code: str
    daycare_name: str

class PairDeviceResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    device: DeviceMiniResponse
    assignment: AssignmentResponse

class DeviceDetails(BaseModel):
    device_code: str | None = None
    platform: str | None = None
    device_identifier: str | None = None
    is_active: bool
    last_seen_at: datetime | None = None
    paired_at: datetime | None = None

class ChildTrackerResponse(BaseModel):
    child_code: str
    child_name: str
    device: DeviceDetails | None = None
