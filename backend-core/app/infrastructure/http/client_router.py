"""HTTP Router: Client endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.application.agent.create_agent import CreateAgentUseCase
from app.application.agent.list_agents import ListAgentsByClientUseCase
from app.application.client.create_client import CreateClientUseCase
from app.application.client.deactivate_client import DeactivateClientUseCase
from app.application.client.get_client import GetClientUseCase
from app.application.client.list_clients import ListClientsUseCase
from app.application.client.update_client import UpdateClientUseCase
from app.application.dtos import (
    AgentToolInput,
    CreateAgentInput,
    CreateClientInput,
    DeactivateClientInput,
    GetClientInput,
    ListAgentsByClientInput,
    ListClientsInput,
    UpdateClientInput,
)
from app.infrastructure.http.dependencies import get_agent_repo, get_client_repo
from app.infrastructure.http.schemas import (
    AgentCreateRequest,
    AgentListResponse,
    AgentResponse,
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
    agent_output_to_response,
)
from app.infrastructure.persistence.agent_repository import SupabaseAgentRepository
from app.infrastructure.persistence.client_repository import SupabaseClientRepository

router = APIRouter()


# E3/E4: GET / — search by whatsapp or list (must be registered before /{client_id})
@router.get("", response_model=None)
async def query_clients(
    whatsapp: str | None = Query(None, description="WhatsApp number to search"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repo: SupabaseClientRepository = Depends(get_client_repo),
):
    if whatsapp is not None:
        uc = GetClientUseCase(client_repo=repo)
        dto = GetClientInput(client_id=None, whatsapp=whatsapp)
        output = await uc.execute(dto)
        return ClientResponse.model_validate(output)

    uc = ListClientsUseCase(client_repo=repo)
    dto = ListClientsInput(limit=limit, offset=offset)
    outputs = await uc.execute(dto)
    return ClientListResponse(
        items=[ClientResponse.model_validate(o) for o in outputs],
        count=len(outputs),
    )


# E1: POST / — create client
@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    body: ClientCreateRequest,
    repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = CreateClientUseCase(client_repo=repo)
    dto = CreateClientInput(
        name=body.name,
        business_type=body.business_type,
        whatsapp_number=body.whatsapp_number,
    )
    output = await uc.execute(dto)
    return ClientResponse.model_validate(output)


# E2: GET /{client_id} — get client by id
@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = GetClientUseCase(client_repo=repo)
    dto = GetClientInput(client_id=client_id, whatsapp=None)
    return ClientResponse.model_validate(await uc.execute(dto))


# E5: PATCH /{client_id} — update client
@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    body: ClientUpdateRequest,
    repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = UpdateClientUseCase(client_repo=repo)
    dto = UpdateClientInput(
        client_id=client_id,
        name=body.name,
        whatsapp_number=body.whatsapp_number,
    )
    return ClientResponse.model_validate(await uc.execute(dto))


# E6: DELETE /{client_id} — deactivate client
@router.delete("/{client_id}", response_model=ClientResponse)
async def deactivate_client(
    client_id: str,
    repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = DeactivateClientUseCase(client_repo=repo)
    dto = DeactivateClientInput(client_id=client_id)
    return ClientResponse.model_validate(await uc.execute(dto))


# E7: POST /{client_id}/agents — create agent (more specific route, must precede /{client_id} for safety)
@router.post("/{client_id}/agents", response_model=AgentResponse, status_code=201)
async def create_agent(
    client_id: str,
    body: AgentCreateRequest,
    agent_repo: SupabaseAgentRepository = Depends(get_agent_repo),
    client_repo: SupabaseClientRepository = Depends(get_client_repo),
):
    uc = CreateAgentUseCase(agent_repo=agent_repo, client_repo=client_repo)
    dto = CreateAgentInput(
        client_id=client_id,
        name=body.name,
        personality=body.personality,
        tools=[
            AgentToolInput(name=t.name, description=t.description, endpoint=t.endpoint)
            for t in body.tools
        ],
        knowledge_base_refs=body.knowledge_base_refs,
    )
    return agent_output_to_response(await uc.execute(dto))


# E9: GET /{client_id}/agents — list agents by client
@router.get("/{client_id}/agents", response_model=AgentListResponse)
async def list_agents_by_client(
    client_id: str,
    repo: SupabaseAgentRepository = Depends(get_agent_repo),
):
    uc = ListAgentsByClientUseCase(agent_repo=repo)
    dto = ListAgentsByClientInput(client_id=client_id)
    outputs = await uc.execute(dto)
    return AgentListResponse(
        items=[agent_output_to_response(o) for o in outputs],
        count=len(outputs),
    )
