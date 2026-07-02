"""HTTP Router: Lead endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.application.dtos import (
    CreateLeadInput,
    GetLeadStatsInput,
    ListLeadsInput,
    SendProactiveMessageInput,
    UpdateLeadInput,
)
from app.application.lead.create_lead import CreateLeadUseCase
from app.application.lead.get_lead_stats import GetLeadStatsUseCase
from app.application.lead.list_leads import ListLeadsUseCase
from app.application.lead.send_message import SendProactiveMessageUseCase
from app.application.lead.update_lead import UpdateLeadUseCase
from app.application.dtos import CurrentClientOutput
from app.infrastructure.http.dependencies import get_current_client, get_lead_repo
from app.infrastructure.http.schemas import (
    LeadCreateRequest,
    LeadListResponse,
    LeadResponse,
    LeadStatsResponse,
    LeadUpdateRequest,
    SendMessageRequest,
)
from app.infrastructure.persistence.lead_repository import SupabaseLeadRepository

router = APIRouter()


# E1: POST / — create lead
@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(
    body: LeadCreateRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseLeadRepository = Depends(get_lead_repo),
):
    uc = CreateLeadUseCase(repo=repo)
    dto = CreateLeadInput(
        client_id=current_client.client_id,
        phone=body.phone,
        name=body.name,
        source=body.source,
    )
    output = await uc.execute(dto)
    return LeadResponse.model_validate(output, from_attributes=True)


# E2: GET / — list leads with filters
@router.get("", response_model=LeadListResponse)
async def list_leads(
    current_client: CurrentClientOutput = Depends(get_current_client),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: SupabaseLeadRepository = Depends(get_lead_repo),
):
    uc = ListLeadsUseCase(repo=repo)
    dto = ListLeadsInput(
        client_id=current_client.client_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    outputs, total = await uc.execute(dto)
    return LeadListResponse(
        items=[LeadResponse.model_validate(o, from_attributes=True) for o in outputs],
        total=total,
    )


# E3: GET /stats — lead statistics
@router.get("/stats", response_model=LeadStatsResponse)
async def get_lead_stats(
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseLeadRepository = Depends(get_lead_repo),
):
    uc = GetLeadStatsUseCase(repo=repo)
    dto = GetLeadStatsInput(client_id=current_client.client_id)
    return LeadStatsResponse.model_validate(await uc.execute(dto))


# E4: PATCH /{lead_id} — update lead
@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: str,
    body: LeadUpdateRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseLeadRepository = Depends(get_lead_repo),
):
    uc = UpdateLeadUseCase(repo=repo)
    dto = UpdateLeadInput(
        lead_id=lead_id,
        status=body.status,
        score=body.score,
        notes=body.notes,
        name=body.name,
    )
    output = await uc.execute(dto)
    return LeadResponse.model_validate(output, from_attributes=True)


# E5: POST /{lead_id}/send-message — send proactive message
@router.post("/{lead_id}/send-message", status_code=204)
async def send_message(
    lead_id: str,
    body: SendMessageRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseLeadRepository = Depends(get_lead_repo),
):
    uc = SendProactiveMessageUseCase(
        lead_repo=repo,
        message_sender=None,  # type: ignore[arg-type]
    )
    dto = SendProactiveMessageInput(
        lead_id=lead_id,
        message_text=body.message_text,
    )
    await uc.execute(dto)
