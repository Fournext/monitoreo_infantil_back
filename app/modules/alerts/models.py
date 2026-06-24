import uuid
from datetime import datetime
from sqlalchemy import String, Enum, ForeignKey, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.utils.date_utils import get_now
from app.core.constants import AlertType, AlertSeverity, AlertStatus, NotificationLogStatus

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    child_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("children.id", ondelete="CASCADE"))
    daycare_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("daycares.id", ondelete="CASCADE"))
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, 
        ForeignKey("child_locations.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), default=AlertType.OUT_OF_AREA)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), default=AlertSeverity.HIGH)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.NEW)
    
    title: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=get_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=get_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    child = relationship("Child", back_populates="alerts")
    notification_logs = relationship("AlertNotificationLog", back_populates="alert", cascade="all, delete-orphan")


class AlertNotificationLog(Base):
    __tablename__ = "alert_notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("alerts.id", ondelete="CASCADE"))
    guardian_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("guardians.id", ondelete="CASCADE"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, 
        ForeignKey("devices.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    fcm_token: Mapped[str] = mapped_column(String(255))
    status: Mapped[NotificationLogStatus] = mapped_column(Enum(NotificationLogStatus))
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=get_now)

    # Relaciones
    alert = relationship("Alert", back_populates="notification_logs")
