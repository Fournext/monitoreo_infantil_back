from datetime import datetime, timezone

def get_now() -> datetime:
    """Retorna la fecha y hora actual con información de zona horaria UTC."""
    return datetime.now(timezone.utc)

def parse_iso_datetime(dt_str: str) -> datetime:
    """Parsea una cadena en formato ISO a un objeto datetime. Si falla, retorna la hora actual."""
    try:
        # Asegura la lectura correcta de la cadena ISO
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return get_now()
