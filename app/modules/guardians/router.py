import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.constants import UserRole
from app.core.exceptions import ForbiddenException
from app.modules.auth.service import require_roles, UserService
from app.modules.auth.models import User
from app.modules.guardians.schemas import (
    GuardianCreate, GuardianResponse, LinkDaycareRequest,
    LinkChildRequest, LinkedDaycareResponse, LinkedChildResponse,
    MonitoringSummaryResponse
)
from app.modules.guardians.service import GuardianService
from app.modules.alerts.service import AlertService
from app.modules.alerts.schemas import AlertResponse

router = APIRouter(prefix="/api/guardians", tags=["Tutores / Guardianes"])

def verify_guardian_access(guardian_id: uuid.UUID, current_user: User):
    """
    Verifica que el usuario solicitante sea ADMIN, o sea el tutor dueño de los recursos
    (guardian_id del usuario coincide con el guardian_id de la ruta).
    """
    if current_user.role != UserRole.ADMIN:
        if current_user.guardian_id != guardian_id:
            raise ForbiddenException("No tienes permisos para acceder o modificar los recursos de este tutor.")

@router.post("", response_model=GuardianResponse, status_code=status.HTTP_201_CREATED)
async def create_guardian(
    guardian_in: GuardianCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Crea un tutor. (Acceso: ADMIN)
    """
    guardian = await GuardianService.create_guardian(db, guardian_in)
    await db.commit()
    return guardian

@router.post("/{guardian_id}/link-daycare", status_code=status.HTTP_200_OK)
async def link_daycare(
    guardian_id: uuid.UUID,
    link_in: LinkDaycareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Vincula al tutor con una guardería utilizando el código. (Acceso: ADMIN, GUARDIAN propio)
    """
    verify_guardian_access(guardian_id, current_user)
    await GuardianService.link_daycare_by_code(db, guardian_id, link_in.daycare_code)
    await db.commit()
    return {"message": f"Guardería vinculada correctamente al tutor {guardian_id}."}

@router.post("/{guardian_id}/link-child", status_code=status.HTTP_200_OK)
async def link_child(
    guardian_id: uuid.UUID,
    link_in: LinkChildRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Vincula a un niño con un tutor en base al código de la guardería y del niño. (Acceso: ADMIN, GUARDIAN propio)
    El tutor debe estar previamente vinculado a la guardería.
    """
    verify_guardian_access(guardian_id, current_user)
    await GuardianService.link_child_by_code(
        db=db,
        guardian_id=guardian_id,
        daycare_code=link_in.daycare_code,
        child_code=link_in.child_code,
        relationship=link_in.relationship
    )
    await db.commit()
    return {"message": f"Niño {link_in.child_code} vinculado correctamente al tutor."}

@router.get("/{guardian_id}/daycares", response_model=list[LinkedDaycareResponse])
async def list_linked_daycares(
    guardian_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Retorna la lista de todas las guarderías vinculadas al tutor. (Acceso: ADMIN, GUARDIAN propio)
    """
    verify_guardian_access(guardian_id, current_user)
    return await GuardianService.list_linked_daycares(db, guardian_id)

@router.get("/{guardian_id}/children", response_model=list[LinkedChildResponse])
async def list_linked_children(
    guardian_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Lista todos los niños vinculados al tutor, indicando su última ubicación y estado. (Acceso: ADMIN, GUARDIAN propio)
    """
    verify_guardian_access(guardian_id, current_user)
    return await GuardianService.list_linked_children(db, guardian_id)

@router.get("/{guardian_id}/alerts", response_model=list[AlertResponse])
async def list_guardian_alerts(
    guardian_id: uuid.UUID,
    child_code: str | None = None,
    daycare_code: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Lista las alertas de seguridad de los niños que están vinculados al tutor. (Acceso: ADMIN, GUARDIAN propio)
    Filtros opcionales: child_code, daycare_code, status.
    """
    verify_guardian_access(guardian_id, current_user)
    return await AlertService.get_alerts_for_guardian(
        db=db,
        guardian_id=guardian_id,
        child_code=child_code,
        daycare_code=daycare_code,
        status_filter=status
    )

@router.get("/{guardian_id}/monitoring-summary", response_model=MonitoringSummaryResponse)
async def get_monitoring_summary(
    guardian_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.GUARDIAN))
):
    """
    Obtiene el estado unificado y resumen de alertas para todos los niños del tutor. (Acceso: ADMIN, GUARDIAN propio)
    """
    verify_guardian_access(guardian_id, current_user)
    return await GuardianService.get_monitoring_summary(db, guardian_id)
