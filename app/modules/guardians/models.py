import uuid
from datetime import datetime
from sqlalchemy import String, Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.constants import GuardianStatus

class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    status: Mapped[GuardianStatus] = mapped_column(Enum(GuardianStatus), default=GuardianStatus.ACTIVE)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relaciones
    user = orm_relationship("User", back_populates="guardian", uselist=False, cascade="all, delete-orphan")
    child_links = orm_relationship("GuardianChild", back_populates="guardian", cascade="all, delete-orphan")
    daycare_links = orm_relationship("GuardianDaycare", back_populates="guardian", cascade="all, delete-orphan")
    devices = orm_relationship("Device", back_populates="guardian")


class GuardianChild(Base):
    __tablename__ = "guardian_children"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    guardian_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("guardians.id", ondelete="CASCADE"))
    child_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("children.id", ondelete="CASCADE"))
    relationship: Mapped[str] = mapped_column(String(50))  # MADRE, PADRE, TUTOR
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relaciones
    guardian = orm_relationship("Guardian", back_populates="child_links")
    child = orm_relationship("Child", back_populates="guardian_links")


class GuardianDaycare(Base):
    __tablename__ = "guardian_daycares"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    guardian_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("guardians.id", ondelete="CASCADE"))
    daycare_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("daycares.id", ondelete="CASCADE"))
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relaciones
    guardian = orm_relationship("Guardian", back_populates="daycare_links")
    daycare = orm_relationship("Daycare", back_populates="guardian_links")
