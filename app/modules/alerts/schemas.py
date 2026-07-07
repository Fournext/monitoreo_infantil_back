import uuid
from datetime import datetime
from pydantic import BaseModel
from app.core.constants import AlertType, AlertSeverity, AlertStatus

class AlertResponse(BaseModel):
    id: uuid.UUID
    code: str
    child_id: uuid.UUID
    daycare_id: uuid.UUID
    location_id: uuid.UUID | None = None
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True

class AlertUpdateStatus(BaseModel):
    status: AlertStatus

class AdminAlertResponse(BaseModel):
    id: uuid.UUID
    code: str
    child_id: uuid.UUID
    child_code: str
    child_name: str
    daycare_id: uuid.UUID
    daycare_code: str
    daycare_name: str
    location_id: uuid.UUID | None = None
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True


class AdminAlertResponse(BaseModel):
    id: uuid.UUID
    code: str
    child_id: uuid.UUID
    child_code: str
    child_name: str
    daycare_id: uuid.UUID
    daycare_code: str
    daycare_name: str
    location_id: uuid.UUID | None = None
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True

