import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.modules.locations.models import ChildLocation, CurrentChildLocation
from app.shared.geo.spatial_service import SpatialService
from app.utils.date_utils import get_now

class LocationRepository:
    @staticmethod
    async def create_location(
        db: AsyncSession,
        child_id: uuid.UUID,
        daycare_id: uuid.UUID,
        latitude: float,
        longitude: float,
        accuracy: float | None,
        speed: float | None,
        heading: float | None,
        is_inside_area: bool,
        received_at: datetime
    ) -> ChildLocation:
        """
        Inserta un nuevo registro en el historial de ubicaciones del niño.
        Utiliza SpatialService para crear la geometría Point.
        """
        point_geom = SpatialService.create_point(longitude, latitude)

        db_location = ChildLocation(
            child_id=child_id,
            daycare_id=daycare_id,
            point=point_geom,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed,
            heading=heading,
            is_inside_area=is_inside_area,
            received_at=received_at
        )
        db.add(db_location)
        await db.flush()
        return db_location

    @staticmethod
    async def update_current_location(
        db: AsyncSession,
        child_id: uuid.UUID,
        daycare_id: uuid.UUID,
        latitude: float,
        longitude: float,
        accuracy: float | None,
        is_inside_area: bool,
        received_at: datetime
    ) -> CurrentChildLocation:
        """
        Actualiza o inserta la ubicación actual del niño para consultas rápidas sin barrer el historial.
        """
        point_geom = SpatialService.create_point(longitude, latitude)

        # Buscar si ya existe la ubicación actual registrada para el niño
        query = select(CurrentChildLocation).filter(CurrentChildLocation.child_id == child_id)
        result = await db.execute(query)
        current = result.scalar_one_or_none()

        if current:
            current.daycare_id = daycare_id
            current.point = point_geom
            current.latitude = latitude
            current.longitude = longitude
            current.accuracy = accuracy
            current.is_inside_area = is_inside_area
            current.received_at = received_at
        else:
            current = CurrentChildLocation(
                child_id=child_id,
                daycare_id=daycare_id,
                point=point_geom,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                is_inside_area=is_inside_area,
                received_at=received_at
            )
            db.add(current)

        await db.flush()
        return current

    @staticmethod
    async def get_last_location(db: AsyncSession, child_id: uuid.UUID) -> CurrentChildLocation | None:
        """Obtiene la última ubicación conocida del niño."""
        query = select(CurrentChildLocation).filter(CurrentChildLocation.child_id == child_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recent_locations(db: AsyncSession, child_id: uuid.UUID, limit: int = 20) -> list[ChildLocation]:
        """Obtiene el historial reciente de ubicaciones del niño ordenado descendentemente."""
        query = (
            select(ChildLocation)
            .filter(ChildLocation.child_id == child_id)
            .order_by(ChildLocation.received_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def clean_old_locations(db: AsyncSession, days: int) -> int:
        """
        Elimina las ubicaciones del historial que superen los N días de antigüedad.
        Retorna la cantidad de registros eliminados.
        """
        cutoff = get_now() - timedelta(days=days)
        stmt = delete(ChildLocation).where(ChildLocation.created_at < cutoff)
        result = await db.execute(stmt)
        return result.rowcount
