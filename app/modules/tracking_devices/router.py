import uuid
from typing import Any
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_db
from app.core.constants import UserRole
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.auth.dependencies import require_daycare_manager
from app.modules.auth.models import User
from app.modules.children.repository import ChildRepository
from app.modules.tracking_devices.schemas import (
    PairingCodeCreate, PairingCodeResponse, PairingCodeListResponse,
    PairDeviceRequest, PairDeviceResponse, ChildTrackerResponse
)
from app.modules.tracking_devices.service import TrackingDeviceService
from app.modules.tracking_devices.repository import TrackingDeviceRepository

router = APIRouter(prefix="/api/tracking-devices", tags=["Dispositivos de Rastreo"])

async def check_daycare_manager_permission(db: AsyncSession, current_user: User, daycare_id: uuid.UUID):
    """
    Verifica que si el usuario es un DAYCARE_MANAGER, pertenezca a la guardería indicada.
    """
    if current_user.role == UserRole.DAYCARE_MANAGER:
        if current_user.daycare_id != daycare_id:
            raise ForbiddenException("No tienes permisos para realizar operaciones sobre la guardería del niño.")

@router.post("/pairing-codes", response_model=PairingCodeResponse, status_code=status.HTTP_200_OK)
async def generate_pairing_code(
    payload: PairingCodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_daycare_manager)
):
    """
    Genera un código temporal y QR de emparejamiento para un niño. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    child = await ChildRepository.get_by_code(db, payload.child_code)
    if not child:
        raise NotFoundException(f"Niño con código '{payload.child_code}' no encontrado.")
    
    await check_daycare_manager_permission(db, current_user, child.daycare_id)
    
    response = await TrackingDeviceService.generate_pairing_code_for_child(
        db=db,
        child_code=payload.child_code,
        expires_in_minutes=payload.expires_in_minutes,
        created_by_user_id=current_user.id
    )
    await db.commit()
    return response

@router.get("/pairing-codes", response_model=list[PairingCodeListResponse])
async def list_pairing_codes(
    child_code: str = Query(..., min_length=3),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_daycare_manager)
):
    """
    Lista todos los códigos de emparejamiento generados para un niño. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    child = await ChildRepository.get_by_code(db, child_code)
    if not child:
        raise NotFoundException(f"Niño con código '{child_code}' no encontrado.")
        
    await check_daycare_manager_permission(db, current_user, child.daycare_id)
    
    return await TrackingDeviceService.list_pairing_codes_for_child(db, child_code)

@router.patch("/pairing-codes/{pairing_code}/cancel", status_code=status.HTTP_200_OK)
async def cancel_pairing_code(
    pairing_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_daycare_manager)
):
    """
    Cancela un código de emparejamiento activo. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    pairing = await TrackingDeviceRepository.get_pairing_code_by_code(db, pairing_code)
    if not pairing:
        raise NotFoundException(f"Código de emparejamiento '{pairing_code}' no encontrado.")
        
    await check_daycare_manager_permission(db, current_user, pairing.daycare_id)
    
    await TrackingDeviceService.cancel_pairing_code(db, pairing_code)
    await db.commit()
    return {"message": "Código de emparejamiento cancelado correctamente."}

@router.get("/children/{child_code}", response_model=ChildTrackerResponse)
async def get_child_tracker(
    child_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_daycare_manager)
):
    """
    Consulta los detalles del rastreador asignado a un niño. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    child = await ChildRepository.get_by_code(db, child_code)
    if not child:
        raise NotFoundException(f"Niño con código '{child_code}' no encontrado.")
        
    await check_daycare_manager_permission(db, current_user, child.daycare_id)
    
    return await TrackingDeviceService.get_tracker_for_child(db, child_code)

@router.delete("/children/{child_code}", status_code=status.HTTP_200_OK)
async def decouple_tracker(
    child_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_daycare_manager)
):
    """
    Desvincula y desactiva el dispositivo rastreador de un niño. (Acceso: ADMIN, DAYCARE_MANAGER)
    """
    child = await ChildRepository.get_by_code(db, child_code)
    if not child:
        raise NotFoundException(f"Niño con código '{child_code}' no encontrado.")
        
    await check_daycare_manager_permission(db, current_user, child.daycare_id)
    
    await TrackingDeviceService.decouple_tracker_for_child(db, child_code)
    await db.commit()
    return {"message": "Dispositivo rastreador desvinculado y desactivado correctamente."}

@router.post("/pair", response_model=PairDeviceResponse, status_code=status.HTTP_200_OK)
async def pair_device(
    payload: PairDeviceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint público usado por la app rastreadora para emparejar un dispositivo.
    """
    response = await TrackingDeviceService.pair_device(
        db=db,
        pairing_code_str=payload.pairing_code,
        device_identifier=payload.device_identifier,
        platform=payload.platform
    )
    await db.commit()
    return response
