import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from app.core.constants import UserRole, GuardianStatus
from app.core.exceptions import UnauthorizedException, ForbiddenException, BadRequestException
from app.modules.auth.schemas import GuardianLoginRequest, ChangePinRequest
from app.modules.auth.service import UserService

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    return db

@pytest.fixture
def mock_guardian():
    from app.core.security import get_pin_hash
    guardian = MagicMock()
    guardian.id = uuid.uuid4()
    guardian.code = "TUT-7A91P"
    guardian.full_name = "Ana Vargas"
    guardian.phone = "70000001"
    guardian.email = "ana@example.com"
    guardian.pin_hash = get_pin_hash("1234")
    guardian.must_change_pin = True
    guardian.status = GuardianStatus.ACTIVE
    guardian.failed_login_attempts = 0
    guardian.locked_until = None
    return guardian

@pytest.mark.asyncio
@patch("app.modules.guardians.repository.GuardianRepository.get_by_code")
async def test_authenticate_guardian_success(mock_get_by_code, mock_db, mock_guardian):
    mock_get_by_code.return_value = mock_guardian
    
    login_data = GuardianLoginRequest(guardian_code="TUT-7A91P", pin="1234")
    auth_guardian = await UserService.authenticate_guardian(mock_db, login_data)
    
    assert auth_guardian.id == mock_guardian.id
    assert auth_guardian.failed_login_attempts == 0
    assert auth_guardian.locked_until is None

@pytest.mark.asyncio
@patch("app.modules.guardians.repository.GuardianRepository.get_by_code")
async def test_authenticate_guardian_wrong_pin(mock_get_by_code, mock_db, mock_guardian):
    mock_get_by_code.return_value = mock_guardian
    
    login_data = GuardianLoginRequest(guardian_code="TUT-7A91P", pin="9999")
    
    with pytest.raises(UnauthorizedException):
        await UserService.authenticate_guardian(mock_db, login_data)
        
    assert mock_guardian.failed_login_attempts == 1

@pytest.mark.asyncio
@patch("app.modules.guardians.repository.GuardianRepository.get_by_code")
async def test_authenticate_guardian_lockout(mock_get_by_code, mock_db, mock_guardian):
    mock_get_by_code.return_value = mock_guardian
    mock_guardian.failed_login_attempts = 4
    
    login_data = GuardianLoginRequest(guardian_code="TUT-7A91P", pin="9999")
    
    with pytest.raises(ForbiddenException) as exc_info:
        await UserService.authenticate_guardian(mock_db, login_data)
        
    assert "bloqueada temporalmente" in str(exc_info.value.detail)
    assert mock_guardian.locked_until is not None

@pytest.mark.asyncio
async def test_change_guardian_pin_success(mock_db, mock_guardian):
    change_data = ChangePinRequest(current_pin="1234", new_pin="5678")
    
    await UserService.change_guardian_pin(mock_db, mock_guardian, change_data)
    
    from app.core.security import verify_pin
    assert verify_pin("5678", mock_guardian.pin_hash) is True
    assert mock_guardian.must_change_pin is False

@pytest.mark.asyncio
async def test_change_guardian_pin_same_error(mock_db, mock_guardian):
    change_data = ChangePinRequest(current_pin="1234", new_pin="1234")
    
    with pytest.raises(BadRequestException):
        await UserService.change_guardian_pin(mock_db, mock_guardian, change_data)
