"""HTTP Router: Appointment endpoints (agenda del negocio).

Scoped por tenant. client_admin: siempre JWT. superadmin: puede pasar
``client_id`` en query para listar / operar sobre otro negocio.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
from app.application.shared.tenant_scope import (
    TenantScopeError,
    resolve_list_client_id,
)
from app.infrastructure.http.dependencies import (
    get_appointment_repo,
    get_client_repo,
    get_current_client,
    get_lead_repo,
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
from app.infrastructure.persistence.lead_repository import SupabaseLeadRepository

router = APIRouter()


def _resolve_tenant(
    current: CurrentClientOutput, requested: str | None
) -> str:
    try:
        return resolve_list_client_id(current.role, current.client_id, requested)
    except TenantScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


# E1: POST / — create appointment
@router.post("", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    body: AppointmentCreateRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    client_id: str | None = Query(
        None, description="Tenant (superadmin); ignorado para client_admin"
    ),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
    lead_repo: SupabaseLeadRepository = Depends(get_lead_repo),
):
    tenant = _resolve_tenant(current_client, client_id)
    uc = CreateAppointmentUseCase(
        repo=repo, schedule_repo=client_repo, lead_repo=lead_repo
    )
    dto = CreateAppointmentInput(
        client_id=tenant,
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
    client_id: str | None = Query(
        None, description="Tenant (superadmin); ignorado para client_admin"
    ),
    date_from: str | None = Query(None, description="Desde (YYYY-MM-DD o ISO datetime)"),
    date_to: str | None = Query(None, description="Hasta (YYYY-MM-DD o ISO datetime)"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
):
    tenant = _resolve_tenant(current_client, client_id)
    uc = ListAppointmentsUseCase(repo=repo, schedule_repo=client_repo)
    dto = ListAppointmentsInput(
        client_id=tenant,
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
    client_id: str | None = Query(
        None, description="Tenant (superadmin); ignorado para client_admin"
    ),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
):
    tenant = _resolve_tenant(current_client, client_id)
    uc = GetAvailabilityUseCase(repo=repo, schedule_repo=client_repo)
    dto = GetAvailabilityInput(client_id=tenant, date=date)
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
    client_id: str | None = Query(
        None, description="Tenant (superadmin); ignorado para client_admin"
    ),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
):
    tenant = _resolve_tenant(current_client, client_id)
    uc = RescheduleAppointmentUseCase(repo=repo, schedule_repo=client_repo)
    dto = RescheduleAppointmentInput(
        client_id=tenant,
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
    client_id: str | None = Query(
        None, description="Tenant (superadmin); ignorado para client_admin"
    ),
    repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
):
    tenant = _resolve_tenant(current_client, client_id)
    uc = CancelAppointmentUseCase(repo=repo)
    dto = CancelAppointmentInput(
        client_id=tenant,
        appointment_id=appointment_id,
    )
    output = await uc.execute(dto)
    return AppointmentResponse.model_validate(output, from_attributes=True)
