import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.core.constants import UserRole

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.GUARDIAN

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    guardian_id: uuid.UUID | None = None

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    guardian_id: uuid.UUID | None
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
