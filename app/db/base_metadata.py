from app.db.base import Base

# Importar todos los modelos para registrar las tablas en la metadata de Base
from app.modules.auth.models import User
from app.modules.daycares.models import Daycare
from app.modules.guardians.models import Guardian, GuardianChild, GuardianDaycare
from app.modules.children.models import Child
from app.modules.devices.models import Device
from app.modules.locations.models import ChildLocation, CurrentChildLocation
from app.modules.alerts.models import Alert, AlertNotificationLog
from app.modules.tracking_devices.models import TrackerPairingCode
