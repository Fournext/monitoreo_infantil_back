import uuid
from datetime import datetime
from sqlalchemy import String, Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.constants import PairingCodeStatus

class TrackerPairingCode(Base):
    __tablename__ = "tracker_pairing_codes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        ForeignKey("children.id", ondelete="CASCADE")
    )
    daycare_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        ForeignKey("daycares.id", ondelete="CASCADE")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column()
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[PairingCodeStatus] = mapped_column(
        Enum(PairingCodeStatus), 
        default=PairingCodeStatus.ACTIVE
    )
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relaciones
    child = relationship("Child")
    daycare = relationship("Daycare")
    created_by = relationship("User")
