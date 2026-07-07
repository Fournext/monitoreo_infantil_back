import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.children.models import Child
from app.modules.children.schemas import ChildCreate, ChildUpdate
from app.shared.utils.code_generator import generate_child_code

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
        await db.refresh(db_child)
        return db_child

    @staticmethod
    async def get_all(db: AsyncSession, daycare_id: uuid.UUID | None = None) -> list[Child]:
        """Obtiene la lista de todos los niños, con filtro opcional por guardería."""
        stmt = select(Child)
        if daycare_id:
            stmt = stmt.filter(Child.daycare_id == daycare_id)
        stmt = stmt.order_by(Child.full_name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, child: Child, child_in: ChildUpdate) -> Child:
        """Actualiza la ficha de un niño."""
        update_data = child_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(child, key, value)
        db.add(child)
        await db.flush()
        await db.refresh(child)
        return child
