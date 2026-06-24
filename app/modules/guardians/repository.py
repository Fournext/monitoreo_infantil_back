import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from app.modules.guardians.models import Guardian, GuardianChild, GuardianDaycare
from app.modules.daycares.models import Daycare
from app.modules.children.models import Child
from app.modules.guardians.schemas import GuardianCreate

from app.shared.utils.code_generator import generate_guardian_code
from app.core.security import get_pin_hash
from app.core.constants import GuardianStatus
import random
import string

class GuardianRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, guardian_id: uuid.UUID) -> Guardian | None:
        """Obtiene un tutor por su ID primario."""
        result = await db.execute(select(Guardian).filter(Guardian.id == guardian_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_code(db: AsyncSession, code: str) -> Guardian | None:
        """Busca un tutor por su código de negocio (e.g. TUT-7A91P)."""
        result = await db.execute(select(Guardian).filter(Guardian.code == code))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, guardian_in: GuardianCreate) -> Guardian:
        """Crea una nueva entidad de tutor con código y PIN temporal."""
        code = generate_guardian_code()
        while True:
            existing = await db.execute(select(Guardian).filter(Guardian.code == code))
            if not existing.scalar_one_or_none():
                break
            code = generate_guardian_code()
            
        temporary_pin = "".join(random.choices(string.digits, k=4))
        
        db_guardian = Guardian(
            code=code,
            full_name=guardian_in.full_name,
            phone=guardian_in.phone,
            email=guardian_in.email,
            pin_hash=get_pin_hash(temporary_pin),
            must_change_pin=True,
            status=GuardianStatus.ACTIVE
        )
        db.add(db_guardian)
        await db.flush()
        # Adjuntar temporalmente para la capa superior
        db_guardian.temporary_pin = temporary_pin
        return db_guardian

    @staticmethod
    async def get_daycare_link(db: AsyncSession, guardian_id: uuid.UUID, daycare_id: uuid.UUID) -> GuardianDaycare | None:
        """Verifica si ya existe un enlace entre un tutor y una guardería."""
        query = select(GuardianDaycare).filter(
            and_(GuardianDaycare.guardian_id == guardian_id, GuardianDaycare.daycare_id == daycare_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def link_daycare(db: AsyncSession, guardian_id: uuid.UUID, daycare_id: uuid.UUID) -> GuardianDaycare:
        """Registra la vinculación de un tutor con una guardería."""
        link = GuardianDaycare(guardian_id=guardian_id, daycare_id=daycare_id)
        db.add(link)
        await db.flush()
        return link

    @staticmethod
    async def get_child_link(db: AsyncSession, guardian_id: uuid.UUID, child_id: uuid.UUID) -> GuardianChild | None:
        """Verifica si ya existe un enlace entre un tutor y un niño."""
        query = select(GuardianChild).filter(
            and_(GuardianChild.guardian_id == guardian_id, GuardianChild.child_id == child_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def link_child(db: AsyncSession, guardian_id: uuid.UUID, child_id: uuid.UUID, relationship: str) -> GuardianChild:
        """Vincula un niño con un tutor definiendo el parentesco (e.g. MADRE)."""
        link = GuardianChild(guardian_id=guardian_id, child_id=child_id, relationship=relationship)
        db.add(link)
        await db.flush()
        return link

    @staticmethod
    async def get_linked_daycares(db: AsyncSession, guardian_id: uuid.UUID) -> list[Daycare]:
        """Retorna todas las guarderías asociadas al tutor."""
        query = (
            select(Daycare)
            .join(GuardianDaycare, Daycare.id == GuardianDaycare.daycare_id)
            .filter(GuardianDaycare.guardian_id == guardian_id)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_linked_children_with_relations(db: AsyncSession, guardian_id: uuid.UUID) -> list[GuardianChild]:
        """
        Retorna la relación de niños vinculados al tutor, trayendo de manera eficiente
        las relaciones a guardería, última ubicación y alertas usando joinedload (evita N+1).
        """
        query = (
            select(GuardianChild)
            .options(
                joinedload(GuardianChild.child).joinedload(Child.daycare),
                joinedload(GuardianChild.child).joinedload(Child.current_location),
                joinedload(GuardianChild.child).joinedload(Child.alerts)
            )
            .filter(GuardianChild.guardian_id == guardian_id)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_guardians_by_child(db: AsyncSession, child_id: uuid.UUID) -> list[Guardian]:
        """Retorna todos los tutores vinculados a un niño."""
        query = (
            select(Guardian)
            .join(GuardianChild, Guardian.id == GuardianChild.guardian_id)
            .filter(GuardianChild.child_id == child_id)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
