from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement
from app.shared.geo.geojson_utils import validate_polygon_geojson, geojson_to_polygon_wkt

class SpatialService:
    @staticmethod
    def create_point(longitude: float, latitude: float) -> WKTElement:
        """
        Crea un objeto WKTElement que representa un Point en el SRID 4326.
        """
        return WKTElement(f"SRID=4326;POINT({longitude} {latitude})", srid=4326)

    @staticmethod
    async def is_point_inside_daycare_area(db: AsyncSession, daycare_area: Any, point: Any) -> bool:
        """
        Verifica mediante PostGIS si el punto se encuentra dentro del área de la guardería (ST_Covers).
        """
        if daycare_area is None or point is None:
            return False
        
        query = select(func.ST_Covers(daycare_area, point))
        result = await db.execute(query)
        return bool(result.scalar())

    @staticmethod
    async def is_point_near_area(db: AsyncSession, daycare_area: Any, point: Any, tolerance_meters: float) -> bool:
        """
        Verifica mediante PostGIS si el punto está dentro del margen de tolerancia en metros (ST_DWithin),
        casteando las geometrías a geografía para un cálculo métrico preciso sobre la elipsoide.
        """
        if daycare_area is None or point is None:
            return False
            
        # Si daycare_area es un objeto espacial (como WKBElement cargado de la BD),
        # lo convertimos a WKT string para evitar fallos de parseo en ST_GeogFromText
        if isinstance(daycare_area, (WKBElement, WKTElement)):
            daycare_area = to_shape(daycare_area).wkt
            
        # Casteo de geometry a geography para ST_DWithin
        query = select(func.ST_DWithin(
            func.cast(daycare_area, Geography),
            func.cast(point, Geography),
            tolerance_meters
        ))
        result = await db.execute(query)
        return bool(result.scalar())

    @classmethod
    async def check_if_inside_with_tolerance(
        cls, db: AsyncSession, daycare_area: Any, point: Any, tolerance_meters: float
    ) -> bool:
        """
        Verifica si el niño está a salvo:
        - Si está estrictamente dentro del polígono (ST_Covers).
        - Si está a una distancia menor o igual al margen de tolerancia de GPS (ST_DWithin).
        """
        # 1. Comprobar si está estrictamente dentro
        is_inside = await cls.is_point_inside_daycare_area(db, daycare_area, point)
        if is_inside:
            return True
            
        # 2. Si no, comprobar tolerancia por imprecisión del GPS
        if tolerance_meters > 0:
            is_near = await cls.is_point_near_area(db, daycare_area, point, tolerance_meters)
            return is_near
            
        return False

    @staticmethod
    def validate_polygon_geojson(geojson: dict[str, Any]) -> dict[str, Any]:
        """Expone la utilidad de validación de polígonos GeoJSON."""
        return validate_polygon_geojson(geojson)

    @staticmethod
    def geojson_to_polygon_wkt(geojson: dict[str, Any]) -> str:
        """Expone la utilidad para convertir polígono GeoJSON a WKT."""
        return geojson_to_polygon_wkt(geojson)
