import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.constants import UserRole
from app.modules.auth.dependencies import (
    get_current_user, get_current_guardian, require_daycare_manager, require_admin
)
from app.modules.auth.models import User
from app.modules.guardians.models import Guardian
from app.modules.guardians.schemas import (
    GuardianCreateRequest, GuardianCreateResponse, GuardianResponse,
    GuardianResetPinResponse, GuardianChildLinkRequest, GuardianDaycareResponse,
    GuardianChildResponse, GuardianMonitoringSummaryResponse, GuardianChildrenListResponse,
    LinkDaycareRequest, LinkChildRequest, LinkedDaycareResponse
)
from app.modules.guardians.service import GuardianService
from app.modules.alerts.service import AlertService
from app.modules.alerts.schemas import AlertResponse

router = APIRouter(prefix="/api/guardians", tags=["Tutores / Guardianes"])

# Admin: Crear tutor
@router.post("", response_model=GuardianCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_guardian(
    guardian_in: GuardianCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_daycare_manager)
):
    """
    Crea un tutor. Retorna el código y el PIN temporal. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    guardian = await GuardianService.create_guardian(db, guardian_in)
    await db.commit()
    return guardian

# Admin: Vincular tutor con niño
@router.post("/{guardian_code}/link-child", status_code=status.HTTP_200_OK)
async def link_child_admin(
    guardian_code: str,
    link_in: GuardianChildLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_daycare_manager)
):
    """
    Vincula un tutor con un niño usando sus respectivos códigos. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    await GuardianService.link_child_by_guardian_code(
        db=db,
        guardian_code=guardian_code,
        daycare_code=link_in.daycare_code,
        child_code=link_in.child_code,
        relationship=link_in.relationship
    )
    await db.commit()
    return {"message": "Niño vinculado correctamente al tutor."}

# Admin: Resetear PIN de tutor
@router.patch("/{guardian_code}/reset-pin", response_model=GuardianResetPinResponse)
async def reset_pin_admin(
    guardian_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_daycare_manager)
):
    """
    Resetea el PIN de acceso del tutor y devuelve un PIN temporal. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    result = await GuardianService.reset_guardian_pin(db, guardian_code)
    await db.commit()
    return result

# --- ENDPOINTS /ME PARA EL TUTOR AUTENTICADO ---

# Tutor: Obtener perfil propio
@router.get("/me", response_model=GuardianResponse)
async def get_my_profile(
    current_guardian: Guardian = Depends(get_current_guardian)
):
    """
    Retorna el perfil del tutor autenticado. (Acceso: GUARDIAN propio)
    """
    return current_guardian

# Tutor: Obtener guarderías vinculadas
@router.get("/me/daycares", response_model=list[LinkedDaycareResponse])
async def list_my_daycares(
    db: AsyncSession = Depends(get_db),
    current_guardian: Guardian = Depends(get_current_guardian)
):
    """
    Retorna las guarderías asociadas al tutor autenticado. (Acceso: GUARDIAN propio)
    """
    return await GuardianService.list_linked_daycares(db, current_guardian.id)

# Tutor: Obtener niños vinculados
@router.get("/me/children", response_model=GuardianChildrenListResponse)
async def list_my_children(
    db: AsyncSession = Depends(get_db),
    current_guardian: Guardian = Depends(get_current_guardian)
):
    """
    Lista los niños vinculados al tutor autenticado con su última ubicación y estado. (Acceso: GUARDIAN propio)
    """
    children = await GuardianService.list_linked_children(db, current_guardian.id)
    formatted = []
    for c in children:
        monitoring_status = "NO_LOCATION"
        last_loc_at = None
        if c.last_location:
            last_loc_at = c.last_location.received_at
            if not c.last_location.is_inside_area:
                monitoring_status = "OUTSIDE_AREA"
            else:
                monitoring_status = "INSIDE_AREA"
                
        formatted.append(
            GuardianChildResponse(
                child_code=c.code,
                child_name=c.full_name,
                daycare_code=c.daycare_code,
                daycare_name=c.daycare_name,
                monitoring_status=monitoring_status,
                has_active_alert=c.has_active_alert,
                last_location_at=last_loc_at
            )
        )
    return GuardianChildrenListResponse(children=formatted)

# Tutor: Obtener alertas
@router.get("/me/alerts", response_model=list[AlertResponse])
async def list_my_alerts(
    child_code: str | None = None,
    daycare_code: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_guardian: Guardian = Depends(get_current_guardian)
):
    """
    Lista las alertas de los niños vinculados al tutor autenticado. (Acceso: GUARDIAN propio)
    """
    return await AlertService.get_alerts_for_guardian(
        db=db,
        guardian_id=current_guardian.id,
        child_code=child_code,
        daycare_code=daycare_code,
        status_filter=status
    )

# Tutor: Resumen de monitoreo
@router.get("/me/monitoring-summary", response_model=GuardianMonitoringSummaryResponse)
async def get_my_monitoring_summary(
    db: AsyncSession = Depends(get_db),
    current_guardian: Guardian = Depends(get_current_guardian)
):
    """
    Obtiene el estado unificado y resumen de alertas para el tutor autenticado. (Acceso: GUARDIAN propio)
    """
    summary = await GuardianService.get_monitoring_summary(db, current_guardian.id)
    daycares = await GuardianService.list_linked_daycares(db, current_guardian.id)
    total_daycares = len(daycares)
    
    return GuardianMonitoringSummaryResponse(
        total_children=summary.total_children,
        total_daycares=total_daycares,
        active_alerts=summary.active_alerts,
        children=summary.children
    )

# Tutor: Vincular niño desde Flutter
@router.post("/me/link-child", status_code=status.HTTP_200_OK)
async def link_child_mobile(
    link_in: LinkChildRequest,
    db: AsyncSession = Depends(get_db),
    current_guardian: Guardian = Depends(get_current_guardian)
):
    """
    Permite al tutor vincular un niño desde su aplicación móvil. (Acceso: GUARDIAN propio)
    """
    await GuardianService.link_child_by_code(
        db=db,
        guardian_id=current_guardian.id,
        daycare_code=link_in.daycare_code,
        child_code=link_in.child_code,
        relationship=link_in.relationship
    )
    await db.commit()
    return {"message": "Niño vinculado correctamente."}
