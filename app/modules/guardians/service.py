import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ConflictException, BadRequestException, ForbiddenException
from app.core.constants import AlertStatus, AlertType
from app.modules.guardians.repository import GuardianRepository
from app.modules.daycares.repository import DaycareRepository
from app.modules.children.repository import ChildRepository
from app.modules.guardians.schemas import (
    GuardianCreate, GuardianResponse, LinkedDaycareResponse,
    LinkedChildResponse, LocationSchema, MonitoringSummaryResponse, MonitoringChildSummary
)

class GuardianService:
    @staticmethod
    async def create_guardian(db: AsyncSession, guardian_in: GuardianCreate) -> GuardianResponse:
        """Crea un perfil de tutor."""
        guardian = await GuardianRepository.create(db, guardian_in)
        return GuardianResponse.model_validate(guardian)

    @staticmethod
    async def link_daycare_by_code(db: AsyncSession, guardian_id: uuid.UUID, daycare_code: str) -> None:
        """
        Vincula una guardería a un tutor.
        Valida que exista la guardería y que no esté ya vinculada.
        """
        # Validar existencia de la guardería
        daycare = await DaycareRepository.get_by_code(db, daycare_code)
        if not daycare:
            raise NotFoundException(f"Guardería con código '{daycare_code}' no encontrada.")

        # Validar existencia del tutor
        guardian = await GuardianRepository.get_by_id(db, guardian_id)
        if not guardian:
            raise NotFoundException(f"Tutor con ID '{guardian_id}' no encontrado.")

        # Validar si ya está vinculada
        existing_link = await GuardianRepository.get_daycare_link(db, guardian_id, daycare.id)
        if existing_link:
            raise ConflictException(f"La guardería '{daycare_code}' ya está vinculada a este tutor.")

        await GuardianRepository.link_daycare(db, guardian_id, daycare.id)

    @staticmethod
    async def link_child_by_code(
        db: AsyncSession,
        guardian_id: uuid.UUID,
        daycare_code: str,
        child_code: str,
        relationship: str
    ) -> None:
        """
        Vincula un niño con un tutor.
        Validaciones:
        - La guardería debe existir.
        - El niño debe existir.
        - El niño debe pertenecer a esa guardería.
        - El tutor debe estar vinculado a la guardería.
        - No debe estar ya vinculado con ese niño.
        """
        daycare = await DaycareRepository.get_by_code(db, daycare_code)
        if not daycare:
            raise NotFoundException(f"Guardería con código '{daycare_code}' no encontrada.")

        child = await ChildRepository.get_by_code(db, child_code)
        if not child:
            raise NotFoundException(f"Niño con código '{child_code}' no encontrado.")

        # Validar pertenencia a la guardería
        if child.daycare_id != daycare.id:
            raise BadRequestException(
                f"El niño '{child_code}' no pertenece a la guardería '{daycare_code}'."
            )

        # El tutor debe estar vinculado a la guardería
        daycare_link = await GuardianRepository.get_daycare_link(db, guardian_id, daycare.id)
        if not daycare_link:
            raise ForbiddenException(
                f"El tutor debe estar vinculado a la guardería '{daycare_code}' antes de vincular un niño."
            )

        # No debe estar vinculado previamente con ese niño
        child_link = await GuardianRepository.get_child_link(db, guardian_id, child.id)
        if child_link:
            raise ConflictException(f"El niño '{child_code}' ya está vinculado a este tutor.")

        await GuardianRepository.link_child(db, guardian_id, child.id, relationship)

    @staticmethod
    async def list_linked_daycares(db: AsyncSession, guardian_id: uuid.UUID) -> list[LinkedDaycareResponse]:
        """Obtiene la lista de guarderías vinculadas al tutor."""
        daycares = await GuardianRepository.get_linked_daycares(db, guardian_id)
        return [LinkedDaycareResponse.model_validate(d) for d in daycares]

    @classmethod
    async def list_linked_children(db: AsyncSession, guardian_id: uuid.UUID) -> list[LinkedChildResponse]:
        """Obtiene la lista de niños vinculados con su última ubicación y estado de alerta."""
        links = await GuardianRepository.get_linked_children_with_relations(db, guardian_id)
        
        response_list = []
        for link in links:
            child = link.child
            daycare = child.daycare
            current_loc = child.current_location

            # Calcular si tiene alerta activa (tipo OUT_OF_AREA y estado NEW o VIEWED)
            has_alert = any(
                a.alert_type == AlertType.OUT_OF_AREA and a.status in (AlertStatus.NEW, AlertStatus.VIEWED)
                for a in child.alerts
            )

            location_dto = None
            if current_loc:
                location_dto = LocationSchema(
                    latitude=current_loc.latitude,
                    longitude=current_loc.longitude,
                    accuracy=current_loc.accuracy,
                    is_inside_area=current_loc.is_inside_area,
                    received_at=current_loc.received_at
                )

            response_list.append(
                LinkedChildResponse(
                    id=child.id,
                    code=child.code,
                    full_name=child.full_name,
                    age=child.age,
                    status=child.status,
                    relationship=link.relationship,
                    daycare_code=daycare.code,
                    daycare_name=daycare.name,
                    has_active_alert=has_alert,
                    last_location=location_dto
                )
            )
        return response_list

    @classmethod
    async def get_monitoring_summary(db: AsyncSession, guardian_id: uuid.UUID) -> MonitoringSummaryResponse:
        """
        Obtiene el resumen de monitoreo en tiempo real de todos los niños de un tutor.
        """
        links = await GuardianRepository.get_linked_children_with_relations(db, guardian_id)
        
        children_summaries = []
        active_alerts_count = 0

        for link in links:
            child = link.child
            daycare = child.daycare
            current_loc = child.current_location

            # Validar alertas activas
            has_alert = any(
                a.alert_type == AlertType.OUT_OF_AREA and a.status in (AlertStatus.NEW, AlertStatus.VIEWED)
                for a in child.alerts
            )
            if has_alert:
                active_alerts_count += 1

            # Determinar estado de monitoreo
            if not current_loc:
                monitoring_status = "NO_LOCATION"
            elif not current_loc.is_inside_area:
                monitoring_status = "OUTSIDE_AREA"
            else:
                monitoring_status = "INSIDE_AREA"

            children_summaries.append(
                MonitoringChildSummary(
                    child_code=child.code,
                    child_name=child.full_name,
                    daycare_code=daycare.code,
                    daycare_name=daycare.name,
                    monitoring_status=monitoring_status,
                    has_active_alert=has_alert,
                    last_location_at=current_loc.received_at if current_loc else None
                )
            )

        return MonitoringSummaryResponse(
            total_children=len(links),
            active_alerts=active_alerts_count,
            children=children_summaries
        )
