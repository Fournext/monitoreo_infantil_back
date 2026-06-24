import random
import string

def generate_child_code() -> str:
    """Genera un código aleatorio para niños en formato NIN-XXXXX (e.g. NIN-8F42K)."""
    chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"NIN-{chars}"

def generate_alert_code() -> str:
    """Genera un código aleatorio para alertas en formato ALT-XXXXX (e.g. ALT-98214)."""
    chars = "".join(random.choices(string.digits, k=5))
    return f"ALT-{chars}"

def generate_daycare_code(next_num: int) -> str:
    """Genera un código correlativo para guarderías en formato GUA-SCZ-XXX (e.g. GUA-SCZ-001)."""
    return f"GUA-SCZ-{next_num:03d}"
