import uuid
from datetime import datetime
from sqlalchemy import String, Enum, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.constants import ChildStatus

class Child(Base):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    daycare_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("daycares.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ChildStatus] = mapped_column(Enum(ChildStatus), default=ChildStatus.ACTIVE)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relaciones
    daycare = relationship("Daycare", back_populates="children")
    guardian_links = relationship("GuardianChild", back_populates="child", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="child")
    locations = relationship("ChildLocation", back_populates="child", cascade="all, delete-orphan")
    current_location = relationship("CurrentChildLocation", back_populates="child", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="child", cascade="all, delete-orphan")
