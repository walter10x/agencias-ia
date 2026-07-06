"""HTTP Router: Agent endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.agent.deactivate_agent import DeactivateAgentUseCase
from app.application.agent.delete_agent import DeleteAgentUseCase
from app.application.agent.get_agent import GetAgentUseCase
from app.application.agent.update_agent import UpdateAgentUseCase
from app.application.dtos import (
    AgentToolInput,
    DeactivateAgentInput,
    DeleteAgentInput,
    GetAgentInput,
    UpdateAgentInput,
)
from app.application.dtos import CurrentClientOutput
from app.infrastructure.http.dependencies import get_agent_repo, get_current_client, superadmin_or_own_client
from app.infrastructure.http.schemas import (
    AgentResponse,
    AgentUpdateRequest,
    agent_output_to_response,
)
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository

router = APIRouter()


# E12: DELETE /{agent_id}/permanent — must be registered before /{agent_id}
@router.delete("/{agent_id}/permanent", status_code=204)
async def delete_agent(
    agent_id: str,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseAgentRepository = Depends(get_agent_repo),
):
    uc = DeleteAgentUseCase(agent_repo=repo)
    dto = DeleteAgentInput(agent_id=agent_id)
    await uc.execute(dto, client_id=superadmin_or_own_client(current_client))
    return None


# E11: DELETE /{agent_id} — deactivate agent
@router.delete("/{agent_id}", response_model=AgentResponse)
async def deactivate_agent(
    agent_id: str,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseAgentRepository = Depends(get_agent_repo),
):
    uc = DeactivateAgentUseCase(agent_repo=repo)
    dto = DeactivateAgentInput(agent_id=agent_id)
    return agent_output_to_response(await uc.execute(dto, client_id=superadmin_or_own_client(current_client)))


# E8: GET /{agent_id} — get agent by id
@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseAgentRepository = Depends(get_agent_repo),
):
    uc = GetAgentUseCase(agent_repo=repo)
    dto = GetAgentInput(agent_id=agent_id)
    return agent_output_to_response(await uc.execute(dto, client_id=superadmin_or_own_client(current_client)))


# E10: PATCH /{agent_id} — update agent
@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: AgentUpdateRequest,
    current_client: CurrentClientOutput = Depends(get_current_client),
    repo: SupabaseAgentRepository = Depends(get_agent_repo),
):
    uc = UpdateAgentUseCase(agent_repo=repo)
    dto = UpdateAgentInput(
        agent_id=agent_id,
        name=body.name,
        personality=body.personality,
        tools=(
            [
                AgentToolInput(name=t.name, description=t.description, endpoint=t.endpoint)
                for t in body.tools
            ]
            if body.tools is not None
            else None
        ),
        knowledge_base_refs=body.knowledge_base_refs,
    )
    return agent_output_to_response(await uc.execute(dto, client_id=superadmin_or_own_client(current_client)))
