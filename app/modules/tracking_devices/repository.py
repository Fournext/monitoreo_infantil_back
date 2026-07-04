import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.modules.tracking_devices.models import TrackerPairingCode
from app.modules.devices.models import Device
from app.core.constants import PairingCodeStatus, DeviceType

class TrackingDeviceRepository:
    @staticmethod
    async def get_pairing_code_by_code(db: AsyncSession, code: str) -> TrackerPairingCode | None:
        """Busca un código de emparejamiento por su valor de texto."""
        result = await db.execute(
            select(TrackerPairingCode)
            .filter(TrackerPairingCode.code == code)
            .options(selectinload(TrackerPairingCode.child), selectinload(TrackerPairingCode.daycare))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_pairing_codes_by_child(db: AsyncSession, child_id: uuid.UUID) -> list[TrackerPairingCode]:
        """Obtiene el historial de códigos de emparejamiento asociados a un niño."""
        result = await db.execute(
            select(TrackerPairingCode)
            .filter(TrackerPairingCode.child_id == child_id)
            .order_by(TrackerPairingCode.created_at.desc())
            .options(selectinload(TrackerPairingCode.child), selectinload(TrackerPairingCode.daycare))
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_pairing_code(
        db: AsyncSession,
        code: str,
        child_id: uuid.UUID,
        daycare_id: uuid.UUID,
        created_by_user_id: uuid.UUID | None,
        expires_at: datetime
    ) -> TrackerPairingCode:
        """Crea un nuevo código de emparejamiento en la base de datos."""
        pairing_code = TrackerPairingCode(
            code=code,
            child_id=child_id,
            daycare_id=daycare_id,
            created_by_user_id=created_by_user_id,
            expires_at=expires_at,
            status=PairingCodeStatus.ACTIVE
        )
        db.add(pairing_code)
        await db.flush()
        return pairing_code

    @staticmethod
    async def get_active_device_by_child(db: AsyncSession, child_id: uuid.UUID) -> Device | None:
        """Busca el dispositivo rastreador activo actualmente vinculado a un niño."""
        result = await db.execute(
            select(Device).filter(
                and_(
                    Device.child_id == child_id,
                    Device.device_type == DeviceType.CHILD_TRACKER,
                    Device.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_device_by_identifier_and_type(
        db: AsyncSession, 
        device_identifier: str, 
        device_type: DeviceType
    ) -> Device | None:
        """Busca un dispositivo por su identificador único físico y tipo."""
        result = await db.execute(
            select(Device).filter(
                and_(
                    Device.device_identifier == device_identifier,
                    Device.device_type == device_type
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_device_by_id(db: AsyncSession, device_id: uuid.UUID) -> Device | None:
        """Busca un dispositivo por su identificador primario (UUID)."""
        result = await db.execute(select(Device).filter(Device.id == device_id))
        return result.scalar_one_or_none()
