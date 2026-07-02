"""DTOs de entrada/salida para la capa de aplicación.

Dataclasses inmutables que definen los contratos entre
los driver adapters (HTTP, CLI) y los use cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.agent.entity import Agent
from app.domain.client.entity import Client
from app.domain.conversation.entity import Conversation, Message


# ============================================================================
# Input DTOs — Client
# ============================================================================


@dataclass(frozen=True, slots=True)
class CreateClientInput:
    name: str
    business_type: str
    whatsapp_number: str


@dataclass(frozen=True, slots=True)
class GetClientInput:
    client_id: str | None = None
    whatsapp: str | None = None

    def __post_init__(self) -> None:
        if not self.client_id and not self.whatsapp:
            raise ValueError("Must provide client_id or whatsapp")


@dataclass(frozen=True, slots=True)
class ListClientsInput:
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class DeactivateClientInput:
    client_id: str


@dataclass(frozen=True, slots=True)
class UpdateClientInput:
    client_id: str
    name: str | None = None
    whatsapp_number: str | None = None

    def __post_init__(self) -> None:
        if self.name is None and self.whatsapp_number is None:
            raise ValueError("Must provide at least one field to update")


# ============================================================================
# Input DTOs — Agent
# ============================================================================


@dataclass(frozen=True, slots=True)
class AgentToolInput:
    name: str
    description: str
    endpoint: str = ""


@dataclass(frozen=True, slots=True)
class CreateAgentInput:
    client_id: str
    name: str
    personality: str
    tools: list[AgentToolInput] = field(default_factory=list)
    knowledge_base_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class GetAgentInput:
    agent_id: str


@dataclass(frozen=True, slots=True)
class ListAgentsByClientInput:
    client_id: str


@dataclass(frozen=True, slots=True)
class UpdateAgentInput:
    agent_id: str
    name: str | None = None
    personality: str | None = None
    tools: list[AgentToolInput] | None = None
    knowledge_base_refs: list[str] | None = None

    def __post_init__(self) -> None:
        fields = (self.name, self.personality, self.tools, self.knowledge_base_refs)
        if all(f is None for f in fields):
            raise ValueError("Must provide at least one field to update")


@dataclass(frozen=True, slots=True)
class DeactivateAgentInput:
    agent_id: str


@dataclass(frozen=True, slots=True)
class DeleteAgentInput:
    agent_id: str


# ============================================================================
# Output DTOs
# ============================================================================


@dataclass(frozen=True, slots=True)
class ClientOutput:
    id: str
    name: str
    business_type: str
    whatsapp_number: str
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class AgentToolOutput:
    name: str
    description: str
    endpoint: str


@dataclass(frozen=True, slots=True)
class AgentOutput:
    id: str
    client_id: str
    name: str
    personality: str
    tools: list[AgentToolOutput]
    knowledge_base_refs: list[str]
    is_active: bool
    created_at: str
    updated_at: str


# ============================================================================
# Mapper functions
# ============================================================================


def client_to_output(client: Client) -> ClientOutput:
    """Map a Client entity to ClientOutput DTO."""
    return ClientOutput(
        id=str(client.id),
        name=client.name,
        business_type=str(client.business_type),
        whatsapp_number=str(client.whatsapp_number),
        is_active=client.is_active,
        created_at=client.created_at.isoformat(),
        updated_at=client.updated_at.isoformat(),
    )


def client_to_admin_output(client: Client) -> AdminClientOutput:
    """Map a Client entity to AdminClientOutput DTO."""
    return AdminClientOutput(
        id=str(client.id),
        email=str(client.email) if client.email else "",
        name=client.name,
        role=client.role.value,
        status=client.status.value,
        is_active=client.is_active,
        whatsapp_number=str(client.whatsapp_number),
        whatsapp_connected=client.whatsapp_connected,
        plan=client.plan,
        created_at=client.created_at.isoformat(),
        updated_at=client.updated_at.isoformat(),
    )


def agent_to_output(agent: Agent) -> AgentOutput:
    """Map an Agent entity to AgentOutput DTO."""
    return AgentOutput(
        id=str(agent.id),
        client_id=str(agent.client_id),
        name=agent.name,
        personality=agent.personality,
        tools=[
            AgentToolOutput(name=t.name, description=t.description, endpoint=t.endpoint)
            for t in agent.tools
        ],
        knowledge_base_refs=list(agent.knowledge_base_refs),
        is_active=agent.is_active,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat(),
    )


# ============================================================================
# Input DTOs — Conversation
# ============================================================================


@dataclass(frozen=True, slots=True)
class ListConversationsInput:
    client_id: str
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class GetConversationMessagesInput:
    conversation_id: str


@dataclass(frozen=True, slots=True)
class GetConversationStatsInput:
    pass  # No input needed


# ============================================================================
# Output DTOs — Conversation
# ============================================================================


# ============================================================================
# Template DTOs
# ============================================================================


@dataclass(frozen=True, slots=True)
class TemplateItemOutput:
    """DTO ligero para listar plantillas."""
    slug: str
    name: str
    emoji: str
    description: str
    tools_count: int


@dataclass(frozen=True, slots=True)
class ApplyTemplateInput:
    """Input para aplicar una plantilla."""
    slug: str
    name: str
    whatsapp_number: str


@dataclass(frozen=True, slots=True)
class ApplyTemplateOutput:
    """Output después de aplicar una plantilla."""
    template_slug: str
    client: ClientOutput
    agent: AgentOutput
    message: str


# ============================================================================
# Output DTOs — Conversation
# ============================================================================


@dataclass(frozen=True, slots=True)
class ConversationOutput:
    id: str
    client_id: str
    agent_id: str | None
    wa_phone_number: str
    status: str
    last_message: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class MessageOutput:
    id: str
    conversation_id: str
    role: str
    content: str
    tokens_used: int
    created_at: str


@dataclass(frozen=True, slots=True)
class ConversationStatsOutput:
    total_conversations: int
    active_conversations: int
    messages_today: int
    clients_with_conversations: int


# ============================================================================
# Mapper functions — Conversation
# ============================================================================


def conversation_to_output(conv: Conversation) -> ConversationOutput:
    """Map a Conversation entity to ConversationOutput DTO."""
    return ConversationOutput(
        id=str(conv.id),
        client_id=str(conv.client_id),
        agent_id=str(conv.agent_id) if conv.agent_id else None,
        wa_phone_number=conv.wa_phone_number,
        status=conv.status,
        last_message=conv.last_message,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


def message_to_output(msg: Message) -> MessageOutput:
    """Map a Message entity to MessageOutput DTO."""
    return MessageOutput(
        id=str(msg.id),
        conversation_id=str(msg.conversation_id),
        role=msg.role,
        content=msg.content,
        tokens_used=msg.tokens_used,
        created_at=msg.created_at.isoformat(),
    )


# ============================================================================
# Input DTOs — Lead
# ============================================================================


@dataclass(frozen=True, slots=True)
class CreateLeadInput:
    client_id: str
    phone: str
    name: str = ""
    source: str = "whatsapp"


@dataclass(frozen=True, slots=True)
class ListLeadsInput:
    client_id: str
    status: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class UpdateLeadInput:
    lead_id: str
    status: str | None = None
    score: int | None = None
    notes: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        if self.status is None and self.score is None and self.notes is None and self.name is None:
            raise ValueError("Must provide at least one field to update")


@dataclass(frozen=True, slots=True)
class GetLeadStatsInput:
    client_id: str


@dataclass(frozen=True, slots=True)
class SendProactiveMessageInput:
    lead_id: str
    message_text: str


# ============================================================================
# Input DTOs — Feedback
# ============================================================================


@dataclass(frozen=True, slots=True)
class CreateFeedbackInput:
    client_id: str
    rating: int
    lead_id: str | None = None
    conversation_id: str | None = None
    comment: str = ""

    # Validation is handled in CreateFeedbackUseCase and domain entity


@dataclass(frozen=True, slots=True)
class ListFeedbackInput:
    client_id: str
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class GetFeedbackStatsInput:
    client_id: str


# ============================================================================
# Output DTOs — Lead
# ============================================================================


@dataclass(frozen=True, slots=True)
class LeadOutput:
    id: str
    client_id: str
    phone: str
    name: str
    status: str
    source: str
    score: int
    notes: str
    last_contacted_at: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class LeadStatsOutput:
    total: int
    by_status: dict[str, int]
    conversion_rate: float
    new_today: int
    avg_score: float


# ============================================================================
# Output DTOs — Feedback
# ============================================================================


@dataclass(frozen=True, slots=True)
class FeedbackOutput:
    id: str
    client_id: str
    lead_id: str | None
    conversation_id: str | None
    rating: int
    comment: str
    created_at: str


@dataclass(frozen=True, slots=True)
class FeedbackStatsOutput:
    total: int
    average_rating: float
    rating_distribution: dict[int, int]


# ============================================================================
# Mapper functions — Lead
# ============================================================================


def lead_to_output(lead: Lead) -> LeadOutput:
    """Map a Lead entity to LeadOutput DTO."""
    from app.domain.lead.entity import LeadStatus
    return LeadOutput(
        id=str(lead.id),
        client_id=str(lead.client_id),
        phone=lead.phone,
        name=lead.name,
        status=lead.status.value if isinstance(lead.status, LeadStatus) else lead.status,
        source=lead.source,
        score=lead.score,
        notes=lead.notes,
        last_contacted_at=lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
        created_at=lead.created_at.isoformat(),
        updated_at=lead.updated_at.isoformat(),
    )


# ============================================================================
# Landing DTOs
# ============================================================================


@dataclass(frozen=True, slots=True)
class SubmitLandingInput:
    """Input para el envío de formulario desde una landing page pública."""
    slug: str
    name: str
    whatsapp: str
    interest: str = ""


@dataclass(frozen=True, slots=True)
class SubmitLandingOutput:
    """Output después de procesar el formulario de landing."""
    lead_id: str
    message: str
    auto_reply: str


@dataclass(frozen=True, slots=True)
class GetLandingConfigInput:
    """Input para obtener la configuración de landing de un cliente (admin)."""
    client_id: str


@dataclass(frozen=True, slots=True)
class UpdateLandingConfigInput:
    """Input para actualizar la configuración de landing de un cliente (admin)."""
    client_id: str
    landing_slug: str | None = None
    landing_title: str | None = None
    landing_description: str | None = None
    landing_active: bool | None = None
    landing_primary_color: str | None = None
    landing_auto_reply: str | None = None

    def __post_init__(self) -> None:
        fields = (
            self.landing_slug, self.landing_title, self.landing_description,
            self.landing_active, self.landing_primary_color, self.landing_auto_reply,
        )
        if all(f is None for f in fields):
            raise ValueError("Must provide at least one landing field to update")


@dataclass(frozen=True, slots=True)
class LandingConfigOutput:
    """Output con la configuración completa de landing."""
    client_id: str
    landing_slug: str | None
    landing_title: str
    landing_description: str
    landing_active: bool
    landing_primary_color: str
    landing_auto_reply: str
    leads_count: int


@dataclass(frozen=True, slots=True)
class LandingPublicConfigOutput:
    """Output ligero para la landing page pública (sin datos sensibles)."""
    client_name: str
    landing_title: str
    landing_description: str
    landing_active: bool
    landing_primary_color: str


# ============================================================================
# Mapper functions — Feedback
# ============================================================================


def feedback_to_output(fb: Feedback) -> FeedbackOutput:
    """Map a Feedback entity to FeedbackOutput DTO."""
    return FeedbackOutput(
        id=str(fb.id),
        client_id=str(fb.client_id),
        lead_id=str(fb.lead_id) if fb.lead_id else None,
        conversation_id=str(fb.conversation_id) if fb.conversation_id else None,
        rating=fb.rating,
        comment=fb.comment,
        created_at=fb.created_at.isoformat(),
    )


# ============================================================================
# Input DTOs — Email
# ============================================================================


@dataclass(frozen=True, slots=True)
class SendEmailInput:
    client_id: str
    to_email: str
    rubro_slug: str
    sequence_number: int = 1
    lead_id: str | None = None
    business_name: str = ""
    contact_name: str = ""


@dataclass(frozen=True, slots=True)
class GetEmailStatsInput:
    client_id: str


@dataclass(frozen=True, slots=True)
class ListEmailsInput:
    client_id: str
    lead_id: str | None = None
    limit: int = 20
    offset: int = 0


# ============================================================================
# Output DTOs — Email
# ============================================================================


@dataclass(frozen=True, slots=True)
class SendEmailOutput:
    id: str
    status: str


@dataclass(frozen=True, slots=True)
class EmailLogOutput:
    id: str
    client_id: str
    lead_id: str | None
    to_email: str
    subject: str
    template_slug: str
    sequence_number: int
    status: str
    error_message: str
    sent_at: str
    created_at: str


@dataclass(frozen=True, slots=True)
class EmailStatsOutput:
    total_sent: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    open_rate: float
    click_rate: float
    by_template: dict[str, int]


# ============================================================================
# Mapper functions — Email
# ============================================================================


def email_log_to_output(log: EmailLog) -> EmailLogOutput:
    from app.domain.email.entity import EmailStatus
    return EmailLogOutput(
        id=str(log.id),
        client_id=str(log.client_id),
        lead_id=str(log.lead_id) if log.lead_id else None,
        to_email=log.to_email,
        subject=log.subject,
        template_slug=log.template_slug,
        sequence_number=log.sequence_number,
        status=log.status.value if isinstance(log.status, EmailStatus) else log.status,
        error_message=log.error_message,
        sent_at=log.sent_at.isoformat(),
        created_at=log.created_at.isoformat(),
    )


# ============================================================================
# Input DTOs — Auth
# ============================================================================


@dataclass(frozen=True, slots=True)
class RegisterClientInput:
    email: str
    password: str
    business_name: str
    whatsapp_number: str


@dataclass(frozen=True, slots=True)
class RegisterClientOutput:
    client_id: str
    email: str
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class LoginClientInput:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginClientOutput:
    access_token: str
    client_id: str
    role: str
    status: str
    token_type: str = "bearer"


@dataclass(frozen=True, slots=True)
class CurrentClientOutput:
    client_id: str
    email: str
    name: str
    role: str
    status: str
    whatsapp_number: str
    whatsapp_connected: bool
    plan: str
    is_active: bool


# ============================================================================
# Input DTOs — Admin (approve/reject/disconnect-whatsapp)
# ============================================================================


@dataclass(frozen=True, slots=True)
class ApproveClientInput:
    client_id: str


@dataclass(frozen=True, slots=True)
class RejectClientInput:
    client_id: str


@dataclass(frozen=True, slots=True)
class DisconnectWhatsappInput:
    client_id: str


@dataclass(frozen=True, slots=True)
class AdminClientOutput:
    id: str
    email: str
    name: str
    role: str
    status: str
    is_active: bool
    whatsapp_number: str
    whatsapp_connected: bool
    plan: str
    created_at: str
    updated_at: str
