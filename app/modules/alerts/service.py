import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.constants import AlertStatus
from app.modules.alerts.models import Alert
from app.modules.alerts.repository import AlertRepository
from app.modules.guardians.repository import GuardianRepository
from app.modules.alerts.schemas import AlertResponse, AdminAlertResponse

class AlertService:
    @staticmethod
    async def get_alerts_admin(
        db: AsyncSession,
        child_code: str | None = None,
        daycare_code: str | None = None,
        daycare_id: uuid.UUID | None = None,
        status_filter: str | None = None
    ) -> list[AdminAlertResponse]:
        """Obtiene y serializa la lista de alertas filtradas para administradores y operadores."""
        alerts = await AlertRepository.get_alerts_admin(
            db=db,
            child_code=child_code,
            daycare_code=daycare_code,
            daycare_id=daycare_id,
            status_filter=status_filter
        )
        return [
            AdminAlertResponse(
                id=a.id,
                code=a.code,
                child_id=a.child_id,
                child_code=a.child.code,
                child_name=a.child.full_name,
                daycare_id=a.daycare_id,
                daycare_code=a.child.daycare.code,
                daycare_name=a.child.daycare.name,
                location_id=a.location_id,
                alert_type=a.alert_type,
                severity=a.severity,
                status=a.status,
                title=a.title,
                message=a.message,
                created_at=a.created_at,
                updated_at=a.updated_at,
                resolved_at=a.resolved_at
            )
            for a in alerts
        ]

    @staticmethod
    async def get_alerts_for_guardian(
        db: AsyncSession,
        guardian_id: uuid.UUID,
        child_code: str | None = None,
        daycare_code: str | None = None,
        status_filter: str | None = None
    ) -> list[AlertResponse]:
        """Obtiene y serializa la lista de alertas filtradas para el tutor."""
        alerts = await AlertRepository.get_alerts_for_guardian(
            db=db,
            guardian_id=guardian_id,
            child_code=child_code,
            daycare_code=daycare_code,
            status_filter=status_filter
        )
        return [AlertResponse.model_validate(a) for a in alerts]

    @staticmethod
    async def update_status_by_code(
        db: AsyncSession,
        code: str,
        new_status: AlertStatus,
        guardian_id: uuid.UUID | None,
        is_admin: bool
    ) -> AlertResponse:
        """
        Actualiza el estado de una alerta por su código de negocio.
        Seguridad: Valida que el tutor solicitante tenga vinculación activa con el niño de la alerta.
        """
        alert = await AlertRepository.get_by_code(db, code)
        if not alert:
            raise NotFoundException(f"Alerta con código '{code}' no encontrada.")

        # Validaciones de seguridad
        if not is_admin:
            if not guardian_id:
                raise ForbiddenException("Usuario no tiene perfil de tutor.")
            
            link = await GuardianRepository.get_child_link(db, guardian_id, alert.child_id)
            if not link:
                raise ForbiddenException("No tienes permisos para modificar el estado de esta alerta.")

        updated_alert = await AlertRepository.update_status(db, alert, new_status)
        return AlertResponse.model_validate(updated_alert)
