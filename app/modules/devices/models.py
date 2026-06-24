import uuid
from datetime import datetime
from sqlalchemy import String, Enum, ForeignKey, Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.constants import DeviceType

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, 
        ForeignKey("guardians.id", ondelete="SET NULL"), 
        nullable=True
    )
    child_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, 
        ForeignKey("children.id", ondelete="SET NULL"), 
        nullable=True
    )
    device_type: Mapped[DeviceType] = mapped_column(Enum(DeviceType))
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)  # android, ios, custom_tracker
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relaciones
    guardian = relationship("Guardian", back_populates="devices")
    child = relationship("Child", back_populates="devices")
