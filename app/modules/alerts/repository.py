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
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Alert)
            .options(selectinload(Alert.child).selectinload(Child.daycare))
            .filter(Alert.id == alert_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_code(db: AsyncSession, code: str) -> Alert | None:
        """Busca una alerta por su código de negocio (e.g. ALT-98214) o por su ID único (UUID)."""
        from sqlalchemy.orm import selectinload
        # Intentar buscar por UUID si el formato coincide
        try:
            alert_uuid = uuid.UUID(code)
            result = await db.execute(
                select(Alert)
                .options(selectinload(Alert.child).selectinload(Child.daycare))
                .filter(Alert.id == alert_uuid)
            )
            alert = result.scalar_one_or_none()
            if alert:
                return alert
        except ValueError:
            pass

        # Buscar por código de negocio como fallback
        result = await db.execute(
            select(Alert)
            .options(selectinload(Alert.child).selectinload(Child.daycare))
            .filter(Alert.code == code)
        )
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
        Retorna la alerta más reciente si existen múltiples para evitar lanzar
        excepciones de tipo MultipleResultsFound.
        """
        query = (
            select(Alert)
            .filter(
                and_(
                    Alert.child_id == child_id,
                    Alert.alert_type == alert_type,
                    Alert.status.in_([AlertStatus.NEW, AlertStatus.VIEWED])
                )
            )
            .order_by(Alert.created_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalars().first()

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
        from sqlalchemy.orm import selectinload
        # Consulta base uniendo con GuardianChild para garantizar seguridad de acceso
        query = (
            select(Alert)
            .join(Child, Child.id == Alert.child_id)
            .join(GuardianChild, GuardianChild.child_id == Child.id)
            .filter(GuardianChild.guardian_id == guardian_id)
            .options(selectinload(Alert.child).selectinload(Child.daycare))
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
            from app.utils.date_utils import get_now
            alert.resolved_at = get_now()
        db.add(alert)
        await db.flush()
        await db.refresh(alert)
        return alert

    @staticmethod
    async def get_alerts_admin(
        db: AsyncSession,
        child_code: str | None = None,
        daycare_code: str | None = None,
        daycare_id: uuid.UUID | None = None,
        status_filter: str | None = None
    ) -> list[Alert]:
        """
        Retorna la lista de alertas para administradores y operadores con filtros opcionales.
        Realiza eager loading de child y child.daycare para optimizar accesos.
        """
        from sqlalchemy.orm import joinedload
        
        query = (
            select(Alert)
            .join(Child, Child.id == Alert.child_id)
            .options(
                joinedload(Alert.child).joinedload(Child.daycare)
            )
        )

        if child_code:
            query = query.filter(Child.code == child_code)

        if daycare_id:
            query = query.filter(Alert.daycare_id == daycare_id)

        if daycare_code:
            query = query.join(Daycare, Daycare.id == Alert.daycare_id).filter(Daycare.code == daycare_code)

        if status_filter:
            query = query.filter(Alert.status == status_filter)

        query = query.order_by(Alert.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

