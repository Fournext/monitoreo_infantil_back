import random
import string

def _generate_random_alphanumeric(length: int = 5) -> str:
    """Genera un string aleatorio alfanumérico en mayúsculas."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_daycare_code(next_num: int) -> str:
    """Genera un código correlativo para guarderías en formato GUA-SCZ-XXX."""
    return f"GUA-SCZ-{next_num:03d}"

def generate_child_code() -> str:
    """Genera un código aleatorio para niños en formato NIN-XXXXX."""
    return f"NIN-{_generate_random_alphanumeric(5)}"

def generate_guardian_code() -> str:
    """Genera un código aleatorio para tutores en formato TUT-XXXXX."""
    return f"TUT-{_generate_random_alphanumeric(5)}"

def generate_alert_code(next_num: int) -> str:
    """Genera un código correlativo para alertas en formato ALT-XXXX."""
    return f"ALT-{next_num:04d}"

def generate_device_code(next_num: int) -> str:
    """Genera un código correlativo para dispositivos en formato DEV-XXXX."""
    return f"DEV-{next_num:04d}"
