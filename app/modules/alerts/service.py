import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ForbiddenException, BadRequestException
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
        current_user: Any
    ) -> AlertResponse:
        """
        Actualiza el estado de una alerta por su código de negocio.
        Seguridad: Valida que el usuario tenga permisos suficientes según su rol y guardería.
        """
        alert = await AlertRepository.get_by_code(db, code)
        if not alert:
            raise NotFoundException(f"Alerta con código '{code}' no encontrada.")

        # Evitar transición de RESOLVED a VIEWED
        if alert.status == AlertStatus.RESOLVED and new_status == AlertStatus.VIEWED:
            raise BadRequestException("No se puede marcar como vista una alerta que ya ha sido resuelta.")

        # Validaciones de seguridad por rol
        from app.modules.guardians.models import Guardian
        from app.core.constants import UserRole

        is_guardian = isinstance(current_user, Guardian)

        if is_guardian:
            link = await GuardianRepository.get_child_link(db, current_user.id, alert.child_id)
            if not link:
                raise ForbiddenException("No tienes permisos para modificar el estado de esta alerta.")
        else:
            # Es personal interno (ADMIN, DAYCARE_MANAGER, OPERATOR, MONITOR)
            if current_user.role == UserRole.ADMIN:
                pass # El administrador tiene acceso global
            elif current_user.role in (UserRole.DAYCARE_MANAGER, UserRole.OPERATOR, UserRole.MONITOR):
                # Si el usuario tiene asignada una guardería específica, restringir a esa guardería
                if current_user.daycare_id and alert.daycare_id != current_user.daycare_id:
                    raise ForbiddenException("No tienes permisos para modificar alertas de otra guardería.")
            else:
                raise ForbiddenException("Rol de usuario no autorizado para modificar esta alerta.")

        updated_alert = await AlertRepository.update_status(db, alert, new_status)
        return AlertResponse.model_validate(updated_alert)
