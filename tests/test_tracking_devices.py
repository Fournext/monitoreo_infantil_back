import pytest
import uuid
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from app.core.constants import PairingCodeStatus, DeviceType, UserRole
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException
from app.modules.tracking_devices.service import TrackingDeviceService
from app.modules.tracking_devices.schemas import (
    PairingCodeCreate, PairDeviceRequest
)
from app.utils.date_utils import get_now

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()
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
    return daycare

@pytest.fixture
def mock_child(mock_daycare):
    child = MagicMock()
    child.id = uuid.uuid4()
    child.code = "NIN-8F42K"
    child.daycare_id = mock_daycare.id
    child.full_name = "Mateo Vargas"
    return child

@pytest.fixture
def mock_pairing_code(mock_child, mock_daycare):
    pairing = MagicMock()
    pairing.id = uuid.uuid4()
    pairing.code = "PAIR-DEMO-001"
    pairing.child_id = mock_child.id
    pairing.daycare_id = mock_daycare.id
    pairing.child = mock_child
    pairing.daycare = mock_daycare
    pairing.status = PairingCodeStatus.ACTIVE
    pairing.expires_at = get_now() + timedelta(minutes=10)
    pairing.used_at = None
    return pairing

# --- SERVICE TESTS ---

@pytest.mark.asyncio
@patch("app.modules.children.repository.ChildRepository.get_by_code")
@patch("app.modules.daycares.repository.DaycareRepository.get_by_id")
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.create_pairing_code")
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.get_pairing_code_by_code")
async def test_generate_pairing_code_success(
    mock_get_pairing, mock_create, mock_get_dc, mock_get_child, mock_db, mock_child, mock_daycare
):
    mock_get_child.return_value = mock_child
    mock_get_dc.return_value = mock_daycare
    mock_get_pairing.return_value = None  # unique
    
    mock_created_code = MagicMock()
    mock_created_code.code = "PAIR-X7K2-91A"
    mock_create.return_value = mock_created_code

    response = await TrackingDeviceService.generate_pairing_code_for_child(
        db=mock_db,
        child_code="NIN-8F42K",
        expires_in_minutes=10,
        created_by_user_id=uuid.uuid4()
    )

    assert response.child_code == "NIN-8F42K"
    assert response.daycare_code == "GUA-SCZ-001"
    assert response.pairing_code != ""
    mock_create.assert_called_once()


@pytest.mark.asyncio
@patch("app.modules.children.repository.ChildRepository.get_by_code")
async def test_generate_pairing_code_child_not_found(mock_get_child, mock_db):
    mock_get_child.return_value = None
    with pytest.raises(NotFoundException):
        await TrackingDeviceService.generate_pairing_code_for_child(
            db=mock_db,
            child_code="NIN-NONE",
            expires_in_minutes=10,
            created_by_user_id=None
        )


@pytest.mark.asyncio
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.get_pairing_code_by_code")
async def test_cancel_pairing_code_success(mock_get_pairing, mock_db, mock_pairing_code):
    mock_get_pairing.return_value = mock_pairing_code
    
    await TrackingDeviceService.cancel_pairing_code(mock_db, "PAIR-DEMO-001")
    
    assert mock_pairing_code.status == PairingCodeStatus.CANCELLED


@pytest.mark.asyncio
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.get_pairing_code_by_code")
async def test_cancel_pairing_code_already_cancelled(mock_get_pairing, mock_db, mock_pairing_code):
    mock_pairing_code.status = PairingCodeStatus.CANCELLED
    mock_get_pairing.return_value = mock_pairing_code
    
    with pytest.raises(BadRequestException):
        await TrackingDeviceService.cancel_pairing_code(mock_db, "PAIR-DEMO-001")


@pytest.mark.asyncio
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.get_pairing_code_by_code")
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.get_active_device_by_child")
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.get_device_by_identifier_and_type")
async def test_pair_device_success_new_device(
    mock_get_device, mock_get_active, mock_get_pairing, mock_db, mock_pairing_code, mock_child
):
    mock_get_pairing.return_value = mock_pairing_code
    mock_get_active.return_value = None  # no active device
    mock_get_device.return_value = None  # new device registry

    # Mock DB insert count
    mock_db.execute.return_value.scalar.return_value = 0
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    response = await TrackingDeviceService.pair_device(
        db=mock_db,
        pairing_code_str="PAIR-DEMO-001",
        device_identifier="tracker-123",
        platform="android"
    )

    assert response.access_token != ""
    assert response.device.device_type == DeviceType.CHILD_TRACKER
    assert response.assignment.child_code == mock_child.code
    assert mock_pairing_code.status == PairingCodeStatus.USED
    assert mock_pairing_code.used_at is not None


@pytest.mark.asyncio
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.get_pairing_code_by_code")
async def test_pair_device_expired_code(mock_get_pairing, mock_db, mock_pairing_code):
    # Set expiration in past
    mock_pairing_code.expires_at = get_now() - timedelta(minutes=10)
    mock_get_pairing.return_value = mock_pairing_code

    with pytest.raises(BadRequestException) as exc_info:
        await TrackingDeviceService.pair_device(
            db=mock_db,
            pairing_code_str="PAIR-DEMO-001",
            device_identifier="tracker-123",
            platform="android"
        )
    assert "expired" in str(exc_info.value.detail).lower() or "no es válido" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
@patch("app.modules.children.repository.ChildRepository.get_by_code")
@patch("app.modules.tracking_devices.repository.TrackingDeviceRepository.get_active_device_by_child")
async def test_decouple_tracker_success(
    mock_get_active, mock_get_child, mock_db, mock_child
):
    mock_get_child.return_value = mock_child
    
    mock_device = MagicMock()
    mock_device.id = uuid.uuid4()
    mock_device.is_active = True
    mock_device.tracking_token_hash = "somehash"
    mock_get_active.return_value = mock_device

    await TrackingDeviceService.decouple_tracker_for_child(mock_db, "NIN-8F42K")

    assert mock_device.is_active is False
    assert mock_device.tracking_token_hash is None
