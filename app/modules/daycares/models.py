import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import String, Enum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.db.base import Base
from app.core.constants import DaycareStatus

class Daycare(Base):
    __tablename__ = "daycares"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[DaycareStatus] = mapped_column(Enum(DaycareStatus), default=DaycareStatus.ACTIVE)
    
    # Campo geométrico tipo Polígono con SRID 4326 e índice espacial GIST automático
    area: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relaciones
    children = relationship("Child", back_populates="daycare", cascade="all, delete-orphan")
    guardian_links = relationship("GuardianDaycare", back_populates="daycare", cascade="all, delete-orphan")
