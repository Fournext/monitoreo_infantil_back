from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.devices.schemas import FcmTokenRegisterRequest, DeviceRegisterRequest, DeviceResponse
from app.modules.devices.service import DeviceService
from app.modules.auth.dependencies import get_current_guardian
from app.modules.guardians.models import Guardian

router = APIRouter(prefix="/api/devices", tags=["Dispositivos"])

@router.post("/me/fcm-token", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
async def register_fcm_token(
    register_in: FcmTokenRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_guardian: Guardian = Depends(get_current_guardian)
):
    """
    Registra o actualiza el token FCM del tutor autenticado actual. (Acceso: GUARDIAN)
    """
    # Mapear a la estructura interna del repositorio/servicio
    mapped_request = DeviceRegisterRequest(
        guardian_id=current_guardian.id,
        fcm_token=register_in.fcm_token,
        platform=register_in.platform,
        device_identifier=register_in.device_identifier
    )
    device = await DeviceService.register_device(db, mapped_request)
    await db.commit()
    return device
