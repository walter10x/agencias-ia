"""Pydantic v2 models for Evolution API webhook payload."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class EvolutionKey(BaseModel):
    """Identificador del chat en Evolution API."""

    remote_jid: str = Field(
        alias="remoteJid",
        pattern=r"^[\d\-]+@(s\.whatsapp\.net|g\.us)$",
        description="WhatsApp JID, ej: 573001234567@s.whatsapp.net",
    )
    from_me: bool = Field(default=False, alias="fromMe")
    id: Optional[str] = Field(default=None)

    model_config = {"populate_by_name": True}

    def extract_phone(self) -> str:
        """Extrae el numero de WhatsApp sin el sufijo @."""
        return self.remote_jid.split("@")[0]


class EvolutionMessageData(BaseModel):
    """Datos del mensaje (parte 'message' del payload)."""

    conversation: Optional[str] = None
    image_message: Optional[dict] = None
    audio_message: Optional[dict] = None
    video_message: Optional[dict] = None
    document_message: Optional[dict] = None
    location_message: Optional[dict] = None
    contacts_array_message: Optional[dict] = None
    extended_text_message: Optional[dict] = None
    reaction_message: Optional[dict] = None
    button_response_message: Optional[dict] = None
    list_response_message: Optional[dict] = None
    poll_update_message: Optional[dict] = None

    @property
    def message_type(self) -> str:
        """Determina el tipo de mensaje basado en los campos presentes."""
        if self.conversation or self.extended_text_message:
            return "text"
        if self.image_message:
            return "image"
        if self.audio_message:
            return "audio"
        if self.video_message:
            return "video"
        if self.document_message:
            return "document"
        if self.location_message:
            return "location"
        if self.reaction_message:
            return "reaction"
        if self.button_response_message:
            return "button_response"
        if self.list_response_message:
            return "list_response"
        return "unknown"

    @property
    def content(self) -> Optional[str]:
        """Extrae el contenido textual del mensaje, si existe."""
        if self.conversation:
            return self.conversation
        if self.extended_text_message:
            return self.extended_text_message.get("text", "")
        if self.button_response_message:
            return self.button_response_message.get("selectedDisplayText", "")
        if self.list_response_message:
            return self.list_response_message.get("title", "")
        return None


class EvolutionData(BaseModel):
    """Contenedor de datos del evento."""

    key: EvolutionKey
    message: Optional[EvolutionMessageData] = None
    push_name: Optional[str] = Field(default=None, alias="pushName")
    message_timestamp: Optional[int] = Field(default=None, alias="messageTimestamp")
    instance_id: Optional[str] = Field(default=None, alias="instanceId")
    source: Optional[str] = None

    model_config = {"populate_by_name": True}


class EvolutionWebhookPayload(BaseModel):
    """Payload completo del webhook de Evolution API."""

    event: str = Field(
        ...,
        description="Tipo de evento: messages.upsert, messages.update, messages.delete",
    )
    instance: str = Field(default="default")
    data: EvolutionData

    @field_validator("event")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        valid_events = {"messages.upsert", "messages.update", "messages.delete"}
        if v not in valid_events:
            raise ValueError(f"Unsupported event type: {v}. Valid: {valid_events}")
        return v

    @property
    def is_messages_upsert(self) -> bool:
        return self.event == "messages.upsert"

    @property
    def has_text_content(self) -> bool:
        return self.data.message is not None and self.data.message.content is not None


class WebhookResponse(BaseModel):
    """Respuesta estandar del webhook."""

    status: Literal["queued", "ignored"] = "queued"
    task_id: Optional[str] = None
    reason: Optional[str] = None


# ============================================================================
# Meta WhatsApp Cloud API schemas
# ============================================================================

class MetaText(BaseModel):
    body: str = ""

class MetaMessage(BaseModel):
    from_: str = Field(alias="from", default="")
    id: str = ""
    text: MetaText = Field(default_factory=MetaText)
    type: str = "text"
    model_config = {"populate_by_name": True}

class MetaContact(BaseModel):
    profile: dict = Field(default_factory=dict)
    wa_id: str = ""

class MetaMetadata(BaseModel):
    """Bloque `metadata` del payload de Meta — identifica el número receptor.

    `phone_number_id` es la clave del routing multi-tenant (Fase 3.3):
    Meta lo incluye en cada `value.metadata` y coincide con el
    `phone_number_id` que cada tenant configura al conectar su WhatsApp.
    """

    display_phone_number: str = ""
    phone_number_id: str = ""

class MetaValue(BaseModel):
    messages: list[MetaMessage] = Field(default_factory=list)
    contacts: list[MetaContact] = Field(default_factory=list)
    metadata: MetaMetadata = Field(default_factory=MetaMetadata)

class MetaChange(BaseModel):
    value: MetaValue = Field(default_factory=MetaValue)

class MetaEntry(BaseModel):
    changes: list[MetaChange] = Field(default_factory=list)

class MetaWebhookPayload(BaseModel):
    object: str = ""
    entry: list[MetaEntry] = Field(default_factory=list)
