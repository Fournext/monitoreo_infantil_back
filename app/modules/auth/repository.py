import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.modules.auth.models import User
from app.modules.auth.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash

class UserRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Busca un usuario por su ID primario."""
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> User | None:
        """Busca un usuario por su nombre de usuario."""
        result = await db.execute(select(User).filter(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """Busca un usuario por su email."""
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username_or_email(db: AsyncSession, identifier: str) -> User | None:
        """Busca un usuario coincidiendo con su username o correo electrónico."""
        result = await db.execute(
            select(User).filter(
                or_(User.username == identifier, User.email == identifier)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, user_in: UserCreate) -> User:
        """Crea un nuevo usuario encriptando su contraseña."""
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            role=user_in.role,
            daycare_id=user_in.daycare_id
        )
        db.add(db_user)
        await db.flush()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def get_all(db: AsyncSession) -> list[User]:
        """Obtiene todos los usuarios del sistema ordenados por su username."""
        result = await db.execute(select(User).order_by(User.username))
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, user: User, user_in: UserUpdate) -> User:
        """Actualiza los campos de un usuario, encriptando la contraseña si se provee una nueva."""
        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for key, value in update_data.items():
            setattr(user, key, value)
            
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user
