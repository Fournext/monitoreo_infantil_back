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
from app.modules.auth.schemas import UserCreate, UserLogin, GuardianLoginRequest, ChangePinRequest
from app.modules.guardians.models import Guardian

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
    async def get_current_user_ws(token: str | None, db: AsyncSession) -> User | Guardian:
        """Método helper para validar tokens en WebSockets desde los parámetros de consulta."""
        if not token:
            raise UnauthorizedException("Token de WebSocket ausente.")
            
        payload = decode_access_token(token)
        if not payload:
            raise UnauthorizedException("Token de WebSocket inválido o expirado.")
            
        user_id_str = payload.get("sub")
        role = payload.get("role")
        if not user_id_str or not role:
            raise UnauthorizedException("El token no contiene claims válidos.")
            
        try:
            entity_id = uuid.UUID(user_id_str)
        except ValueError:
            raise UnauthorizedException("Identificador inválido.")
            
        if role == UserRole.GUARDIAN:
            from app.modules.guardians.repository import GuardianRepository
            guardian = await GuardianRepository.get_by_id(db, entity_id)
            if not guardian:
                raise UnauthorizedException("El tutor asociado al token no existe.")
            guardian.role = UserRole.GUARDIAN
            return guardian
        else:
            user = await UserRepository.get_by_id(db, entity_id)
            if not user:
                raise UnauthorizedException("Usuario asociado al token no existe.")
            return user

    @staticmethod
    async def authenticate_guardian(db: AsyncSession, login_data: GuardianLoginRequest) -> Guardian:
        """Autentica a un tutor por código y PIN, manejando intentos fallidos y bloqueos."""
        from app.modules.guardians.repository import GuardianRepository
        from app.utils.date_utils import get_now
        from app.core.security import verify_pin
        from datetime import timedelta
        from app.core.constants import GuardianStatus
        from app.core.exceptions import NotFoundException, ForbiddenException, UnauthorizedException
        
        guardian = await GuardianRepository.get_by_code(db, login_data.guardian_code)
        if not guardian:
            raise UnauthorizedException("El código de tutor o PIN es incorrecto.")
            
        now = get_now()
        
        # Verificar bloqueo permanente o por admin
        if guardian.status == GuardianStatus.BLOCKED:
            raise ForbiddenException("Esta cuenta de tutor se encuentra bloqueada permanentemente.")
        if guardian.status == GuardianStatus.INACTIVE:
            raise ForbiddenException("Esta cuenta de tutor se encuentra inactiva.")
            
        # Verificar bloqueo temporal
        if guardian.locked_until and guardian.locked_until > now:
            time_left = guardian.locked_until - now
            minutes_left = int(time_left.total_seconds() / 60) + 1
            raise ForbiddenException(
                f"El acceso está bloqueado temporalmente por demasiados intentos fallidos. "
                f"Intente nuevamente en {minutes_left} minuto(s)."
            )
            
        # Verificar PIN
        if not verify_pin(login_data.pin, guardian.pin_hash):
            guardian.failed_login_attempts += 1
            if guardian.failed_login_attempts >= 5:
                guardian.locked_until = now + timedelta(minutes=15)
                # Resetear attempts para la siguiente ronda tras expirar
                guardian.failed_login_attempts = 0
                await db.flush()
                raise ForbiddenException(
                    "Código o PIN incorrecto. Ha superado el límite de intentos fallidos. "
                    "Su cuenta ha sido bloqueada temporalmente por 15 minutos."
                )
            await db.flush()
            raise UnauthorizedException("El código de tutor o PIN es incorrecto.")
            
        # Login exitoso
        guardian.failed_login_attempts = 0
        guardian.locked_until = None
        guardian.last_login_at = now
        await db.flush()
        
        return guardian

    @staticmethod
    async def change_guardian_pin(db: AsyncSession, guardian: Guardian, change_data: ChangePinRequest) -> None:
        """Cambia el PIN de acceso del tutor verificado."""
        from app.core.security import verify_pin, get_pin_hash
        from app.core.exceptions import BadRequestException
        
        if not change_data.new_pin.isdigit() or len(change_data.new_pin) not in (4, 6):
            raise BadRequestException("El nuevo PIN debe contener exactamente 4 o 6 dígitos numéricos.")
            
        if not verify_pin(change_data.current_pin, guardian.pin_hash):
            raise BadRequestException("El PIN actual es incorrecto.")
            
        if change_data.current_pin == change_data.new_pin:
            raise BadRequestException("El nuevo PIN no puede ser igual al PIN actual.")
            
        guardian.pin_hash = get_pin_hash(change_data.new_pin)
        guardian.must_change_pin = False
        await db.flush()


def require_roles(*allowed_roles: UserRole):
    """Generador de dependencias para restringir accesos según roles."""
    async def role_checker(current_user: Annotated[User, Depends(UserService.get_current_user)]):
        if current_user.role not in allowed_roles:
            raise ForbiddenException("No tienes permisos suficientes para realizar esta acción.")
        return current_user
    return role_checker
