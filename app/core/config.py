from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Configuración de base de datos
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/monitoring_db")
    
    # Seguridad y JWT
    SECRET_KEY: str = Field(default="change_me_to_a_secure_random_key_123456789")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 días

    # Notificaciones FCM
    FIREBASE_CREDENTIALS_PATH: str = Field(default="./monitoreo-infantil-da5a9-firebase-adminsdk-fbsvc-07772f0451.json")

    # Parámetros del motor de alertas
    ALERT_OUTSIDE_CONSECUTIVE_LIMIT: int = Field(default=3)
    ALERT_OUTSIDE_SECONDS_LIMIT: int = Field(default=15)
    ALERT_COOLDOWN_SECONDS: int = Field(default=5)
    GPS_TOLERANCE_METERS: float = Field(default=3.0)

settings = Settings()
