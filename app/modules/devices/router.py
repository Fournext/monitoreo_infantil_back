from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.devices.schemas import DeviceRegisterRequest, DeviceResponse
from app.modules.devices.service import DeviceService
from app.modules.auth.service import require_roles
from app.core.constants import UserRole

router = APIRouter(prefix="/api/devices", tags=["Dispositivos"])

@router.post("/fcm-token", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
async def register_fcm_token(
    register_in: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Registra o actualiza el token FCM asociado a un tutor para enviarle alertas push. (Acceso: ADMIN, GUARDIAN)
    """
    device = await DeviceService.register_device(db, register_in)
    await db.commit()
    return device
