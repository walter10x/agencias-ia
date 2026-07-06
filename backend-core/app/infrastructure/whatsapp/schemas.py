"""Pydantic v2 models for the Meta WhatsApp Cloud API webhook payload."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


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
