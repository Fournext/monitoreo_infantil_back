from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Contexto para encriptación de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return pwd_context.hash(password)

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verifica si un PIN coincide con su hash."""
    return pwd_context.verify(plain_pin, hashed_pin)

def get_pin_hash(pin: str) -> str:
    """Genera el hash de un PIN."""
    return pwd_context.hash(pin)

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Genera un token de acceso JWT firmado."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decodifica y valida un token de acceso JWT."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.JWTError:
        return None
