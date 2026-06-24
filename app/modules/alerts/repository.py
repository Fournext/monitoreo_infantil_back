import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.modules.alerts.models import Alert
from app.modules.children.models import Child
from app.modules.guardians.models import GuardianChild
from app.modules.daycares.models import Daycare
from app.core.constants import AlertStatus, AlertType

class AlertRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, alert_id: uuid.UUID) -> Alert | None:
        """Busca una alerta por su ID único primario."""
        result = await db.execute(select(Alert).filter(Alert.id == alert_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_code(db: AsyncSession, code: str) -> Alert | None:
        """Busca una alerta por su código de negocio (e.g. ALT-98214)."""
        result = await db.execute(select(Alert).filter(Alert.code == code))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_alert_by_child_and_type(
        db: AsyncSession,
        child_id: uuid.UUID,
        alert_type: AlertType
    ) -> Alert | None:
        """
        Verifica si ya existe una alerta activa (estado NEW o VIEWED) de un tipo específico
        asociada a un niño para evitar duplicados.
        """
        query = select(Alert).filter(
            and_(
                Alert.child_id == child_id,
                Alert.alert_type == alert_type,
                Alert.status.in_([AlertStatus.NEW, AlertStatus.VIEWED])
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_alerts_for_guardian(
        db: AsyncSession,
        guardian_id: uuid.UUID,
        child_code: str | None = None,
        daycare_code: str | None = None,
        status_filter: str | None = None
    ) -> list[Alert]:
        """
        Retorna la lista de alertas asociadas a los niños vinculados a un tutor determinado,
        aplicando filtros opcionales (child_code, daycare_code, status).
        """
        # Consulta base uniendo con GuardianChild para garantizar seguridad de acceso
        query = (
            select(Alert)
            .join(Child, Child.id == Alert.child_id)
            .join(GuardianChild, GuardianChild.child_id == Child.id)
            .filter(GuardianChild.guardian_id == guardian_id)
        )

        if child_code:
            query = query.filter(Child.code == child_code)
            
        if daycare_code:
            query = query.join(Daycare, Daycare.id == Alert.daycare_id).filter(Daycare.code == daycare_code)
            
        if status_filter:
            query = query.filter(Alert.status == status_filter)

        query = query.order_by(Alert.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_status(db: AsyncSession, alert: Alert, new_status: AlertStatus) -> Alert:
        """
        Actualiza el estado de una alerta y setea resolved_at si el estado es RESOLVED.
        """
        alert.status = new_status
        if new_status == AlertStatus.RESOLVED:
            alert.resolved_at = datetime.now(timezone.utc)
        db.add(alert)
        await db.flush()
        return alert
