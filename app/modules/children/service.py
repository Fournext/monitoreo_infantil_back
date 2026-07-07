import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.modules.children.models import Child
from app.modules.children.repository import ChildRepository
from app.modules.daycares.repository import DaycareRepository
from app.modules.children.schemas import ChildCreate, ChildResponse, ChildUpdate

class ChildService:
    @classmethod
    async def create_child(cls, db: AsyncSession, child_in: ChildCreate) -> ChildResponse:
        """
        Crea el perfil de un niño asociándolo a una guardería existente.
        """
        daycare = await DaycareRepository.get_by_id(db, child_in.daycare_id)
        if not daycare:
            raise NotFoundException(f"Guardería con ID '{child_in.daycare_id}' no existe.")

        child = await ChildRepository.create(db, child_in)
        return ChildResponse.model_validate(child)

    @classmethod
    async def get_child_by_code(cls, db: AsyncSession, code: str) -> ChildResponse:
        """Busca un niño por su código."""
        child = await ChildRepository.get_by_code(db, code)
        if not child:
            raise NotFoundException(f"Niño con código '{code}' no encontrado.")
        return ChildResponse.model_validate(child)

    @classmethod
    async def list_children(cls, db: AsyncSession, daycare_id: uuid.UUID | None = None) -> list[ChildResponse]:
        """Retorna una lista de niños, opcionalmente filtrados por guardería."""
        children = await ChildRepository.get_all(db, daycare_id)
        return [ChildResponse.model_validate(c) for c in children]

    @classmethod
    async def update_child(cls, db: AsyncSession, code: str, child_in: ChildUpdate) -> ChildResponse:
        """Actualiza la ficha de un niño por su código correlativo."""
        child = await ChildRepository.get_by_code(db, code)
        if not child:
            raise NotFoundException(f"Niño con código '{code}' no encontrado.")
            
        if child_in.daycare_id:
            daycare = await DaycareRepository.get_by_id(db, child_in.daycare_id)
            if not daycare:
                raise NotFoundException(f"Guardería con ID '{child_in.daycare_id}' no existe.")
                
        updated_child = await ChildRepository.update(db, child, child_in)
        return ChildResponse.model_validate(updated_child)
