import uuid
from pydantic import BaseModel
from app.core.constants import AlertType, AlertSeverity, AlertStatus
from app.utils.date_utils import BoliviaDateTime

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
    created_at: BoliviaDateTime
    updated_at: BoliviaDateTime
    resolved_at: BoliviaDateTime | None = None
    
    # Campos adicionales para UI de notificaciones
    child_code: str
    child_name: str
    daycare_code: str
    daycare_name: str

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
    created_at: BoliviaDateTime
    updated_at: BoliviaDateTime
    resolved_at: BoliviaDateTime | None = None

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
    created_at: BoliviaDateTime
    updated_at: BoliviaDateTime
    resolved_at: BoliviaDateTime | None = None

    class Config:
        from_attributes = True

