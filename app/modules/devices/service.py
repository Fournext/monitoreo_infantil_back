from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.modules.devices.models import Device
from app.modules.devices.repository import DeviceRepository
from app.modules.guardians.repository import GuardianRepository
from app.modules.devices.schemas import DeviceRegisterRequest, DeviceResponse

class DeviceService:
    @staticmethod
    async def register_device(db: AsyncSession, register_in: DeviceRegisterRequest) -> DeviceResponse:
        """
        Registra o actualiza el dispositivo y token de notificaciones de un tutor.
        """
        guardian = await GuardianRepository.get_by_id(db, register_in.guardian_id)
        if not guardian:
            raise NotFoundException(f"Tutor con ID '{register_in.guardian_id}' no encontrado.")

        device = await DeviceRepository.register_or_update(db, register_in)
        return DeviceResponse.model_validate(device)
