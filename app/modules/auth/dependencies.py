import uuid
from typing import Annotated, Any
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.constants import UserRole
from app.modules.auth.models import User
from app.modules.guardians.models import Guardian

# Define OAuth2 scheme matching /api/auth/login or /api/auth/guardian/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    db: AsyncSession = Depends(get_db)
) -> User | Guardian:
    """
    Decodes the JWT token and fetches either the User or Guardian entity.
    """
    if not token:
        raise UnauthorizedException("Falta el token de autenticación.")
        
    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedException("El token es inválido o ha expirado.")
        
    user_id_str = payload.get("sub")
    role = payload.get("role")
    if not user_id_str or not role:
        raise UnauthorizedException("El token no contiene claims válidos.")
        
    try:
        entity_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("El identificador en el token es inválido.")
        
    if role == "GUARDIAN":
        from app.modules.guardians.repository import GuardianRepository
        guardian = await GuardianRepository.get_by_id(db, entity_id)
        if not guardian:
            raise UnauthorizedException("El tutor asociado al token ya no existe.")
        # Dynamically set role attribute on Guardian object
        guardian.role = "GUARDIAN"
        return guardian
    else:
        from app.modules.auth.repository import UserRepository
        user = await UserRepository.get_by_id(db, entity_id)
        if not user:
            raise UnauthorizedException("El usuario asociado al token ya no existe.")
        return user

async def get_current_guardian(
    current_user: Annotated[User | Guardian, Depends(get_current_user)]
) -> Guardian:
    """
    Requires the current authenticated client to be a Guardian.
    """
    if not isinstance(current_user, Guardian):
        raise ForbiddenException("Esta acción requiere el rol de tutor (GUARDIAN).")
    return current_user

async def require_admin(
    current_user: Annotated[User | Guardian, Depends(get_current_user)]
) -> User:
    """
    Requires the current authenticated user to be an ADMIN.
    """
    if isinstance(current_user, Guardian) or current_user.role != UserRole.ADMIN:
        raise ForbiddenException("No tienes permisos suficientes para realizar esta acción (ADMIN).")
    return current_user

async def require_daycare_manager(
    current_user: Annotated[User | Guardian, Depends(get_current_user)]
) -> User:
    """
    Requires the current authenticated user to be an ADMIN or DAYCARE_MANAGER.
    """
    if isinstance(current_user, Guardian) or current_user.role not in (UserRole.ADMIN, UserRole.DAYCARE_MANAGER):
        raise ForbiddenException("No tienes permisos suficientes para realizar esta acción (DAYCARE_MANAGER).")
    return current_user

async def require_tracking_device(
    current_user: Annotated[User | Guardian, Depends(get_current_user)]
) -> User:
    """
    Requires the current authenticated user to be a TRACKING_DEVICE.
    """
    if isinstance(current_user, Guardian) or current_user.role != "TRACKING_DEVICE":
        raise ForbiddenException("No tienes permisos suficientes para realizar esta acción (TRACKING_DEVICE).")
    return current_user

async def get_current_tracking_device(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Valida el token de un dispositivo rastreador y confirma que esté activo y emparejado.
    """
    import hashlib
    from app.modules.devices.models import Device
    from app.core.constants import DeviceType
    
    if not token:
        raise UnauthorizedException("Falta el token de autenticación del dispositivo.")
        
    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedException("El token de rastreo es inválido o ha expirado.")
        
    role = payload.get("role")
    device_id_str = payload.get("sub")
    child_id_str = payload.get("child_id")
    
    if role != "TRACKING_DEVICE" or not device_id_str or not child_id_str:
        raise ForbiddenException("Token inválido para un dispositivo rastreador.")
        
    try:
        device_id = uuid.UUID(device_id_str)
    except ValueError:
        raise UnauthorizedException("El identificador del dispositivo es inválido.")
        
    # Consultar base de datos
    result = await db.execute(select(Device).filter(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        raise UnauthorizedException("El dispositivo rastreador no está registrado.")
        
    if not device.is_active or device.device_type != DeviceType.CHILD_TRACKER or not device.child_id:
        raise UnauthorizedException("El dispositivo rastreador no está activo o no está vinculado a un niño.")
        
    # Verificar validez del token contra el hash guardado en BD (para revocación instantánea)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if device.tracking_token_hash != token_hash:
        raise UnauthorizedException("El token de rastreo ha sido revocado o desvinculado.")
        
    return device
