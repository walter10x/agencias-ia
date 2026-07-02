"""HTTP Router: Email marketing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.application.dtos import (
    GetEmailStatsInput,
    ListEmailsInput,
    SendEmailInput,
)
from app.application.email.get_email_stats import GetEmailStatsUseCase
from app.application.email.send_email import SendEmailUseCase
from app.application.dtos import CurrentClientOutput
from app.infrastructure.http.dependencies import get_current_client, get_email_repo
from app.infrastructure.http.schemas import (
    EmailLogResponse,
    EmailListResponse,
    EmailSendRequest,
    EmailSendResponse,
    EmailStatsResponse,
)
from app.infrastructure.persistence.email_repository import SupabaseEmailRepository

router = APIRouter()


@router.post("/send", response_model=EmailSendResponse, status_code=201)
async def send_email(
    body: EmailSendRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseEmailRepository = Depends(get_email_repo),
):
    uc = SendEmailUseCase(repo=repo)
    dto = SendEmailInput(
        client_id=current_client.client_id,
        to_email=body.to_email,
        rubro_slug=body.rubro_slug,
        sequence_number=body.sequence_number,
        lead_id=body.lead_id,
        business_name=body.business_name,
        contact_name=body.contact_name,
    )
    output = await uc.execute(dto)
    return EmailSendResponse.model_validate(output)


@router.get("", response_model=EmailListResponse)
async def list_emails(
    current_client: CurrentClientOutput = Depends(get_current_client),
    lead_id: str | None = Query(None, description="Filter by lead UUID"),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: SupabaseEmailRepository = Depends(get_email_repo),
):
    dto = ListEmailsInput(
        client_id=current_client.client_id,
        lead_id=lead_id,
        limit=limit,
        offset=offset,
    )
    logs = await repo.list_by_client(
        client_id=dto.client_id,
        lead_id=dto.lead_id,
        limit=dto.limit,
        offset=dto.offset,
    )
    from app.application.dtos import email_log_to_output
    return EmailListResponse(
        items=[EmailLogResponse.model_validate(email_log_to_output(log)) for log in logs],
        total=len(logs),
    )


@router.get("/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseEmailRepository = Depends(get_email_repo),
):
    uc = GetEmailStatsUseCase(repo=repo)
    dto = GetEmailStatsInput(client_id=current_client.client_id)
    return EmailStatsResponse.model_validate(await uc.execute(dto))


@router.get("/templates", response_model=dict)
async def list_email_templates():
    """Retorna los rubros con plantillas de email disponibles."""
    from app.domain.email.templates import get_all_rubro_slugs
    return {"rubros": get_all_rubro_slugs()}
