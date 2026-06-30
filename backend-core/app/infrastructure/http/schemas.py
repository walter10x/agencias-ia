"""Pydantic v2 schemas for HTTP request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


# ============================================================================
# Client Schemas
# ============================================================================


class ClientCreateRequest(BaseModel):
    name: str = Field(..., max_length=200, description="Client business name")
    business_type: str = Field(..., min_length=1, description="Business type")
    whatsapp_number: str = Field(..., min_length=10, description="WhatsApp number (digits only, min 10)")


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=200, description="New client name (optional)")
    whatsapp_number: str | None = Field(None, min_length=10, description="New WhatsApp number (optional)")

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> ClientUpdateRequest:
        if self.name is None and self.whatsapp_number is None:
            raise ValueError("Must provide at least one of: name, whatsapp_number")
        return self


class ClientResponse(BaseModel):
    id: str
    name: str
    business_type: str
    whatsapp_number: str
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    count: int


# ============================================================================
# Agent Schemas
# ============================================================================


class AgentToolSchema(BaseModel):
    name: str = Field(..., min_length=1, description="Tool name")
    description: str = Field(..., min_length=1, description="Tool description")
    endpoint: str = Field("", description="Tool API endpoint URL (optional)")


class AgentCreateRequest(BaseModel):
    name: str = Field(..., max_length=200, description="Agent display name")
    personality: str = Field(..., min_length=10, max_length=5000, description="System prompt / personality (min 10 chars)")
    tools: list[AgentToolSchema] = Field(default_factory=list, description="Tools the agent can invoke")
    knowledge_base_refs: list[str] = Field(default_factory=list, description="Knowledge base references")


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=200, description="New name (optional)")
    personality: str | None = Field(None, min_length=10, max_length=5000, description="New personality (optional)")
    tools: list[AgentToolSchema] | None = Field(None, description="New tools list (optional)")
    knowledge_base_refs: list[str] | None = Field(None, description="New knowledge base refs (optional)")

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> AgentUpdateRequest:
        if (
            self.name is None
            and self.personality is None
            and self.tools is None
            and self.knowledge_base_refs is None
        ):
            raise ValueError("Must provide at least one of: name, personality, tools, knowledge_base_refs")
        return self


class AgentResponse(BaseModel):
    id: str
    client_id: str
    name: str
    personality: str
    tools: list[AgentToolSchema]
    knowledge_base_refs: list[str]
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    count: int


# ============================================================================
# Error Schema
# ============================================================================


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: str | None = None


# ============================================================================
# Response factory helpers
# ============================================================================


def agent_output_to_response(output) -> AgentResponse:
    """Convert an AgentOutput DTO to an AgentResponse Pydantic model."""
    return AgentResponse(
        id=output.id,
        client_id=output.client_id,
        name=output.name,
        personality=output.personality,
        tools=[AgentToolSchema(name=t.name, description=t.description, endpoint=t.endpoint) for t in output.tools],
        knowledge_base_refs=list(output.knowledge_base_refs),
        is_active=output.is_active,
        created_at=output.created_at,
        updated_at=output.updated_at,
    )


# ============================================================================
# Conversation Schemas
# ============================================================================


class ConversationResponse(BaseModel):
    id: str
    client_id: str
    agent_id: str | None = None
    wa_phone_number: str
    status: str
    last_message: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    count: int


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    tokens_used: int = 0
    created_at: str

    model_config = {"from_attributes": True}


class ConversationMessagesResponse(BaseModel):
    phone_number: str
    status: str
    messages: list[MessageResponse]


class ConversationStatsResponse(BaseModel):
    total_conversations: int
    active_conversations: int
    messages_today: int
    clients_with_conversations: int


# ============================================================================
# Lead Schemas
# ============================================================================


class LeadCreateRequest(BaseModel):
    client_id: str = Field(..., description="Client UUID")
    phone: str = Field(..., min_length=5, description="Phone number")
    name: str = Field(default="", max_length=200, description="Lead name")
    source: str = Field(default="whatsapp", description="Source (whatsapp, webchat, telegram, manual, import)")


class LeadUpdateRequest(BaseModel):
    status: str | None = Field(None, description="New status")
    score: int | None = Field(None, ge=0, le=100, description="Score 0-100")
    notes: str | None = Field(None, description="Notes")
    name: str | None = Field(None, max_length=200, description="Name")

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> LeadUpdateRequest:
        if self.status is None and self.score is None and self.notes is None and self.name is None:
            raise ValueError("Must provide at least one of: status, score, notes, name")
        return self


class LeadResponse(BaseModel):
    id: str
    client_id: str
    phone: str
    name: str
    status: str
    source: str
    score: int
    notes: str
    last_contacted_at: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int


class LeadStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    conversion_rate: float
    new_today: int
    avg_score: float


class SendMessageRequest(BaseModel):
    message_text: str = Field(..., min_length=1, max_length=4096, description="Message text to send")


# ============================================================================
# Feedback Schemas
# ============================================================================


class FeedbackCreateRequest(BaseModel):
    client_id: str = Field(..., description="Client UUID")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    lead_id: str | None = Field(None, description="Associated lead UUID")
    conversation_id: str | None = Field(None, description="Associated conversation UUID")
    comment: str = Field(default="", max_length=2000, description="Comment")


class FeedbackResponse(BaseModel):
    id: str
    client_id: str
    lead_id: str | None = None
    conversation_id: str | None = None
    rating: int
    comment: str
    created_at: str

    model_config = {"from_attributes": True}


class FeedbackListResponse(BaseModel):
    items: list[FeedbackResponse]
    total: int


class FeedbackStatsResponse(BaseModel):
    total: int
    average_rating: float
    rating_distribution: dict[int, int]


# ============================================================================
# Template Schemas
# ============================================================================


class TemplateItemSchema(BaseModel):
    """Schema ligero para listar plantillas (sin personality completa)."""
    slug: str
    name: str
    emoji: str
    description: str
    tools_count: int


class TemplateListResponse(BaseModel):
    templates: list[TemplateItemSchema]


class ApplyTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Client business name")
    whatsapp_number: str = Field(..., min_length=10, description="WhatsApp number (digits only)")


class ApplyTemplateResponse(BaseModel):
    template_slug: str
    client: ClientResponse
    agent: AgentResponse
    message: str


# ============================================================================
# Landing Schemas
# ============================================================================


class LandingSubmitRequest(BaseModel):
    """Request body para el formulario público de landing."""
    name: str = Field(..., min_length=1, max_length=200, description="Full name")
    whatsapp: str = Field(..., min_length=10, description="WhatsApp number (digits only)")
    interest: str = Field(default="", max_length=1000, description="Interest or message (optional)")


class LandingSubmitResponse(BaseModel):
    """Response después de enviar el formulario de landing."""
    lead_id: str
    message: str
    auto_reply: str


class LandingUpdateRequest(BaseModel):
    """Request body para actualizar config de landing (admin)."""
    landing_slug: str | None = Field(None, min_length=1, max_length=100, description="URL slug")
    landing_title: str | None = Field(None, min_length=1, max_length=200, description="Page title")
    landing_description: str | None = Field(None, min_length=1, max_length=500, description="Page description")
    landing_active: bool | None = Field(None, description="Enable/disable landing")
    landing_primary_color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$", description="Hex color #RRGGBB")
    landing_auto_reply: str | None = Field(None, min_length=1, max_length=1000, description="Auto-reply message template")

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "LandingUpdateRequest":
        fields = (
            self.landing_slug, self.landing_title, self.landing_description,
            self.landing_active, self.landing_primary_color, self.landing_auto_reply,
        )
        if all(f is None for f in fields):
            raise ValueError("Must provide at least one landing field to update")
        return self


class LandingConfigResponse(BaseModel):
    """Response con configuración completa de landing (admin)."""
    client_id: str
    landing_slug: str | None
    landing_title: str
    landing_description: str
    landing_active: bool
    landing_primary_color: str
    landing_auto_reply: str
    leads_count: int

    model_config = {"from_attributes": True}


class LandingPublicConfigResponse(BaseModel):
    """Response pública: info para renderizar la landing page."""
    client_name: str
    landing_title: str
    landing_description: str
    landing_active: bool
    landing_primary_color: str


# ============================================================================
# Email Schemas
# ============================================================================


class EmailSendRequest(BaseModel):
    client_id: str = Field(..., description="Client UUID")
    to_email: str = Field(..., min_length=5, description="Recipient email address")
    rubro_slug: str = Field(..., min_length=1, description="Rubro slug (restaurante, clinica, etc.)")
    sequence_number: int = Field(default=1, ge=1, le=3, description="Email sequence 1, 2, or 3")
    lead_id: str | None = Field(None, description="Associated lead UUID")
    business_name: str = Field(default="", description="Business name for template")
    contact_name: str = Field(default="", description="Contact name for template")


class EmailSendResponse(BaseModel):
    id: str
    status: str


class EmailLogResponse(BaseModel):
    id: str
    client_id: str
    lead_id: str | None = None
    to_email: str
    subject: str
    template_slug: str
    sequence_number: int
    status: str
    error_message: str
    sent_at: str
    created_at: str

    model_config = {"from_attributes": True}


class EmailListResponse(BaseModel):
    items: list[EmailLogResponse]
    total: int


class EmailStatsResponse(BaseModel):
    total_sent: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    open_rate: float
    click_rate: float
    by_template: dict[str, int]
