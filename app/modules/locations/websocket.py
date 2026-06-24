import uuid
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.database import async_session_maker
from app.core.constants import UserRole
from app.utils.date_utils import parse_iso_datetime
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

@router.websocket("/ws/tracking/children/{child_code}/location")
async def child_tracking_websocket(websocket: WebSocket, child_code: str):
    """
    WebSocket por el cual los rastreadores GPS del niño transmiten la telemetría periódicamente.
    Cierra sesión tras procesar cada mensaje para optimizar la pool de conexiones.
    """
    await manager.connect_tracker(child_code, websocket)
    try:
        while True:
            # Esperar coordenadas en formato JSON
            data = await websocket.receive_json()
            
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
                    # Enviar log de error pero mantener el socket activo
                    logger.error(f"Error procesando lectura de tracker del niño {child_code}: {ex}")
                    
    except WebSocketDisconnect:
        logger.info(f"Dispositivo del niño {child_code} se desconectó.")
    except Exception as e:
        logger.error(f"Error de conexión en WebSocket de rastreador {child_code}: {e}")
    finally:
        manager.disconnect_tracker(child_code)


@router.websocket("/ws/guardians/{guardian_id}/children/{child_code}/live-location")
async def guardian_live_location_websocket(
    websocket: WebSocket,
    guardian_id: uuid.UUID,
    child_code: str,
    token: str | None = Query(default=None)
):
    """
    WebSocket utilizado por la app móvil del tutor para ver en vivo al niño en el mapa.
    Seguridad:
    - Valida validez de token JWT.
    - Valida que pertenezca al tutor correspondiente o sea administrador.
    - Valida que el niño exista y esté vinculado con el tutor.
    Retorna la última ubicación conocida al conectarse y retransmite cada nueva actualización.
    """
    query_params = websocket.query_params
    token_str = token or query_params.get("token")

    async with async_session_maker() as db:
        try:
            # 1. Autenticación
            try:
                user = await UserService.get_current_user_ws(token_str, db)
            except Exception as auth_err:
                logger.warning(f"Intento de conexión a WS sin autorización para tutor {guardian_id}: {auth_err}")
                await websocket.close(code=4001, reason="No autorizado: Token inválido.")
                return

            # 2. Control de accesos del tutor
            if user.role != UserRole.ADMIN and user.guardian_id != guardian_id:
                await websocket.close(code=4003, reason="Prohibido: No tienes acceso a este tutor.")
                return

            # 3. Validar existencia del niño
            child = await ChildRepository.get_by_code(db, child_code)
            if not child:
                await websocket.close(code=4004, reason="No encontrado: Niño no registrado.")
                return

            # 4. Validar vinculación tutor-niño
            link = await GuardianRepository.get_child_link(db, guardian_id, child.id)
            if not link and user.role != UserRole.ADMIN:
                await websocket.close(code=4003, reason="Prohibido: El tutor no está vinculado a este niño.")
                return

            # 5. Aceptar conexión y registrar
            await manager.connect_guardian(child_code, websocket)

            # 6. Enviar última ubicación conocida de inmediato si existe
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
                    "received_at": last_loc.received_at.isoformat()
                }
                await websocket.send_json(init_payload)

        except Exception as init_err:
            logger.error(f"Error inicializando WebSocket para tutor {guardian_id}: {init_err}")
            await websocket.close(code=1011, reason="Error interno de servidor.")
            return

    # Escucha desconexiones de forma asíncrona para limpiar el ConnectionManager
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Tutor {guardian_id} cerró mapa del niño {child_code}.")
    except Exception as e:
         logger.error(f"Error en bucle de WebSocket para tutor {guardian_id}: {e}")
    finally:
        manager.disconnect_guardian(child_code, websocket)
