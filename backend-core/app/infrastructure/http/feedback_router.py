"""HTTP Router: Feedback endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.application.dtos import (
    CreateFeedbackInput,
    GetFeedbackStatsInput,
    ListFeedbackInput,
)
from app.application.feedback.create_feedback import CreateFeedbackUseCase
from app.application.feedback.get_feedback_stats import GetFeedbackStatsUseCase
from app.application.feedback.list_feedback import ListFeedbackUseCase
from app.application.dtos import CurrentClientOutput
from app.infrastructure.http.dependencies import get_current_client, get_feedback_repo
from app.infrastructure.http.schemas import (
    FeedbackCreateRequest,
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackStatsResponse,
)
from app.infrastructure.persistence.feedback_repository import SupabaseFeedbackRepository

router = APIRouter()


# E1: POST / — create feedback
@router.post("", response_model=FeedbackResponse, status_code=201)
async def create_feedback(
    body: FeedbackCreateRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseFeedbackRepository = Depends(get_feedback_repo),
):
    uc = CreateFeedbackUseCase(repo=repo)
    dto = CreateFeedbackInput(
        client_id=current_client.client_id,
        rating=body.rating,
        lead_id=body.lead_id,
        conversation_id=body.conversation_id,
        comment=body.comment,
    )
    output = await uc.execute(dto)
    return FeedbackResponse.model_validate(output, from_attributes=True)


# E2: GET / — list feedbacks
@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    current_client: CurrentClientOutput = Depends(get_current_client),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: SupabaseFeedbackRepository = Depends(get_feedback_repo),
):
    uc = ListFeedbackUseCase(repo=repo)
    dto = ListFeedbackInput(
        client_id=current_client.client_id,
        limit=limit,
        offset=offset,
    )
    outputs, total = await uc.execute(dto)
    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(o, from_attributes=True) for o in outputs],
        total=total,
    )


# E3: GET /stats — feedback statistics
@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseFeedbackRepository = Depends(get_feedback_repo),
):
    uc = GetFeedbackStatsUseCase(repo=repo)
    dto = GetFeedbackStatsInput(client_id=current_client.client_id)
    return FeedbackStatsResponse.model_validate(await uc.execute(dto))
