"""HTTP Router: Client endpoints (CRUD + Admin approve/reject/disconnect)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.auth.approve_client import ApproveClientUseCase
from app.application.auth.connect_whatsapp import ConnectWhatsappUseCase
from app.application.auth.disconnect_whatsapp import DisconnectWhatsappUseCase
from app.application.auth.reject_client import RejectClientUseCase
from app.application.agent.create_agent import CreateAgentUseCase
from app.application.agent.list_agents import ListAgentsByClientUseCase
from app.application.client.create_client import CreateClientUseCase
from app.application.client.deactivate_client import DeactivateClientUseCase
from app.application.client.get_client import GetClientUseCase
from app.application.client.list_clients import ListClientsUseCase
from app.application.client.update_client import UpdateClientUseCase
from app.application.dtos import (
    AdminClientOutput,
    AgentToolInput,
    ApproveClientInput,
    ConnectWhatsappInput,
    CreateAgentInput,
    CreateClientInput,
    CurrentClientOutput,
    DeactivateClientInput,
    DisconnectWhatsappInput,
    GetClientInput,
    ListAgentsByClientInput,
    ListClientsInput,
    RejectClientInput,
    UpdateClientInput,
)
from app.domain.shared.errors import ForbiddenError, InvalidClientError
from app.infrastructure.http.dependencies import (
    get_agent_repo,
    get_client_repo,
    require_superadmin,
)
from app.infrastructure.http.schemas import (
    AdminClientResponse,
    AgentCreateRequest,
    AgentListResponse,
    AgentResponse,
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
    ConnectWhatsappRequest,
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


# ============================================================================
# Admin endpoints (require superadmin)
# ============================================================================


def _admin_output_to_response(output: AdminClientOutput) -> AdminClientResponse:
    return AdminClientResponse(
        id=output.id,
        email=output.email,
        name=output.name,
        role=output.role,
        status=output.status,
        is_active=output.is_active,
        whatsapp_number=output.whatsapp_number,
        whatsapp_connected=output.whatsapp_connected,
        plan=output.plan,
        created_at=output.created_at,
        updated_at=output.updated_at,
    )


@router.post("/{client_id}/approve", response_model=AdminClientResponse)
async def approve_client(
    client_id: str,
    current: CurrentClientOutput = Depends(require_superadmin),
    repo: SupabaseClientRepository = Depends(get_client_repo),
) -> AdminClientResponse:
    uc = ApproveClientUseCase(repo)
    inp = ApproveClientInput(client_id=client_id)
    try:
        output = await uc.execute(inp, current_role=current.role)
    except InvalidClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _admin_output_to_response(output)


@router.post("/{client_id}/reject", response_model=AdminClientResponse)
async def reject_client(
    client_id: str,
    current: CurrentClientOutput = Depends(require_superadmin),
    repo: SupabaseClientRepository = Depends(get_client_repo),
) -> AdminClientResponse:
    uc = RejectClientUseCase(repo)
    inp = RejectClientInput(client_id=client_id)
    try:
        output = await uc.execute(inp, current_role=current.role)
    except InvalidClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _admin_output_to_response(output)


@router.post("/{client_id}/disconnect-whatsapp", response_model=AdminClientResponse)
async def disconnect_whatsapp(
    client_id: str,
    current: CurrentClientOutput = Depends(require_superadmin),
    repo: SupabaseClientRepository = Depends(get_client_repo),
) -> AdminClientResponse:
    uc = DisconnectWhatsappUseCase(repo)
    inp = DisconnectWhatsappInput(client_id=client_id)
    try:
        output = await uc.execute(inp, current_role=current.role)
    except InvalidClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _admin_output_to_response(output)


@router.post("/{client_id}/connect-whatsapp", response_model=AdminClientResponse)
async def connect_whatsapp(
    client_id: str,
    body: ConnectWhatsappRequest,
    current: CurrentClientOutput = Depends(require_superadmin),
    repo: SupabaseClientRepository = Depends(get_client_repo),
) -> AdminClientResponse:
    """Conecta el número de WhatsApp Cloud API de un tenant (Fase 3.1).

    NO valida el token contra la API de Meta (sin salida de red en
    sandbox/CI); el token se cifra antes de persistirse.
    """
    uc = ConnectWhatsappUseCase(repo)
    inp = ConnectWhatsappInput(
        client_id=client_id,
        phone_number_id=body.phone_number_id,
        access_token=body.access_token,
    )
    try:
        output = await uc.execute(inp, current_role=current.role)
    except InvalidClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return _admin_output_to_response(output)
