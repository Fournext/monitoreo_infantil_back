from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.constants import UserRole
from app.core.exceptions import BadRequestException
from app.modules.auth.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    GuardianLoginRequest, ChangePinRequest, CurrentUserResponse
)
from app.modules.auth.service import UserService
from app.modules.auth.dependencies import get_current_user, get_current_guardian
from app.modules.guardians.models import Guardian
from app.modules.auth.models import User

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

async def get_login_data(request: Request) -> UserLogin:
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")
        if not username or not password:
            raise BadRequestException("Falta username o password en el formulario.")
        return UserLogin(username_or_email=str(username), password=str(password))
    else:
        try:
            body = await request.json()
            username_or_email = body.get("username_or_email") or body.get("username")
            password = body.get("password")
            if not username_or_email or not password:
                raise BadRequestException("Falta username/correo o contraseña.")
            return UserLogin(username_or_email=username_or_email, password=password)
        except Exception as e:
            if isinstance(e, BadRequestException):
                raise
            raise BadRequestException("Cuerpo de petición inválido (se esperaba JSON o Form-urlencoded).")

@router.post(
    "/login", 
    response_model=TokenResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username_or_email": {"type": "string", "example": "admin"},
                            "password": {"type": "string", "example": "adminpassword"}
                        },
                        "required": ["username_or_email", "password"]
                    }
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"}
                        },
                        "required": ["username", "password"]
                    }
                }
            }
        }
    }
)
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Autentica a un usuario y genera su token de acceso JWT.
    Soporta formato JSON (para clientes web/móvil) y Form-urlencoded (para el botón 'Authorize' de Swagger).
    """
    login_data = await get_login_data(request)
    user = await UserService.authenticate(db, login_data)
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=access_token, user=user)

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Registra un nuevo usuario en la plataforma (ADMIN o GUARDIAN).
    """
    user = await UserService.register(db, user_in)
    await db.commit()
    return user

@router.post("/guardian/login", response_model=TokenResponse)
async def guardian_login(login_data: GuardianLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Autentica a un tutor con su código y PIN, retornando un token de acceso JWT.
    """
    guardian = await UserService.authenticate_guardian(db, login_data)
    access_token = create_access_token(data={
        "sub": str(guardian.id),
        "role": "GUARDIAN",
        "code": guardian.code
    })
    await db.commit()
    return TokenResponse(access_token=access_token, guardian=guardian)

@router.patch("/guardian/change-pin", status_code=200)
async def change_pin(
    change_data: ChangePinRequest,
    db: AsyncSession = Depends(get_db),
    current_guardian: Guardian = Depends(get_current_guardian)
):
    """
    Permite al tutor autenticado cambiar su PIN de acceso.
    """
    await UserService.change_guardian_pin(db, current_guardian, change_data)
    await db.commit()
    return {"message": "PIN cambiado correctamente."}

@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user: User | Guardian = Depends(get_current_user)):
    """
    Retorna la información del usuario o tutor autenticado en la sesión actual.
    """
    if isinstance(current_user, Guardian):
        return CurrentUserResponse(
            id=current_user.id,
            code=current_user.code,
            full_name=current_user.full_name,
            role="GUARDIAN",
            must_change_pin=current_user.must_change_pin
        )
    else:
        return CurrentUserResponse(
            id=current_user.id,
            code=None,
            full_name=current_user.username,
            role=current_user.role,
            must_change_pin=False
        )
