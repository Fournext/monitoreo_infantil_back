import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.modules.devices.models import Device
from app.core.constants import DeviceType
from app.modules.devices.schemas import DeviceRegisterRequest

class DeviceRepository:
    @staticmethod
    async def get_by_identifier(db: AsyncSession, device_identifier: str) -> Device | None:
        """Busca un dispositivo por su identificador único físico."""
        result = await db.execute(select(Device).filter(Device.device_identifier == device_identifier))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_guardian_devices(db: AsyncSession, guardian_id: uuid.UUID) -> list[Device]:
        """Obtiene la lista de dispositivos activos asociados a un tutor (para push)."""
        result = await db.execute(
            select(Device).filter(
                and_(
                    Device.guardian_id == guardian_id,
                    Device.is_active == True,
                    Device.device_type == DeviceType.GUARDIAN_PHONE
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def register_or_update(db: AsyncSession, register_in: DeviceRegisterRequest) -> Device:
        """
        Registra un dispositivo o actualiza su token FCM si ya existe.
        Asigna el tipo GUARDIAN_PHONE por defecto.
        """
        device = await DeviceRepository.get_by_identifier(db, register_in.device_identifier)

        if device:
            # Actualizar dispositivo existente
            device.fcm_token = register_in.fcm_token
            device.platform = register_in.platform
            device.guardian_id = register_in.guardian_id
            device.is_active = True
        else:
            # Crear uno nuevo
            device = Device(
                guardian_id=register_in.guardian_id,
                device_type=DeviceType.GUARDIAN_PHONE,
                fcm_token=register_in.fcm_token,
                device_identifier=register_in.device_identifier,
                platform=register_in.platform,
                is_active=True
            )
            db.add(device)

        await db.flush()
        return device
