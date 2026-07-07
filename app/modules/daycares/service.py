from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from app.core.exceptions import NotFoundException
from app.modules.daycares.models import Daycare
from app.modules.daycares.repository import DaycareRepository
from app.modules.daycares.schemas import DaycareCreate, DaycareResponse, DaycareUpdate
from app.shared.geo.spatial_service import SpatialService

class DaycareService:
    @staticmethod
    def _map_to_response(daycare: Daycare) -> DaycareResponse:
        """Convierte una entidad de base de datos Daycare a su esquema DaycareResponse."""
        area_geojson = None
        if daycare.area is not None:
            try:
                # Conversión de WKBElement a diccionario GeoJSON con Shapely
                geom_shape = to_shape(daycare.area)
                area_geojson = mapping(geom_shape)
            except Exception:
                pass
                
        return DaycareResponse(
            id=daycare.id,
            code=daycare.code,
            name=daycare.name,
            address=daycare.address,
            status=daycare.status,
            has_area=daycare.area is not None,
            area=area_geojson,
            created_at=daycare.created_at,
            updated_at=daycare.updated_at
        )

    @classmethod
    async def create_daycare(cls, db: AsyncSession, daycare_in: DaycareCreate) -> DaycareResponse:
        """Crea una guardería y retorna su representación final."""
        daycare = await DaycareRepository.create(db, daycare_in)
        return cls._map_to_response(daycare)

    @classmethod
    async def get_daycare_by_code(cls, db: AsyncSession, code: str) -> DaycareResponse:
        """Busca una guardería por código de negocio. Lanza error 404 si no existe."""
        daycare = await DaycareRepository.get_by_code(db, code)
        if not daycare:
            raise NotFoundException(f"Guardería con código '{code}' no encontrada.")
        return cls._map_to_response(daycare)

    @classmethod
    async def list_daycares(cls, db: AsyncSession) -> list[DaycareResponse]:
        """Retorna una lista de todas las guarderías registradas."""
        daycares = await DaycareRepository.get_all(db)
        return [cls._map_to_response(d) for d in daycares]

    @classmethod
    async def update_daycare_area(cls, db: AsyncSession, code: str, geojson: dict[str, Any]) -> DaycareResponse:
        """
        Valida que el GeoJSON sea un Polygon válido y cerrado, lo convierte a WKT
        y actualiza el área física de la guardería en la base de datos.
        """
        daycare = await DaycareRepository.get_by_code(db, code)
        if not daycare:
            raise NotFoundException(f"Guardería con código '{code}' no encontrada.")

        # Validar y convertir a WKT
        SpatialService.validate_polygon_geojson(geojson)
        wkt_polygon = SpatialService.geojson_to_polygon_wkt(geojson)

        # Actualizar área
        updated_daycare = await DaycareRepository.update_area(db, daycare, wkt_polygon)
        return cls._map_to_response(updated_daycare)
#esto aumente
    @classmethod
    async def update_daycare(cls, db: AsyncSession, code: str, daycare_in: DaycareUpdate) -> DaycareResponse:
        """
        Actualiza los datos básicos de una guardería por su código único de negocio.
        """
        daycare = await DaycareRepository.get_by_code(db, code)
        if not daycare:
            raise NotFoundException(f"Guardería con código '{code}' no encontrada.")

        updated_daycare = await DaycareRepository.update(db, daycare, daycare_in)
        return cls._map_to_response(updated_daycare)
