import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.children.models import Child
from app.modules.children.schemas import ChildCreate
from app.utils.code_generator import generate_child_code

class ChildRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, child_id: uuid.UUID) -> Child | None:
        """Busca un niño por su ID único primario."""
        result = await db.execute(select(Child).filter(Child.id == child_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_code(db: AsyncSession, code: str) -> Child | None:
        """Busca un niño por su código correlativo (e.g. NIN-8F42K)."""
        result = await db.execute(select(Child).filter(Child.code == code))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, child_in: ChildCreate) -> Child:
        """
        Registra un niño en una guardería.
        Genera automáticamente un código único en formato NIN-XXXXX.
        """
        # Asegurar unicidad del código autogenerado
        code = generate_child_code()
        while True:
            existing = await db.execute(select(Child).filter(Child.code == code))
            if not existing.scalar_one_or_none():
                break
            code = generate_child_code()

        db_child = Child(
            code=code,
            daycare_id=child_in.daycare_id,
            full_name=child_in.full_name,
            age=child_in.age,
            status=child_in.status
        )
        db.add(db_child)
        await db.flush()
        return db_child
