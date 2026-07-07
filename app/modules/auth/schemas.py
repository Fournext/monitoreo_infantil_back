import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.core.constants import UserRole

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.MONITOR
    daycare_id: uuid.UUID | None = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = Field(default=None)
    role: UserRole | None = Field(default=None)
    daycare_id: uuid.UUID | None = Field(default=None)
    password: str | None = Field(default=None, min_length=6)

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class GuardianAuthResponse(BaseModel):
    id: uuid.UUID
    code: str
    full_name: str
    must_change_pin: bool

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None
    guardian: GuardianAuthResponse | None = None

class GuardianLoginRequest(BaseModel):
    guardian_code: str
    pin: str

class ChangePinRequest(BaseModel):
    current_pin: str = Field(..., min_length=4, max_length=6)
    new_pin: str = Field(..., min_length=4, max_length=6)

class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    code: str | None = None
    full_name: str
    role: str
    must_change_pin: bool = False
