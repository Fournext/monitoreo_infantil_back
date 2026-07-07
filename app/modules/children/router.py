from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.constants import UserRole
from app.modules.auth.service import require_roles
from app.modules.children.schemas import ChildCreate, ChildResponse, ChildUpdate
from app.modules.children.service import ChildService

router = APIRouter(prefix="/api/children", tags=["Niños"])

@router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
async def create_child(
    child_in: ChildCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN))
):
    """
    Registra un niño en una guardería y genera su código identificador. (Acceso: ADMIN)
    """
    child = await ChildService.create_child(db, child_in)
    await db.commit()
    return child

@router.get("/{child_code}", response_model=ChildResponse)
async def get_child(
    child_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN, "GUARDIAN"))
):
    """
    Retorna el detalle básico del niño según su código (e.g. NIN-8F42K). (Acceso: ADMIN, GUARDIAN)
    """
    return await ChildService.get_child_by_code(db, child_code)

@router.get("", response_model=list[ChildResponse])
async def list_children(
    daycare_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN, UserRole.DAYCARE_MANAGER, UserRole.OPERATOR, UserRole.MONITOR))
):
    """
    Retorna la lista de todos los niños del sistema, con opción de filtrar por el ID de la guardería. (Acceso: ADMIN, DAYCARE_MANAGER, OPERATOR, MONITOR)
    """
    import uuid
    daycare_uuid = None
    if daycare_id:
        try:
            daycare_uuid = uuid.UUID(daycare_id)
        except ValueError:
            pass # ignore invalid uuid and return all
            
    return await ChildService.list_children(db, daycare_uuid)

@router.put("/{child_code}", response_model=ChildResponse)
async def update_child(
    child_code: str,
    child_in: ChildUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN, UserRole.DAYCARE_MANAGER))
):
    """
    Actualiza la ficha de un niño (nombre, edad, guardería, estado) según su código correlativo. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    child = await ChildService.update_child(db, child_code, child_in)
    await db.commit()
    return child
