from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import create_access_token
from app.modules.auth.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.modules.auth.service import UserService

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
