import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.constants import DeviceType

class FcmTokenRegisterRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10)
    platform: str = Field(default="android")
    device_identifier: str = Field(..., min_length=3)

class DeviceRegisterRequest(BaseModel):
    guardian_id: uuid.UUID
    fcm_token: str = Field(..., min_length=10)
    platform: str = Field(default="android")
    device_identifier: str = Field(..., min_length=3)

class DeviceResponse(BaseModel):
    id: uuid.UUID
    guardian_id: uuid.UUID | None = None
    child_id: uuid.UUID | None = None
    device_type: DeviceType
    fcm_token: str | None = None
    device_identifier: str | None = None
    platform: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
