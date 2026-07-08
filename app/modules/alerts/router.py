from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.constants import UserRole, AlertStatus
from app.modules.auth.service import require_roles
from app.modules.auth.models import User
from app.modules.alerts.schemas import AlertResponse, AdminAlertResponse
from app.modules.alerts.service import AlertService

router = APIRouter(prefix="/api/alerts", tags=["Alertas de Seguridad"])

@router.get("", response_model=list[AdminAlertResponse])
async def list_alerts(
    child_code: str | None = None,
    daycare_code: str | None = None,
    daycare_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN, UserRole.DAYCARE_MANAGER, UserRole.OPERATOR, UserRole.MONITOR))
):
    """
    Lista todas las alertas de seguridad del sistema con filtros opcionales.
    (Acceso: ADMIN, DAYCARE_MANAGER, OPERATOR, MONITOR)
    """
    import uuid
    daycare_uuid = None
    if daycare_id:
        try:
            daycare_uuid = uuid.UUID(daycare_id)
        except ValueError:
            pass # ignore invalid uuid
            
    # Si el usuario es un DAYCARE_MANAGER, restringir su consulta solo a su guardería
    if current_user.role == UserRole.DAYCARE_MANAGER:
        daycare_uuid = current_user.daycare_id

    return await AlertService.get_alerts_admin(
        db=db,
        child_code=child_code,
        daycare_code=daycare_code,
        daycare_id=daycare_uuid,
        status_filter=status
    )


@router.patch("/{alert_code}/viewed", response_model=AlertResponse)
async def mark_alert_as_viewed(
    alert_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(
        UserRole.ADMIN,
        UserRole.DAYCARE_MANAGER,
        UserRole.OPERATOR,
        UserRole.MONITOR,
        "GUARDIAN"
    ))
):
    """
    Marca una alerta como vista.
    (Acceso: ADMIN, DAYCARE_MANAGER, OPERATOR, MONITOR, GUARDIAN vinculado)
    """
    alert = await AlertService.update_status_by_code(
        db=db,
        code=alert_code,
        new_status=AlertStatus.VIEWED,
        # pyrefly: ignore [unexpected-keyword]
        current_user=current_user
    )
    await db.commit()
    return alert

@router.patch("/{alert_code}/resolved", response_model=AlertResponse)
async def resolve_alert(
    alert_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(
        UserRole.ADMIN,
        UserRole.DAYCARE_MANAGER,
        UserRole.OPERATOR,
        UserRole.MONITOR,
        "GUARDIAN"
    ))
):
    """
    Resuelve y cierra una alerta de seguridad activa.
    (Acceso: ADMIN, DAYCARE_MANAGER, OPERATOR, MONITOR, GUARDIAN vinculado)
    """
    alert = await AlertService.update_status_by_code(
        db=db,
        code=alert_code,
        new_status=AlertStatus.RESOLVED,
        # pyrefly: ignore [unexpected-keyword]
        current_user=current_user
    )
    await db.commit()
    return alert
