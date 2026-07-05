from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.constants import UserRole
from app.modules.auth.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    GuardianLoginRequest, ChangePinRequest, CurrentUserResponse
)
from app.modules.auth.service import UserService
from app.modules.auth.dependencies import get_current_user, get_current_guardian
from app.modules.guardians.models import Guardian
from app.modules.auth.models import User

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Registra un nuevo usuario en la plataforma (ADMIN o GUARDIAN).
    """
    user = await UserService.register(db, user_in)
    await db.commit()
    return user

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Autentica a un usuario y genera su token de acceso JWT.
    """
    user = await UserService.authenticate(db, login_data)
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=access_token, user=user)

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
