from datetime import datetime, timezone, timedelta
from typing import Annotated
from pydantic import PlainSerializer

# Zona horaria de Bolivia / Santa Cruz de la Sierra (UTC-4)
tz_bolivia = timezone(timedelta(hours=-4))

def to_bolivia_tz(dt: datetime) -> datetime:
    """Asegura que el objeto datetime tenga la zona horaria de Bolivia (UTC-4).
    Si no tiene zona horaria (naive), asume que está en UTC antes de convertir.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz_bolivia)

def get_now() -> datetime:
    """Retorna la fecha y hora actual con información de zona horaria de Bolivia (UTC-4)."""
    return datetime.now(tz_bolivia)

def parse_iso_datetime(dt_str: str) -> datetime:
    """Parsea una cadena en formato ISO a un objeto datetime y la convierte a zona horaria de Bolivia."""
    try:
        # Asegura la lectura correcta de la cadena ISO
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return to_bolivia_tz(dt)
    except Exception:
        return get_now()

def serialize_bolivia_datetime(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return to_bolivia_tz(dt).isoformat()

# Tipo anotado para Pydantic que serializa datetimes en zona horaria de Bolivia
BoliviaDateTime = Annotated[
    datetime,
    PlainSerializer(
        serialize_bolivia_datetime,
        return_type=str
    )
]
