"""HTTP Router: Conversation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.conversation.get_conversation_messages import (
    GetConversationMessagesUseCase,
)
from app.application.conversation.get_conversation_stats import (
    GetConversationStatsUseCase,
)
from app.application.conversation.list_conversations import ListConversationsUseCase
from app.application.dtos import (
    CurrentClientOutput,
    GetConversationMessagesInput,
    ListConversationsInput,
)
from app.application.shared.tenant_scope import (
    TenantScopeError,
    resolve_list_client_id,
)
from app.infrastructure.http.dependencies import get_conversation_repo, get_current_client
from app.infrastructure.http.schemas import (
    ConversationListResponse,
    ConversationMessagesResponse,
    ConversationResponse,
    ConversationStatsResponse,
    MessageResponse,
)
from app.infrastructure.persistence.conversation_repository import (
    SupabaseConversationRepository,
)

router = APIRouter()


# E1: GET / — list conversations by client
@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    current_client: CurrentClientOutput = Depends(get_current_client),
    client_id: str | None = Query(
        None,
        description="Tenant a listar (obligatorio para superadmin; ignorado para client_admin)",
    ),
    limit: int = Query(20, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: SupabaseConversationRepository = Depends(get_conversation_repo),
):
    try:
        resolved = resolve_list_client_id(
            current_client.role, current_client.client_id, client_id
        )
    except TenantScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    uc = ListConversationsUseCase(repo=repo)
    dto = ListConversationsInput(
        client_id=resolved, limit=limit, offset=offset,
    )
    outputs, total = await uc.execute(dto)
    return ConversationListResponse(
        items=[ConversationResponse.model_validate(o) for o in outputs],
        count=total,
    )


# E2: GET /{conversation_id}/messages — get messages for a conversation
@router.get("/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    conversation_id: str,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseConversationRepository = Depends(get_conversation_repo),
):
    uc = GetConversationMessagesUseCase(repo=repo)
    dto = GetConversationMessagesInput(conversation_id=conversation_id)
    messages, phone_number, status = await uc.execute(dto)
    return ConversationMessagesResponse(
        phone_number=phone_number,
        status=status,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


# E3: GET /stats — conversation statistics by tenant
@router.get("/stats", response_model=ConversationStatsResponse)
async def get_conversation_stats(
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseConversationRepository = Depends(get_conversation_repo),
):
    uc = GetConversationStatsUseCase(repo=repo)
    output = await uc.execute()
    return ConversationStatsResponse(
        total_conversations=output.total_conversations,
        active_conversations=output.active_conversations,
        messages_today=output.messages_today,
        clients_with_conversations=output.clients_with_conversations,
    )
