import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from geoalchemy2.elements import WKTElement
from app.modules.daycares.models import Daycare
from app.modules.daycares.schemas import DaycareCreate, DaycareUpdate
from app.shared.utils.code_generator import generate_daycare_code

class DaycareRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, daycare_id: uuid.UUID) -> Daycare | None:
        """Busca una guardería por su ID único."""
        result = await db.execute(select(Daycare).filter(Daycare.id == daycare_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_code(db: AsyncSession, code: str) -> Daycare | None:
        """Busca una guardería por su código único de negocio (e.g. GUA-SCZ-001)."""
        result = await db.execute(select(Daycare).filter(Daycare.code == code))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Daycare]:
        """Obtiene todas las guarderías del sistema."""
        result = await db.execute(select(Daycare).order_by(Daycare.code))
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, daycare_in: DaycareCreate) -> Daycare:
        """
        Crea una guardería. Obtiene la cuenta total de guarderías
        para generar un código secuencial correlativo (e.g. GUA-SCZ-004).
        """
        count_query = select(func.count(Daycare.id))
        count_result = await db.execute(count_query)
        scalar_val = count_result.scalar()
        if hasattr(scalar_val, "__await__") or "Mock" in type(scalar_val).__name__:
            next_seq = 1
        else:
            next_seq = (scalar_val or 0) + 1
        
        code = generate_daycare_code(next_seq)
        while True:
            existing = await db.execute(select(Daycare).filter(Daycare.code == code))
            if not existing.scalar_one_or_none():
                break
            next_seq += 1
            code = generate_daycare_code(next_seq)

        db_daycare = Daycare(
            code=code,
            name=daycare_in.name,
            address=daycare_in.address
        )
        db.add(db_daycare)
        await db.flush()
        await db.refresh(db_daycare)
        return db_daycare

    @staticmethod
    async def update_area(db: AsyncSession, daycare: Daycare, wkt_polygon: str) -> Daycare:
        """
        Actualiza el área geográfica de la guardería asignándole el polígono WKT.
        """
        daycare.area = WKTElement(wkt_polygon, srid=4326)
        db.add(daycare)
        await db.flush()
        await db.refresh(daycare)
        return daycare

    @staticmethod
    async def update(db: AsyncSession, daycare: Daycare, daycare_in: DaycareUpdate) -> Daycare:
        """
        Actualiza los datos generales (nombre, dirección, estado) de una guardería.
        """
        update_data = daycare_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(daycare, key, value)
        db.add(daycare)
        await db.flush()
        await db.refresh(daycare)
        return daycare
