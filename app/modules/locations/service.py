import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.constants import AlertStatus, AlertType, AlertSeverity
from app.utils.date_utils import get_now
from app.modules.children.repository import ChildRepository
from app.modules.daycares.repository import DaycareRepository
from app.modules.guardians.repository import GuardianRepository
from app.modules.devices.repository import DeviceRepository
from app.modules.locations.repository import LocationRepository
from app.modules.locations.schemas import LocationInput
from app.modules.alerts.models import Alert, AlertNotificationLog
from app.modules.alerts.repository import AlertRepository
from app.modules.notifications.service import NotificationService
from app.shared.geo.spatial_service import SpatialService
from app.shared.websocket.connection_manager import manager

logger = logging.getLogger("app.locations")

class LocationService:
    @classmethod
    async def process_child_location(
        cls,
        db: AsyncSession,
        child_code: str,
        loc_in: LocationInput
    ) -> None:
        """
        Procesa la telemetría enviada por el dispositivo del niño:
        1. Valida existencia de niño y guardería.
        2. Determina si el punto está dentro del área (usando tolerancia GPS).
        3. Registra en el historial y actualiza el caché de última ubicación.
        4. Transmite por WebSockets a los tutores observando en tiempo real.
        5. Evalúa si amerita disparar alertas (fuera del área >=3 veces o >=15 segundos).
        6. Despacha notificaciones FCM a los dispositivos del tutor aplicando cooldown.
        """
        # 1. Validar entidades
        child = await ChildRepository.get_by_code(db, child_code)
        if not child:
            logger.error(f"Ubicación recibida para niño inexistente: {child_code}")
            raise NotFoundException(f"Niño con código '{child_code}' no registrado.")

        daycare = await DaycareRepository.get_by_id(db, child.daycare_id)
        if not daycare:
            logger.error(f"El niño {child_code} está asociado a una guardería inexistente: {child.daycare_id}")
            raise NotFoundException("Guardería asociada no encontrada.")

        # 2. Evaluar geocercas
        point_geom = SpatialService.create_point(loc_in.longitude, loc_in.latitude)
        
        if daycare.area is None:
            logger.warning(f"La guardería '{daycare.name}' no tiene perímetro configurado. Saltando alertas.")
            is_inside_area = True
        else:
            is_inside_area = await SpatialService.check_if_inside_with_tolerance(
                db=db,
                daycare_area=daycare.area,
                point=point_geom,
                tolerance_meters=settings.GPS_TOLERANCE_METERS
            )

        # 3. Guardar en BD
        new_loc = await LocationRepository.create_location(
            db=db,
            child_id=child.id,
            daycare_id=daycare.id,
            latitude=loc_in.latitude,
            longitude=loc_in.longitude,
            accuracy=loc_in.accuracy,
            speed=loc_in.speed,
            heading=loc_in.heading,
            is_inside_area=is_inside_area,
            received_at=loc_in.received_at
        )

        await LocationRepository.update_current_location(
            db=db,
            child_id=child.id,
            daycare_id=daycare.id,
            latitude=loc_in.latitude,
            longitude=loc_in.longitude,
            accuracy=loc_in.accuracy,
            is_inside_area=is_inside_area,
            received_at=loc_in.received_at
        )

        # 4. Difusión en tiempo real vía WebSocket
        monitoring_status = "INSIDE_AREA" if is_inside_area else "OUTSIDE_AREA"
        ws_payload = {
            "child_code": child.code,
            "child_name": child.full_name,
            "daycare_code": daycare.code,
            "daycare_name": daycare.name,
            "latitude": loc_in.latitude,
            "longitude": loc_in.longitude,
            "accuracy": loc_in.accuracy,
            "is_inside_area": is_inside_area,
            "monitoring_status": monitoring_status,
            "received_at": loc_in.received_at.isoformat()
        }
        await manager.broadcast_to_guardians(child.code, ws_payload)

        # Si está adentro, reiniciamos y no evaluamos alertas
        if is_inside_area:
            return

        # 5. Evaluar reglas de Alertas
        # Buscar historial reciente de ubicaciones para el análisis temporal y de lecturas consecutivas
        recent = await LocationRepository.get_recent_locations(db, child.id, limit=10)
        
        # Unimos la nueva con las anteriores (excluyendo duplicados si ya se persistió y sale en el select)
        history = [new_loc] + [l for l in recent if l.id != new_loc.id]

        consecutive_outside = 0
        earliest_outside_time = None

        for loc in history:
            if not loc.is_inside_area:
                consecutive_outside += 1
                earliest_outside_time = loc.received_at
            else:
                break

        trigger_alert = False
        
        # Regla A: 3 Lecturas consecutivas fuera
        if consecutive_outside >= settings.ALERT_OUTSIDE_CONSECUTIVE_LIMIT:
            trigger_alert = True

        # Regla B: Fuera del área por más de 15 segundos
        if consecutive_outside >= 1 and earliest_outside_time:
            duration = (loc_in.received_at - earliest_outside_time).total_seconds()
            if duration >= settings.ALERT_OUTSIDE_SECONDS_LIMIT:
                trigger_alert = True

        if not trigger_alert:
            return

        # Validar si ya existe una alerta activa OUT_OF_AREA
        active_alert = await AlertRepository.get_active_alert_by_child_and_type(
            db=db,
            child_id=child.id,
            alert_type=AlertType.OUT_OF_AREA
        )

        if active_alert:
            # Ya hay una alerta en curso, no duplicamos
            return

        # Crear nueva alerta
        from app.utils.code_generator import generate_alert_code
        alert_code = generate_alert_code()
        
        new_alert = Alert(
            code=alert_code,
            child_id=child.id,
            daycare_id=daycare.id,
            location_id=new_loc.id,
            alert_type=AlertType.OUT_OF_AREA,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.NEW,
            title="Alerta de seguridad",
            message=f"El niño {child.full_name} ha salido del área de la guardería {daycare.name}.",
            created_at=get_now()
        )
        db.add(new_alert)
        await db.flush()

        # 6. Despachar notificaciones push a todos los tutores vinculados al niño
        guardians = await GuardianRepository.get_guardians_by_child(db, child.id)
        
        for guardian in guardians:
            # Obtener dispositivos registrados del tutor
            devices = await DeviceRepository.get_active_guardian_devices(db, guardian.id)
            
            for device in devices:
                if not device.fcm_token:
                    continue

                # Cooldown de 5 minutos para evitar spam de notificaciones por tutor
                cooldown_cutoff = get_now() - timedelta(seconds=settings.ALERT_COOLDOWN_SECONDS)
                cooldown_query = select(AlertNotificationLog).join(Alert).filter(
                    and_(
                        Alert.child_id == child.id,
                        AlertNotificationLog.guardian_id == guardian.id,
                        AlertNotificationLog.created_at >= cooldown_cutoff
                    )
                ).limit(1)
                
                cooldown_result = await db.execute(cooldown_query)
                if cooldown_result.scalar_one_or_none():
                    logger.info(f"Notificación omitida para el tutor {guardian.id} debido a cooldown activo.")
                    continue

                # Preparar payload FCM
                push_data = {
                    "alert_id": str(new_alert.id),
                    "child_code": child.code,
                    "child_name": child.full_name,
                    "daycare_code": daycare.code,
                    "daycare_name": daycare.name,
                    "alert_type": AlertType.OUT_OF_AREA.value,
                    "severity": AlertSeverity.HIGH.value,
                    "status": AlertStatus.NEW.value,
                    "created_at": new_alert.created_at.isoformat(),
                    "open_map": "false"
                }

                # Envío push y registro asíncrono
                await NotificationService.log_and_send_notification(
                    db=db,
                    alert_id=new_alert.id,
                    guardian_id=guardian.id,
                    device_id=device.id,
                    fcm_token=device.fcm_token,
                    title="Alerta de seguridad",
                    body=f"El niño {child.full_name} salió del área de la guardería.",
                    data=push_data
                )
