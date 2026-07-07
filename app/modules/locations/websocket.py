import uuid
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.guardians.models import Guardian
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.database import async_session_maker
from app.core.constants import UserRole
from app.utils.date_utils import parse_iso_datetime, to_bolivia_tz
from app.modules.auth.service import UserService
from app.modules.children.repository import ChildRepository
from app.modules.daycares.repository import DaycareRepository
from app.modules.guardians.repository import GuardianRepository
from app.modules.locations.repository import LocationRepository
from app.modules.locations.schemas import LocationInput
from app.modules.locations.service import LocationService
from app.shared.websocket.connection_manager import manager

logger = logging.getLogger("app.websockets")
router = APIRouter(tags=["WebSockets de Monitoreo"])

async def get_tracking_device_for_ws(token: str | None, db: AsyncSession) -> Any:
    import hashlib
    from sqlalchemy import select
    from app.modules.devices.models import Device
    from app.core.constants import DeviceType
    from app.core.security import decode_access_token
    from app.core.exceptions import UnauthorizedException, ForbiddenException
    
    if not token:
        raise UnauthorizedException("Falta el token de autenticación del dispositivo.")
        
    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedException("El token de rastreo es inválido o ha expirado.")
        
    role = payload.get("role")
    device_id_str = payload.get("sub")
    
    if role != "TRACKING_DEVICE" or not device_id_str:
        raise ForbiddenException("Token inválido para un dispositivo rastreador.")
        
    try:
        device_id = uuid.UUID(device_id_str)
    except ValueError:
        raise UnauthorizedException("El identificador del dispositivo es inválido.")
        
    result = await db.execute(select(Device).filter(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        raise UnauthorizedException("El dispositivo rastreador no está registrado.")
        
    if not device.is_active or device.device_type != DeviceType.CHILD_TRACKER or not device.child_id:
        raise UnauthorizedException("El dispositivo rastreador no está activo o no está vinculado a un niño.")
        
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if device.tracking_token_hash != token_hash:
        raise UnauthorizedException("El token de rastreo ha sido revocado o desvinculado.")
        
    return device

@router.websocket("/ws/tracking/location")
async def new_child_tracking_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None)
):
    """
    WebSocket recomendado por el cual los rastreadores envían su telemetría usando su token.
    Resuelve niño y guardería automáticamente sin child_code en la URL.
    """
    query_params = websocket.query_params
    token_str = token or query_params.get("token")
    
    async with async_session_maker() as db:
        try:
            device = await get_tracking_device_for_ws(token_str, db)
            child = await ChildRepository.get_by_id(db, device.child_id)
            if not child:
                await websocket.close(code=4004, reason="Niño no encontrado.")
                return
            child_code = child.code
        except Exception as auth_err:
            logger.warning(f"Intento de conexión a WS de rastreador sin autorización: {auth_err}")
            await websocket.close(code=4001, reason="No autorizado.")
            return

    await manager.connect_tracker(child_code, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"WebSocket [Dispositivo {child_code}]: Datos de telemetría recibidos: {data}")
            
            async with async_session_maker() as db:
                try:
                    # Validar nuevamente que el dispositivo siga activo/emparejado
                    device = await get_tracking_device_for_ws(token_str, db)
                    
                    loc_input = LocationInput(
                        latitude=data["latitude"],
                        longitude=data["longitude"],
                        accuracy=data.get("accuracy"),
                        speed=data.get("speed"),
                        heading=data.get("heading"),
                        received_at=parse_iso_datetime(data["received_at"])
                    )

                    await LocationService.process_location_from_device(
                        db=db,
                        device=device,
                        loc_in=loc_input
                    )
                    await db.commit()
                except Exception as ex:
                    logger.error(f"Error procesando lectura de tracker para dispositivo {device.id}: {ex}")
                    
    except WebSocketDisconnect:
        logger.info(f"Dispositivo del niño {child_code} se desconectó.")
    except Exception as e:
        logger.error(f"Error de conexión en WebSocket de rastreador {child_code}: {e}")
    finally:
        manager.disconnect_tracker(child_code)


@router.websocket("/ws/tracking/children/{child_code}/location")
async def child_tracking_websocket(
    websocket: WebSocket,
    child_code: str,
    token: str | None = Query(default=None)
):
    """
    [LEGACY/TESTING ONLY] WebSocket de rastreo antiguo.
    """
    logger.warning(f"Llamada a endpoint legado /ws/tracking/children/{child_code}/location para niño {child_code}.")
    """
    WebSocket por el cual los rastreadores GPS del niño transmiten la telemetría periódicamente.
    Valida token con rol TRACKING_DEVICE o ADMIN.
    """
    query_params = websocket.query_params
    token_str = token or query_params.get("token")
    
    async with async_session_maker() as db:
        try:
            # 1. Autenticación del cliente (puede ser un tracker o un administrador)
            user = None
            is_tracker = False
            try:
                device = await get_tracking_device_for_ws(token_str, db)
                is_tracker = True
            except Exception:
                try:
                    user = await UserService.get_current_user_ws(token_str, db)
                except Exception as auth_err:
                    logger.warning(f"Intento de conexión a WS de rastreador sin autorización para {child_code}: {auth_err}")
                    await websocket.close(code=4001, reason="No autorizado: Token inválido.")
                    return
            
            if not is_tracker:
                if getattr(user, "role", None) != UserRole.ADMIN:
                    await websocket.close(code=4003, reason="Prohibido: Rol no autorizado para rastreo.")
                    return

            # 2. Validar existencia del niño
            child = await ChildRepository.get_by_code(db, child_code)
            if not child:
                await websocket.close(code=4004, reason="No encontrado: Niño no registrado.")
                return

        except Exception as init_err:
            logger.error(f"Error inicializando WS de rastreador para niño {child_code}: {init_err}")
            await websocket.close(code=1011, reason="Error interno de servidor.")
            return

    await manager.connect_tracker(child_code, websocket)
    try:
        while True:
            # Esperar coordenadas en formato JSON
            data = await websocket.receive_json()
            logger.info(f"WebSocket [{child_code}]: Datos de telemetría recibidos en endpoint legado: {data}")
            
            async with async_session_maker() as db:
                try:
                    # Validar datos mínimos y mapear
                    loc_input = LocationInput(
                        latitude=data["latitude"],
                        longitude=data["longitude"],
                        accuracy=data.get("accuracy"),
                        speed=data.get("speed"),
                        heading=data.get("heading"),
                        received_at=parse_iso_datetime(data["received_at"])
                    )

                    await LocationService.process_child_location(
                        db=db,
                        child_code=child_code,
                        loc_in=loc_input
                    )
                    await db.commit() # Confirmar inserciones de ubicación y alertas creadas
                except Exception as ex:
                    logger.error(f"Error procesando lectura de tracker del niño {child_code}: {ex}")
                    
    except WebSocketDisconnect:
        logger.info(f"Dispositivo del niño {child_code} se desconectó.")
    except Exception as e:
        logger.error(f"Error de conexión en WebSocket de rastreador {child_code}: {e}")
    finally:
        manager.disconnect_tracker(child_code)


@router.websocket("/ws/guardians/me/children/{child_code}/live-location")
async def guardian_live_location_websocket(
    websocket: WebSocket,
    child_code: str,
    token: str | None = Query(default=None)
):
    """
    WebSocket utilizado por la app móvil del tutor para ver en vivo al niño en el mapa.
    Seguridad:
    - Valida token JWT del tutor.
    - Obtiene guardian_id desde el token.
    - Verifica que ese tutor esté vinculado al niño (o sea Admin).
    - Envia última ubicación conocida al conectarse y retransmite cada nueva actualización.
    """
    query_params = websocket.query_params
    token_str = token or query_params.get("token")

    async with async_session_maker() as db:
        try:
            # 1. Autenticación
            try:
                user = await UserService.get_current_user_ws(token_str, db)
            except Exception as auth_err:
                logger.warning(f"Intento de conexión a WS sin autorización para mapa en vivo de {child_code}: {auth_err}")
                await websocket.close(code=4001, reason="No autorizado: Token inválido.")
                return

            # 2. Control de accesos
            is_admin = getattr(user, "role", None) in (UserRole.ADMIN, UserRole.DAYCARE_MANAGER)
            
            if not is_admin:
                if not isinstance(user, Guardian):
                    await websocket.close(code=4003, reason="Prohibido: Rol inválido.")
                    return
                
                guardian_id = user.id
                
                # Validar existencia del niño
                child = await ChildRepository.get_by_code(db, child_code)
                if not child:
                    await websocket.close(code=4004, reason="No encontrado: Niño no registrado.")
                    return

                # Validar vinculación tutor-niño
                link = await GuardianRepository.get_child_link(db, guardian_id, child.id)
                if not link:
                    await websocket.close(code=4003, reason="Prohibido: El tutor no está vinculado a este niño.")
                    return
            else:
                child = await ChildRepository.get_by_code(db, child_code)
                if not child:
                    await websocket.close(code=4004, reason="No encontrado: Niño no registrado.")
                    return
                guardian_id = user.id

            # 3. Aceptar conexión y registrar
            await manager.connect_guardian(child_code, websocket)

            # 4. Enviar última ubicación conocida de inmediato si existe
            last_loc = await LocationRepository.get_last_location(db, child.id)
            if last_loc:
                daycare = await DaycareRepository.get_by_id(db, child.daycare_id)
                monitoring_status = "INSIDE_AREA" if last_loc.is_inside_area else "OUTSIDE_AREA"
                init_payload = {
                    "child_code": child.code,
                    "child_name": child.full_name,
                    "daycare_code": daycare.code if daycare else "",
                    "daycare_name": daycare.name if daycare else "",
                    "latitude": last_loc.latitude,
                    "longitude": last_loc.longitude,
                    "accuracy": last_loc.accuracy,
                    "is_inside_area": last_loc.is_inside_area,
                    "monitoring_status": monitoring_status,
                    "received_at": to_bolivia_tz(last_loc.received_at).isoformat()
                }
                await websocket.send_json(init_payload)

        except Exception as init_err:
            logger.error(f"Error inicializando WebSocket de mapa para tutor {guardian_id}: {init_err}")
            await websocket.close(code=1011, reason="Error interno de servidor.")
            return

    # Escucha desconexiones
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Tutor {guardian_id} cerró mapa del niño {child_code}.")
    except Exception as e:
         logger.error(f"Error en bucle de WebSocket para tutor {guardian_id}: {e}")
    finally:
        manager.disconnect_guardian(child_code, websocket)
