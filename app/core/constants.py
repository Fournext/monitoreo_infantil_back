from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DAYCARE_MANAGER = "DAYCARE_MANAGER"
    OPERATOR = "OPERATOR"
    MONITOR = "MONITOR"

class DaycareStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class GuardianStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"

class ChildStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class PairingCodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class DeviceType(str, Enum):
    GUARDIAN_PHONE = "GUARDIAN_PHONE"
    CHILD_TRACKER = "CHILD_TRACKER"

class AlertType(str, Enum):
    OUT_OF_AREA = "OUT_OF_AREA"
    NO_SIGNAL = "NO_SIGNAL"
    GPS_ERROR = "GPS_ERROR"

class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class AlertStatus(str, Enum):
    NEW = "NEW"
    VIEWED = "VIEWED"
    RESOLVED = "RESOLVED"

class NotificationLogStatus(str, Enum):
    SENT = "SENT"
    FAILED = "FAILED"
