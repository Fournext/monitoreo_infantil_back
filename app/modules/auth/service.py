import uuid
from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import verify_password, decode_access_token, create_access_token
from app.core.exceptions import UnauthorizedException, ConflictException, ForbiddenException
from app.core.constants import UserRole
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import UserCreate, UserLogin

# Define el esquema OAuth2 para resolver el header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

class UserService:
    @staticmethod
    async def authenticate(db: AsyncSession, login_data: UserLogin) -> User:
        """Autentica a un usuario y retorna la entidad si las credenciales son válidas."""
        user = await UserRepository.get_by_username_or_email(db, login_data.username_or_email)
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise UnauthorizedException("El nombre de usuario, correo o la contraseña son incorrectos.")
        return user

    @staticmethod
    async def register(db: AsyncSession, user_in: UserCreate) -> User:
        """Registra un nuevo usuario verificando unicidad de username y email."""
        existing_username = await UserRepository.get_by_username(db, user_in.username)
        if existing_username:
            raise ConflictException("El nombre de usuario ya se encuentra registrado.")
            
        existing_email = await UserRepository.get_by_email(db, user_in.email)
        if existing_email:
            raise ConflictException("El correo electrónico ya se encuentra registrado.")
            
        return await UserRepository.create(db, user_in)

    @staticmethod
    async def get_current_user(
        token: Annotated[str | None, Depends(oauth2_scheme)],
        db: Annotated[AsyncSession, Depends(get_db)]
    ) -> User:
        """Dependencia para resolver el usuario autenticado a partir del token JWT."""
        if not token:
            raise UnauthorizedException("Falta el token de autenticación.")
            
        payload = decode_access_token(token)
        if not payload:
            raise UnauthorizedException("El token es inválido o ha expirado.")
            
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("El token no contiene un identificador de usuario válido.")
            
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise UnauthorizedException("El identificador de usuario en el token es inválido.")
            
        user = await UserRepository.get_by_id(db, user_id)
        if not user:
            raise UnauthorizedException("El usuario asociado al token ya no existe.")
            
        return user

    @staticmethod
    async def get_current_user_ws(token: str | None, db: AsyncSession) -> User:
        """Método helper para validar tokens en WebSockets desde los parámetros de consulta."""
        if not token:
            raise UnauthorizedException("Token de WebSocket ausente.")
            
        payload = decode_access_token(token)
        if not payload:
            raise UnauthorizedException("Token de WebSocket inválido o expirado.")
            
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("El token no contiene un identificador de usuario.")
            
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise UnauthorizedException("Identificador de usuario inválido.")
            
        user = await UserRepository.get_by_id(db, user_id)
        if not user:
            raise UnauthorizedException("Usuario asociado al token no existe.")
            
        return user

def require_roles(*allowed_roles: UserRole):
    """Generador de dependencias para restringir accesos según roles."""
    async def role_checker(current_user: Annotated[User, Depends(UserService.get_current_user)]):
        if current_user.role not in allowed_roles:
            raise ForbiddenException("No tienes permisos suficientes para realizar esta acción.")
        return current_user
    return role_checker
