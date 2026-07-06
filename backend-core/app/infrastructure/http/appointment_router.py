"""HTTP Router: Appointment endpoints (agenda del negocio).

Todos los endpoints están scoped por tenant: el client_id sale del JWT
(get_current_client), nunca del body/query, de modo que un cliente no
puede ver ni tocar citas de otro.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.application.appointment.cancel_appointment import CancelAppointmentUseCase
from app.application.appointment.create_appointment import CreateAppointmentUseCase
from app.application.appointment.get_availability import GetAvailabilityUseCase
from app.application.appointment.list_appointments import ListAppointmentsUseCase
from app.application.appointment.reschedule_appointment import (
    RescheduleAppointmentUseCase,
)
from app.application.dtos import (
    CancelAppointmentInput,
    CreateAppointmentInput,
    CurrentClientOutput,
    GetAvailabilityInput,
    ListAppointmentsInput,
    RescheduleAppointmentInput,
)
from app.infrastructure.http.dependencies import (
    get_appointment_repo,
    get_client_repo,
    get_current_client,
)
from app.infrastructure.http.schemas import (
    AppointmentCreateRequest,
    AppointmentListResponse,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    AvailabilityResponse,
    AvailabilitySlotResponse,
)
from app.infrastructure.persistence.appointment_repository import (
    SupabaseAppointmentRepository,
)
from app.infrastructure.persistence.client_repository import SupabaseClientRepository

router = APIRouter()


# E1: POST / — create appointment
@router.post("", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    body: AppointmentCreateRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = CreateAppointmentUseCase(repo=repo, schedule_repo=client_repo)
    dto = CreateAppointmentInput(
        client_id=current_client.client_id,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        contact_phone=body.contact_phone,
        contact_name=body.contact_name,
        notes=body.notes,
        conversation_id=body.conversation_id,
    )
    output = await uc.execute(dto)
    return AppointmentResponse.model_validate(output, from_attributes=True)


# E2: GET / — list appointments with filters
@router.get("", response_model=AppointmentListResponse)
async def list_appointments(
    current_client: CurrentClientOutput = Depends(get_current_client),
    date_from: str | None = Query(None, description="Desde (YYYY-MM-DD o ISO datetime)"),
    date_to: str | None = Query(None, description="Hasta (YYYY-MM-DD o ISO datetime)"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = ListAppointmentsUseCase(repo=repo, schedule_repo=client_repo)
    dto = ListAppointmentsInput(
        client_id=current_client.client_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        limit=limit,
        offset=offset,
    )
    outputs, total = await uc.execute(dto)
    return AppointmentListResponse(
        items=[
            AppointmentResponse.model_validate(o, from_attributes=True)
            for o in outputs
        ],
        total=total,
    )


# E3: GET /availability — free slots for a day
@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    date: str = Query(..., description="Día a consultar (YYYY-MM-DD)"),
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = GetAvailabilityUseCase(repo=repo, schedule_repo=client_repo)
    dto = GetAvailabilityInput(client_id=current_client.client_id, date=date)
    output = await uc.execute(dto)
    return AvailabilityResponse(
        date=output.date,
        timezone=output.timezone,
        slot_duration_minutes=output.slot_duration_minutes,
        slots=[
            AvailabilitySlotResponse(
                starts_at=s.starts_at, ends_at=s.ends_at, label=s.label
            )
            for s in output.slots
        ],
    )


# E4: PATCH /{appointment_id} — reschedule
@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: str,
    body: AppointmentRescheduleRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = RescheduleAppointmentUseCase(repo=repo, schedule_repo=client_repo)
    dto = RescheduleAppointmentInput(
        client_id=current_client.client_id,
        appointment_id=appointment_id,
        new_starts_at=body.starts_at,
        new_ends_at=body.ends_at,
    )
    output = await uc.execute(dto)
    return AppointmentResponse.model_validate(output, from_attributes=True)


# E5: DELETE /{appointment_id} — cancel (soft: status=cancelled)
@router.delete("/{appointment_id}", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: str,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
):
    uc = CancelAppointmentUseCase(repo=repo)
    dto = CancelAppointmentInput(
        client_id=current_client.client_id,
        appointment_id=appointment_id,
    )
    output = await uc.execute(dto)
    return AppointmentResponse.model_validate(output, from_attributes=True)
