from typing import Any
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.daycares.schemas import DaycareCreate, DaycareResponse
from app.modules.daycares.service import DaycareService
from app.modules.auth.service import require_roles
from app.core.constants import UserRole

from app.shared.geo.schemas import GeoJSONPolygon

router = APIRouter(prefix="/api/daycares", tags=["Guarderías"])

# Protegemos estos endpoints para que solo el rol ADMIN pueda crear/modificar
@router.post("", response_model=DaycareResponse, status_code=status.HTTP_201_CREATED)
async def create_daycare(
    daycare_in: DaycareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN))
):
    """
    Crea una guardería. (Acceso: ADMIN)
    El código identificador de negocio se autogenerará incrementalmente (e.g. GUA-SCZ-001).
    """
    daycare = await DaycareService.create_daycare(db, daycare_in)
    await db.commit()
    return daycare

@router.put("/{daycare_code}/area", response_model=DaycareResponse)
async def update_daycare_area(
    daycare_code: str,
    geojson_area: GeoJSONPolygon,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN))
):
    """
    Establece o actualiza el polígono geográfico de cobertura para la guardería. (Acceso: ADMIN)
    Espera un GeoJSON de tipo Polygon válido.
    """
    daycare = await DaycareService.update_daycare_area(db, daycare_code, geojson_area.model_dump())
    await db.commit()
    return daycare


@router.get("", response_model=list[DaycareResponse])
async def list_daycares(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN, "GUARDIAN"))
):
    """
    Lista todas las guarderías del sistema. (Acceso: ADMIN, GUARDIAN)
    """
    return await DaycareService.list_daycares(db)

@router.get("/{daycare_code}", response_model=DaycareResponse)
async def get_daycare(
    daycare_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_roles(UserRole.ADMIN, "GUARDIAN"))
):
    """
    Retorna el detalle completo de una guardería según su código correlativo. (Acceso: ADMIN, GUARDIAN)
    Incluye si el polígono perimetral ha sido establecido.
    """
    return await DaycareService.get_daycare_by_code(db, daycare_code)
