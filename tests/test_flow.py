import pytest
import app.db.base_metadata
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from app.core.constants import UserRole, AlertStatus, AlertType
from app.modules.daycares.schemas import DaycareCreate
from app.modules.daycares.service import DaycareService
from app.modules.guardians.service import GuardianService
from app.modules.locations.service import LocationService
from app.modules.locations.schemas import LocationInput
from app.shared.geo.spatial_service import SpatialService

# Mock models
@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    result.scalars.return_value.all = MagicMock(return_value=[])
    result.scalars.return_value.first = MagicMock(return_value=None)
    
    db.execute.return_value = result
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    return db

@pytest.fixture
def mock_daycare():
    daycare = MagicMock()
    daycare.id = uuid.uuid4()
    daycare.code = "GUA-SCZ-001"
    daycare.name = "Guardería Los Pinos"
    daycare.address = "Santa Cruz de la Sierra"
    daycare.status = "ACTIVE"
    daycare.area = "MOCK_GEOMETRY"
    daycare.created_at = datetime.now(timezone.utc)
    daycare.updated_at = datetime.now(timezone.utc)
    return daycare

@pytest.fixture
def mock_child(mock_daycare):
    child = MagicMock()
    child.id = uuid.uuid4()
    child.code = "NIN-8F42K"
    child.daycare_id = mock_daycare.id
    child.full_name = "Mateo Vargas"
    child.age = 4
    child.status = "ACTIVE"
    child.alerts = []
    child.current_location = None
    return child

@pytest.fixture
def mock_guardian():
    guardian = MagicMock()
    guardian.id = uuid.uuid4()
    guardian.full_name = "Ana Vargas"
    guardian.phone = "70000001"
    guardian.email = "ana@example.com"
    return guardian

# --- TESTS ---

@pytest.mark.asyncio
@patch("app.modules.daycares.repository.DaycareRepository.create")
async def test_create_daycare(mock_repo_create, mock_db, mock_daycare):
    # Configurar mock de repositorio
    mock_repo_create.return_value = mock_daycare
    
    daycare_in = DaycareCreate(name="Guardería Los Pinos", address="Santa Cruz de la Sierra")
    response = await DaycareService.create_daycare(mock_db, daycare_in)
    
    assert response.name == "Guardería Los Pinos"
    assert response.code == "GUA-SCZ-001"
    assert response.has_area is True  # Tiene mock de geometría
    mock_repo_create.assert_called_once()


@pytest.mark.asyncio
@patch("app.shared.geo.spatial_service.SpatialService.validate_polygon_geojson")
@patch("app.shared.geo.spatial_service.SpatialService.geojson_to_polygon_wkt")
@patch("app.modules.daycares.repository.DaycareRepository.get_by_code")
@patch("app.modules.daycares.repository.DaycareRepository.update_area")
async def test_update_daycare_area(
    mock_update_area, mock_get_code, mock_to_wkt, mock_validate, mock_db, mock_daycare
):
    mock_get_code.return_value = mock_daycare
    mock_update_area.return_value = mock_daycare
    mock_to_wkt.return_value = "POLYGON((-63.1821 -17.7833, ...))"

    geojson = {
        "type": "Polygon",
        "coordinates": [[
            [-63.1821, -17.7833],
            [-63.1815, -17.7833],
            [-63.1815, -17.7827],
            [-63.1821, -17.7827],
            [-63.1821, -17.7833]
        ]]
    }

    response = await DaycareService.update_daycare_area(mock_db, "GUA-SCZ-001", geojson)
    
    mock_validate.assert_called_once_with(geojson)
    mock_to_wkt.assert_called_once_with(geojson)
    mock_update_area.assert_called_once()
    assert response.code == "GUA-SCZ-001"


@pytest.mark.asyncio
@patch("app.modules.daycares.repository.DaycareRepository.get_by_code")
@patch("app.modules.guardians.repository.GuardianRepository.get_by_id")
@patch("app.modules.guardians.repository.GuardianRepository.get_daycare_link")
@patch("app.modules.guardians.repository.GuardianRepository.link_daycare")
async def test_link_daycare_to_guardian(
    mock_link, mock_get_link, mock_get_guardian, mock_get_daycare, mock_db, mock_daycare, mock_guardian
):
    mock_get_daycare.return_value = mock_daycare
    mock_get_guardian.return_value = mock_guardian
    mock_get_link.return_value = None  # No está vinculada aún
    
    await GuardianService.link_daycare_by_code(mock_db, mock_guardian.id, "GUA-SCZ-001")
    
    mock_link.assert_called_once_with(mock_db, mock_guardian.id, mock_daycare.id)


@pytest.mark.asyncio
@patch("app.modules.daycares.repository.DaycareRepository.get_by_code")
@patch("app.modules.children.repository.ChildRepository.get_by_code")
@patch("app.modules.guardians.repository.GuardianRepository.get_daycare_link")
@patch("app.modules.guardians.repository.GuardianRepository.get_child_link")
@patch("app.modules.guardians.repository.GuardianRepository.link_child")
async def test_link_child_to_guardian(
    mock_link, mock_get_child_link, mock_get_dc_link, mock_get_child, mock_get_daycare, 
    mock_db, mock_daycare, mock_child, mock_guardian
):
    mock_get_daycare.return_value = mock_daycare
    mock_get_child.return_value = mock_child
    mock_get_dc_link.return_value = MagicMock()  # Ya está vinculado a la guardería
    mock_get_child_link.return_value = None  # No está vinculado al niño
    
    await GuardianService.link_child_by_code(
        db=mock_db,
        guardian_id=mock_guardian.id,
        daycare_code="GUA-SCZ-001",
        child_code="NIN-8F42K",
        relationship="MADRE"
    )
    
    mock_link.assert_called_once_with(mock_db, mock_guardian.id, mock_child.id, "MADRE")


@pytest.mark.asyncio
@patch("app.modules.children.repository.ChildRepository.get_by_code")
@patch("app.modules.daycares.repository.DaycareRepository.get_by_id")
@patch("app.shared.geo.spatial_service.SpatialService.check_if_inside_with_tolerance")
@patch("app.modules.locations.repository.LocationRepository.create_location")
@patch("app.modules.locations.repository.LocationRepository.update_current_location")
@patch("app.shared.websocket.connection_manager.ConnectionManager.broadcast_to_guardians")
async def test_process_location_inside(
    mock_broadcast, mock_update_curr, mock_create_loc, mock_check_inside, 
    mock_get_daycare, mock_get_child, mock_db, mock_child, mock_daycare
):
    mock_get_child.return_value = mock_child
    mock_get_daycare.return_value = mock_daycare
    mock_check_inside.return_value = True  # El niño está adentro
    
    loc_input = LocationInput(
        latitude=-17.7833,
        longitude=-63.1821,
        accuracy=8.5,
        received_at=datetime.now(timezone.utc)
    )
    
    await LocationService.process_child_location(mock_db, "NIN-8F42K", loc_input)
    
    mock_create_loc.assert_called_once()
    mock_update_curr.assert_called_once()
    mock_broadcast.assert_called_once()


@pytest.mark.asyncio
@patch("app.modules.children.repository.ChildRepository.get_by_code")
@patch("app.modules.daycares.repository.DaycareRepository.get_by_id")
@patch("app.shared.geo.spatial_service.SpatialService.check_if_inside_with_tolerance")
@patch("app.modules.locations.repository.LocationRepository.create_location")
@patch("app.modules.locations.repository.LocationRepository.update_current_location")
@patch("app.modules.locations.repository.LocationRepository.get_recent_locations")
@patch("app.modules.alerts.repository.AlertRepository.get_active_alert_by_child_and_type")
@patch("app.modules.guardians.repository.GuardianRepository.get_guardians_by_child")
@patch("app.modules.devices.repository.DeviceRepository.get_active_guardian_devices")
@patch("app.modules.notifications.service.NotificationService.log_and_send_notification")
@patch("app.shared.websocket.connection_manager.ConnectionManager.broadcast_to_guardians")
async def test_process_location_outside_alert_trigger(
    mock_broadcast, mock_send_push, mock_get_devices, mock_get_guardians, 
    mock_get_active_alert, mock_get_recent, mock_update_curr, mock_create_loc, 
    mock_check_inside, mock_get_daycare, mock_get_child, mock_db, mock_child, mock_daycare, mock_guardian
):
    mock_get_child.return_value = mock_child
    mock_get_daycare.return_value = mock_daycare
    mock_check_inside.return_value = False  # El niño está afuera
    
    # Simular 3 lecturas anteriores consecutivas fuera
    loc1 = MagicMock()
    loc1.is_inside_area = False
    loc1.received_at = datetime.now(timezone.utc) - timedelta(seconds=20)
    loc2 = MagicMock()
    loc2.is_inside_area = False
    loc2.received_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    
    new_loc_mock = MagicMock()
    new_loc_mock.id = uuid.uuid4()
    new_loc_mock.is_inside_area = False
    new_loc_mock.received_at = datetime.now(timezone.utc)
    mock_create_loc.return_value = new_loc_mock
    
    mock_db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    mock_get_recent.return_value = [loc1, loc2]
    mock_get_active_alert.return_value = None  # No hay alertas activas
    mock_get_guardians.return_value = [mock_guardian]
    
    device = MagicMock()
    device.id = uuid.uuid4()
    device.fcm_token = "mock_fcm_token_123"
    mock_get_devices.return_value = [device]
    
    loc_input = LocationInput(
        latitude=-17.7900,  # Coordenada fuera
        longitude=-63.1900,
        accuracy=10.0,
        received_at=datetime.now(timezone.utc)
    )
    
    # Procesar
    await LocationService.process_child_location(mock_db, "NIN-8F42K", loc_input)
    
    # Debe crear ubicación e intentar enviar push
    assert mock_create_loc.called
    assert mock_send_push.called


@pytest.mark.asyncio
@patch("app.modules.alerts.repository.AlertRepository.get_by_code")
async def test_update_alert_resolved_to_viewed_raises_bad_request(mock_get_by_code, mock_db):
    from app.modules.alerts.service import AlertService
    from app.core.exceptions import BadRequestException
    
    alert = MagicMock()
    alert.status = AlertStatus.RESOLVED
    alert.child_id = uuid.uuid4()
    mock_get_by_code.return_value = alert
    
    with pytest.raises(BadRequestException) as exc_info:
        await AlertService.update_status_by_code(
            db=mock_db,
            code="ALT-00001",
            new_status=AlertStatus.VIEWED,
            guardian_id=uuid.uuid4(),
            is_admin=True
        )
    
    assert "No se puede marcar como vista una alerta que ya ha sido resuelta" in str(exc_info.value)


def test_alert_properties_serialization():
    from app.modules.alerts.schemas import AlertResponse
    from app.modules.alerts.models import Alert
    from app.modules.children.models import Child
    from app.modules.daycares.models import Daycare
    from app.core.constants import AlertSeverity
    
    daycare = Daycare(code="GUA-001", name="Guarderia Pinos")
    child = Child(code="NIN-001", full_name="Juan Perez", daycare=daycare)
    alert = Alert(
        id=uuid.uuid4(),
        code="ALT-001",
        child_id=uuid.uuid4(),
        daycare_id=uuid.uuid4(),
        alert_type=AlertType.OUT_OF_AREA,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.NEW,
        title="Alerta",
        message="Mensaje",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        child=child
    )
    
    response = AlertResponse.model_validate(alert)
    assert response.child_code == "NIN-001"
    assert response.child_name == "Juan Perez"
    assert response.daycare_code == "GUA-001"
    assert response.daycare_name == "Guarderia Pinos"
