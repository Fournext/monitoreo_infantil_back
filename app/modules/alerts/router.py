from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.constants import UserRole, AlertStatus
from app.modules.auth.service import require_roles
from app.modules.auth.models import User
from app.modules.alerts.schemas import AlertResponse
from app.modules.alerts.service import AlertService

router = APIRouter(prefix="/api/alerts", tags=["Alertas de Seguridad"])

@router.patch("/{alert_code}/viewed", response_model=AlertResponse)
async def mark_alert_as_viewed(
    alert_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Marca una alerta como vista por el tutor o administrador. (Acceso: ADMIN, GUARDIAN vinculado)
    """
    is_admin = current_user.role == UserRole.ADMIN
    alert = await AlertService.update_status_by_code(
        db=db,
        code=alert_code,
        new_status=AlertStatus.VIEWED,
        guardian_id=current_user.guardian_id,
        is_admin=is_admin
    )
    await db.commit()
    return alert

@router.patch("/{alert_code}/resolved", response_model=AlertResponse)
async def resolve_alert(
    alert_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Resuelve y cierra una alerta de seguridad activa. (Acceso: ADMIN, GUARDIAN vinculado)
    """
    is_admin = current_user.role == UserRole.ADMIN
    alert = await AlertService.update_status_by_code(
        db=db,
        code=alert_code,
        new_status=AlertStatus.RESOLVED,
        guardian_id=current_user.guardian_id,
        is_admin=is_admin
    )
    await db.commit()
    return alert
