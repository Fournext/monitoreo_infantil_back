import logging
import os
import asyncio
import firebase_admin
from firebase_admin import credentials, messaging
from app.core.config import settings

logger = logging.getLogger("app.notifications")

class FirebaseNotificationService:
    _initialized = False

    @classmethod
    def initialize(cls):
        """Inicializa la app de Firebase si el archivo de credenciales existe."""
        if cls._initialized:
            return True
        
        # Verificar si Firebase ya fue inicializado (ej. por hot-reloads o en otra sección)
        try:
            firebase_admin.get_app()
            cls._initialized = True
            logger.info("Firebase Admin SDK ya estaba inicializado (App por defecto existente).")
            return True
        except ValueError:
            pass
        
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info(f"Firebase Admin SDK inicializado correctamente desde: {cred_path}")
                return True
            except Exception as e:
                logger.error(f"Error al inicializar Firebase Admin SDK: {e}. Se ejecutará en modo Simulador (Mock).")
                return False
        else:
            logger.warning(
                f"No se encontró el archivo de credenciales de Firebase en '{cred_path}'. "
                "Las notificaciones se registrarán localmente sin enviarse a FCM real."
            )
            return False

    @classmethod
    async def send_push_notification(cls, token: str, title: str, body: str, data: dict[str, str]) -> tuple[bool, str | None]:
        """
        Envía una notificación push FCM al token del dispositivo especificado.
        Retorna una tupla (status_boolean, error_message).
        """
        if not token:
            return False, "FCM token está vacío."

        # Intentar inicializar Firebase
        cls.initialize()

        if cls._initialized:
            try:
                # Convertir todo en data a strings para cumplir con los requerimientos de FCM
                stringified_data = {k: str(v) for k, v in data.items()}
                
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=stringified_data,
                    token=token
                )
                
                # Ejecutar llamada bloqueante de FCM en un thread pool asíncrono
                response = await asyncio.to_thread(messaging.send, message)
                logger.info(f"Notificación enviada con éxito. FCM Response ID: {response}")
                return True, None
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Fallo al enviar notificación por FCM: {error_msg}")
                return False, error_msg
        else:
            # Modo Simulación (Mock) para pruebas de desarrollo local sin credenciales reales
            logger.info("=== [NOTIFICACIÓN SIMULADA FCM] ===")
            logger.info(f"Para Token: {token}")
            logger.info(f"Título: {title}")
            logger.info(f"Mensaje: {body}")
            logger.info(f"Cuerpo de datos: {data}")
            logger.info("====================================")
            return True, None
