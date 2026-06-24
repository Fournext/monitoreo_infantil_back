import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.alerts.models import AlertNotificationLog
from app.core.constants import NotificationLogStatus
from app.modules.notifications.firebase_service import FirebaseNotificationService

class NotificationService:
    @staticmethod
    async def log_and_send_notification(
        db: AsyncSession,
        alert_id: uuid.UUID,
        guardian_id: uuid.UUID,
        device_id: uuid.UUID | None,
        fcm_token: str,
        title: str,
        body: str,
        data: dict[str, str]
    ) -> AlertNotificationLog:
        """
        Envía una notificación de alerta vía FCM y registra el resultado en alert_notification_logs.
        """
        # Intentar enviar la notificación
        success, error_msg = await FirebaseNotificationService.send_push_notification(
            token=fcm_token,
            title=title,
            body=body,
            data=data
        )

        status = NotificationLogStatus.SENT if success else NotificationLogStatus.FAILED

        # Guardar registro en la base de datos
        log = AlertNotificationLog(
            alert_id=alert_id,
            guardian_id=guardian_id,
            device_id=device_id,
            fcm_token=fcm_token,
            status=status,
            error_message=error_msg
        )

        db.add(log)
        await db.flush() # Guardar temporalmente en la base de datos dentro del contexto de la sesión actual
        return log
