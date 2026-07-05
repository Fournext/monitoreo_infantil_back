from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.constants import UserRole
from app.modules.auth.service import require_roles
from app.modules.children.schemas import ChildCreate, ChildResponse
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
