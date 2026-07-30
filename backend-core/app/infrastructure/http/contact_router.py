"""HTTP Router: Contactos CRM (agregación + notas)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.contact.get_contact import (
    GetContactInput,
    GetContactUseCase,
    ListContactsInput,
    ListContactsUseCase,
)
from app.application.contact.update_contact_notes import (
    UpdateContactNotesInput,
    UpdateContactNotesUseCase,
)
from app.application.dtos import CurrentClientOutput
from app.domain.shared.errors import InvalidLeadError
from app.infrastructure.http.dependencies import (
    get_appointment_repo,
    get_conversation_repo,
    get_current_client,
    get_lead_repo,
)
from app.infrastructure.http.schemas import (
    ContactAppointmentSnippetResponse,
    ContactConversationSnippetResponse,
    ContactDetailResponse,
    ContactLeadSnippetResponse,
    ContactListResponse,
    ContactNotesUpdateRequest,
    ContactSummaryResponse,
)
from app.infrastructure.persistence.appointment_repository import SupabaseAppointmentRepository
from app.infrastructure.persistence.conversation_repository import SupabaseConversationRepository
from app.infrastructure.persistence.lead_repository import SupabaseLeadRepository

router = APIRouter()


def _detail_to_response(detail) -> ContactDetailResponse:
    return ContactDetailResponse(
        client_id=detail.client_id,
        phone=detail.phone,
        display_name=detail.display_name,
        lead=(
            ContactLeadSnippetResponse(
                id=detail.lead.id,
                status=detail.lead.status,
                score=detail.lead.score,
                notes=detail.lead.notes,
                name=detail.lead.name,
            )
            if detail.lead
            else None
        ),
        conversations=[
            ContactConversationSnippetResponse(
                id=c.id, status=c.status, updated_at=c.updated_at
            )
            for c in detail.conversations
        ],
        appointments=[
            ContactAppointmentSnippetResponse(
                id=a.id,
                starts_at=a.starts_at,
                status=a.status,
                contact_name=a.contact_name,
            )
            for a in detail.appointments
        ],
        last_activity_at=detail.last_activity_at,
    )


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    current_client: CurrentClientOutput = Depends(get_current_client),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    lead_repo: SupabaseLeadRepository = Depends(get_lead_repo),
    conversation_repo: SupabaseConversationRepository = Depends(get_conversation_repo),
    appointment_repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
):
    uc = ListContactsUseCase(lead_repo, conversation_repo, appointment_repo)
    items, total = await uc.execute(
        ListContactsInput(
            client_id=current_client.client_id,
            limit=limit,
            offset=offset,
        )
    )
    return ContactListResponse(
        items=[
            ContactSummaryResponse(
                phone=i.phone,
                display_name=i.display_name,
                lead_status=i.lead_status,
                last_activity_at=i.last_activity_at,
                has_conversation=i.has_conversation,
                has_appointments=i.has_appointments,
            )
            for i in items
        ],
        total=total,
    )


@router.get("/by-phone/{phone}", response_model=ContactDetailResponse)
async def get_contact_by_phone(
    phone: str,
    current_client: CurrentClientOutput = Depends(get_current_client),
    lead_repo: SupabaseLeadRepository = Depends(get_lead_repo),
    conversation_repo: SupabaseConversationRepository = Depends(get_conversation_repo),
    appointment_repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
):
    uc = GetContactUseCase(lead_repo, conversation_repo, appointment_repo)
    detail = await uc.execute(
        GetContactInput(client_id=current_client.client_id, phone=phone)
    )
    return _detail_to_response(detail)


@router.patch("/by-phone/{phone}/notes", response_model=ContactDetailResponse)
async def update_contact_notes(
    phone: str,
    body: ContactNotesUpdateRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    lead_repo: SupabaseLeadRepository = Depends(get_lead_repo),
    conversation_repo: SupabaseConversationRepository = Depends(get_conversation_repo),
    appointment_repo: SupabaseAppointmentRepository = Depends(get_appointment_repo),
):
    get_uc = GetContactUseCase(lead_repo, conversation_repo, appointment_repo)
    uc = UpdateContactNotesUseCase(lead_repo, get_uc)
    try:
        detail = await uc.execute(
            UpdateContactNotesInput(
                client_id=current_client.client_id,
                phone=phone,
                notes=body.notes,
                display_name=body.display_name,
            )
        )
    except InvalidLeadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _detail_to_response(detail)
