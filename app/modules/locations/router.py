from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.constants import UserRole
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.auth.service import require_roles
from app.modules.auth.models import User
from app.modules.children.repository import ChildRepository
from app.modules.guardians.repository import GuardianRepository
from app.modules.locations.repository import LocationRepository
from app.modules.locations.schemas import LocationResponse

router = APIRouter(prefix="/api/children", tags=["Ubicaciones de Niños"])

async def verify_guardian_child_access(db: AsyncSession, child_code: str, current_user: Any):
    """
    Valida que el usuario tenga acceso al niño:
    - Si es ADMIN, tiene acceso total.
    - Si es GUARDIAN, debe tener una vinculación activa en guardian_children con el niño.
    """
    from app.modules.guardians.models import Guardian
    child = await ChildRepository.get_by_code(db, child_code)
    if not child:
        raise NotFoundException(f"Niño con código '{child_code}' no encontrado.")
        
    is_admin = getattr(current_user, "role", None) == UserRole.ADMIN
    if not is_admin:
        if isinstance(current_user, Guardian):
            guardian_id = current_user.id
        else:
            raise ForbiddenException("No tienes permisos suficientes.")
            
        link = await GuardianRepository.get_child_link(db, guardian_id, child.id)
        if not link:
            raise ForbiddenException("No tienes permisos para ver información de ubicación de este niño.")
            
    return child

@router.get("/{child_code}/last-location", response_model=LocationResponse)
async def get_last_location(
    child_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, "GUARDIAN"))
):
    """
    Retorna la última ubicación física conocida del niño. (Acceso: ADMIN o GUARDIAN vinculado)
    """
    child = await verify_guardian_child_access(db, child_code, current_user)
    last_loc = await LocationRepository.get_last_location(db, child.id)
    if not last_loc:
        raise NotFoundException(f"No se registran ubicaciones para el niño '{child_code}'.")
        
    return last_loc

@router.get("/{child_code}/locations/recent", response_model=list[LocationResponse])
async def get_recent_locations(
    child_code: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, "GUARDIAN"))
):
    """
    Retorna el historial de ubicaciones recientes del niño. (Acceso: ADMIN o GUARDIAN vinculado)
    Limita la cantidad de registros retornados (máximo 100).
    """
    child = await verify_guardian_child_access(db, child_code, current_user)
    return await LocationRepository.get_recent_locations(db, child.id, limit)
