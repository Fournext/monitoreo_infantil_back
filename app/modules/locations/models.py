import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import ForeignKey, Float, Boolean, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.db.base import Base

class ChildLocation(Base):
    __tablename__ = "child_locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("children.id", ondelete="CASCADE"))
    daycare_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("daycares.id", ondelete="CASCADE"))
    
    # Punto geográfico con SRID 4326 e índice espacial GIST
    point: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True)
    )
    
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_inside_area: Mapped[bool] = mapped_column(Boolean)
    
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    child = relationship("Child", back_populates="locations")


class CurrentChildLocation(Base):
    __tablename__ = "current_child_locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        ForeignKey("children.id", ondelete="CASCADE"), 
        unique=True, 
        index=True
    )
    daycare_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("daycares.id", ondelete="CASCADE"))
    
    # Punto geográfico con SRID 4326 e índice espacial GIST
    point: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True)
    )
    
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_inside_area: Mapped[bool] = mapped_column(Boolean)
    
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relaciones
    child = relationship("Child", back_populates="current_location")
