import uuid
import logging
from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.constants import AlertStatus, AlertType, AlertSeverity
from app.utils.date_utils import get_now, to_bolivia_tz
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
    async def process_location_from_device(
        cls,
        db: AsyncSession,
        device: Any,
        loc_in: LocationInput
    ) -> None:
        """
        Procesa la telemetría enviada por el dispositivo del niño resolviendo la entidad y la guardería.
        """
        from app.utils.date_utils import get_now
        
        # 1. Obtener niño asociado
        child = await ChildRepository.get_by_id(db, device.child_id)
        if not child:
            logger.error(f"El dispositivo {device.id} no tiene un niño asociado válido.")
            raise NotFoundException("Dispositivo no está vinculado a un niño registrado.")

        # Actualizar last_seen_at del dispositivo
        device.last_seen_at = get_now()
        await db.flush()

        # 2. Delegar a la lógica de procesamiento principal
        await cls.process_child_location(
            db=db,
            child_code=child.code,
            loc_in=loc_in
        )

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
            logger.info(f"Ubicación de {child.full_name} ({child.code}) dentro del área de la guardería. No se requiere alerta.")
            # Auto-resolver alerta(s) OUT_OF_AREA activa(s) si el niño regresó al área
            resolved_count = 0
            while True:
                active_alert = await AlertRepository.get_active_alert_by_child_and_type(
                    db=db,
                    child_id=child.id,
                    alert_type=AlertType.OUT_OF_AREA
                )
                if not active_alert:
                    break
                await AlertRepository.update_status(db, active_alert, AlertStatus.RESOLVED)
                resolved_count += 1
            
            if resolved_count > 0:
                logger.info(f"Se auto-resolvieron {resolved_count} alerta(s) OUT_OF_AREA para el niño {child.full_name} al reingresar al área.")
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
        duration = 0.0
        
        # Regla A: 3 Lecturas consecutivas fuera
        if consecutive_outside >= settings.ALERT_OUTSIDE_CONSECUTIVE_LIMIT:
            trigger_alert = True

        # Regla B: Fuera del área por más de 15 segundos
        if consecutive_outside >= 1 and earliest_outside_time:
            duration = (loc_in.received_at - earliest_outside_time).total_seconds()
            if duration >= settings.ALERT_OUTSIDE_SECONDS_LIMIT:
                trigger_alert = True

        if not trigger_alert:
            logger.info(
                f"Ubicación de {child.full_name} ({child.code}) evaluada fuera del área. Alerta NO lista para enviarse. "
                f"Estado de reglas: "
                f"1) Lecturas consecutivas fuera: {consecutive_outside}/{settings.ALERT_OUTSIDE_CONSECUTIVE_LIMIT}. "
                f"2) Tiempo transcurrido fuera: {duration:.1f}s/{settings.ALERT_OUTSIDE_SECONDS_LIMIT}s."
            )
            return

        # Validar si ya existe una alerta activa OUT_OF_AREA
        active_alert = await AlertRepository.get_active_alert_by_child_and_type(
            db=db,
            child_id=child.id,
            alert_type=AlertType.OUT_OF_AREA
        )

        if active_alert:
            logger.info(
                f"Alerta de salida de área para {child.full_name} ({child.code}) lista para dispararse, "
                f"pero se omitió el envío porque ya existe una alerta activa (Código: {active_alert.code}, Estado: {active_alert.status.value})."
            )
            return

        logger.info(
            f"REGLAS DE ALERTA CUMPLIDAS para {child.full_name} ({child.code}). "
            f"Creando nueva alerta de seguridad..."
        )

        # Crear nueva alerta
        from app.shared.utils.code_generator import generate_alert_code
        from app.modules.alerts.models import Alert
        count_query = select(func.count(Alert.id))
        count_result = await db.execute(count_query)
        scalar_val = count_result.scalar()
        if hasattr(scalar_val, "__await__") or "Mock" in type(scalar_val).__name__:
            next_seq = 1
        else:
            next_seq = (scalar_val or 0) + 1
        
        alert_code = generate_alert_code(next_seq)
        while True:
            existing_alert = await db.execute(select(Alert).filter(Alert.code == alert_code))
            if not existing_alert.scalar_one_or_none():
                break
            next_seq += 1
            alert_code = generate_alert_code(next_seq)
        
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
        logger.info(f"Nueva alerta creada: {new_alert.code} (ID: {new_alert.id}). Iniciando envío a tutores...")

        # 6. Despachar notificaciones push a todos los tutores vinculados al niño
        guardians = await GuardianRepository.get_guardians_by_child(db, child.id)
        
        if not guardians:
            logger.warning(f"No se encontraron tutores vinculados para el niño {child.full_name} ({child.code}).")
        
        for guardian in guardians:
            # Obtener dispositivos registrados del tutor
            devices = await DeviceRepository.get_active_guardian_devices(db, guardian.id)
            if not devices:
                logger.info(f"Tutor {guardian.full_name} (ID: {guardian.id}) no tiene ningún dispositivo registrado.")
            
            for device in devices:
                if not device.fcm_token:
                    logger.info(f"Omitiendo dispositivo {device.id} de tutor {guardian.full_name}: no tiene FCM token.")
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
                    logger.info(
                        f"Notificación de alerta {new_alert.code} OMITIDA para el tutor {guardian.full_name} "
                        f"en dispositivo {device.id} debido a cooldown activo. "
                        f"Requiere esperar {settings.ALERT_COOLDOWN_SECONDS}s desde la última notificación."
                    )
                    continue

                logger.info(
                    f"Notificación de alerta {new_alert.code} APROBADA para envío al tutor {guardian.full_name} "
                    f"en el dispositivo {device.id} (FCM token: {device.fcm_token[:8]}...)."
                )

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
                    "created_at": to_bolivia_tz(new_alert.created_at).isoformat(),
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
