# Spec: Integracion WhatsApp Cloud API (Meta)

**Status**: Spec  
**Fecha**: 2026-06-09  
**Version**: 1.0  

---

## 1. Objetivo

Migrar la recepcion/envio de mensajes WhatsApp de Evolution API a **WhatsApp Cloud API** (Meta Graph API v22.0).  
El webhook GET (verificacion) no cambia. El webhook POST cambia de formato. El envio outbound cambia de endpoint.

---

## 2. Diagrama de Flujo

```
WEBHOOK RECEIVE (POST)
======================

Meta Cloud API
     │
     │ POST /webhook/whatsapp
     │ Body: MetaWebhookPayload
     ▼
  ┌──────────────────────────────┐
  │ webhook.py                   │
  │  receive_message()           │
  │  ─ parse MetaWebhookPayload  │  ← schemas.py (NUEVO)
  │  ─ iterar entry[].changes[]  │
  │  ─ extraer messages[]        │
  │  ─ extraer phone, contact    │
  │  ─ validar x-api-key (opc.)  │
  │  ─ rate limiter check        │
  └──────────┬───────────────────┘
             │ MetaMessage normalizado
             ▼
  ┌──────────────────────────────┐
  │ message_processor.py         │
  │  process()                   │
  │  ─ valida msg tiene texto    │
  │  ─ busca Client x phone      │
  │  ─ busca Agent activo        │
  │  ─ sanitize                  │
  │  ─ enqueue Celery task       │
  └──────────┬───────────────────┘
             │ task_id
             ▼
  ┌──────────────────────────────┐
  │ tasks.py                     │
  │  process_whatsapp_message()  │
  │  ─ LLM inference             │
  │  ─ _send_whatsapp_message()  │  ← Meta Cloud API (REAL)
  └──────────┬───────────────────┘
             │ HTTP POST
             ▼
  graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages
    Authorization: Bearer {ACCESS_TOKEN}
    Body: { messaging_product, to, text }
```

---

## 3. Estructuras de Payload

### 3.1 Webhook Inbound (Meta → Nosotros)

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "123456789",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "573001234567",
          "phone_number_id": "123456789"
        },
        "contacts": [{
          "profile": {"name": "Juan Perez"},
          "wa_id": "573001234567"
        }],
        "messages": [{
          "from": "573001234567",
          "id": "wamid.HBgNNTczMD...",
          "timestamp": "1716153600",
          "text": {"body": "Hola quiero una cita"},
          "type": "text"
        }]
      },
      "field": "messages"
    }]
  }]
}
```

### 3.2 Nuevos Schemas Pydantic (schemas.py)

```python
class MetaMessage(BaseModel):
    """Un mensaje individual del webhook Meta."""
    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: str  # "text", "image", "audio", "document", "location"
    text: Optional[dict] = None       # {"body": "..."}
    image: Optional[dict] = None
    audio: Optional[dict] = None
    document: Optional[dict] = None
    location: Optional[dict] = None
    model_config = {"populate_by_name": True}

    @property
    def content(self) -> Optional[str]:
        """Extrae texto del mensaje, si es tipo text."""
        if self.type == "text" and self.text:
            return self.text.get("body", "")
        return None

class MetaContact(BaseModel):
    """Contacto de WhatsApp en el webhook."""
    profile: Optional[dict] = None  # {"name": "Juan"}
    wa_id: str

class MetaValue(BaseModel):
    """value dentro de changes[].value."""
    messaging_product: str = "whatsapp"
    metadata: Optional[dict] = None
    contacts: Optional[list[MetaContact]] = []
    messages: Optional[list[MetaMessage]] = []

class MetaChange(BaseModel):
    """Un change dentro de entry.changes."""
    value: MetaValue
    field: str  # "messages"

class MetaEntry(BaseModel):
    """Una entry del webhook Meta."""
    id: str
    changes: list[MetaChange]

class MetaWebhookPayload(BaseModel):
    """Payload completo del webhook de Meta Cloud API."""
    object: str  # "whatsapp_business_account"
    entry: list[MetaEntry]
```

### 3.3 Mensaje Outbound (Nosotros → Meta)

```json
// POST https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages
// Header: Authorization: Bearer {ACCESS_TOKEN}
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "573001234567",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "Hola Juan, tu cita esta confirmada para el martes"
  }
}
```

---

## 4. Cambios Archivo por Archivo

### 4.1 `settings.py`
| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `whatsapp_phone_number_id` | `str` | `""` | Phone Number ID de WhatsApp Business |
| `whatsapp_access_token` | `str` | `""` | Token permanente de Meta (system user / app) |
| `whatsapp_verify_token` | `str` | `""` | Token que Meta usa para verificar webhook |
| `whatsapp_api_version` | `str` | `"v22.0"` | Version de Graph API |

Mantener campos `evolution_api_url` y `evolution_api_key` (no borrar — backward compat).

### 4.2 `schemas.py`
- **Mantener** schemas Evolution existentes (no borrar).
- **Agregar** nuevos schemas Meta: `MetaMessage`, `MetaContact`, `MetaValue`, `MetaChange`, `MetaEntry`, `MetaWebhookPayload`.
- Agregar `text_content` property a `MetaMessage` para extraer `text.body`.

### 4.3 `webhook.py`
- **GET** `/webhook/whatsapp` → SIN CAMBIOS. Verifica `hub.verify_token` contra `settings.whatsapp_verify_token`.
- **POST** `/webhook/whatsapp`:
  - Aceptar BOTH formatos. Detectar cual llega: `"object" == "whatsapp_business_account"` → Meta, si tiene `"event"` → Evolution.
  - Ruta Meta: parse `MetaWebhookPayload`, iterar `entry→changes→value.messages[]`, por cada mensaje extraer phone (`message.from_`) y texto (`message.content`), invocar `process()` del message_processor.
  - Ruta Evolution: mismo codigo actual.
  - API key validation: cambiar `evolution_api_key` → usar setting de Meta cuando es formato Meta.
  - Rate limiter: aplicar igual (por phone).

### 4.4 `message_processor.py`
- Cambiar firma de `process()` para aceptar phone y content directos (en vez de `EvolutionWebhookPayload` completo).
- Nueva firma: `async def process(phone: str, content: str, push_name: str, client_repo, agent_repo) -> WebhookResponse`.
- Quitar dependencia de `EvolutionWebhookPayload` y `extract_phone_number`.
- Logica de: validar phone con `WhatsAppNumber`, buscar Client, buscar Agent, sanitize, enqueue Celery — igual.
- `extract_phone_number()` se mantiene como helper (Evolution usa JID, Meta usa phone limpio). Meta path llama con phone directo sin `extract_phone_number`.

### 4.5 `tasks.py`
- `_send_whatsapp_message(phone, text, settings)` → implementar POST real a `https://graph.facebook.com/{version}/{phone_number_id}/messages`:
  ```python
  import httpx

  def _send_whatsapp_message(phone: str, text: str, settings) -> bool:
      url = (
          f"https://graph.facebook.com/{settings.whatsapp_api_version}"
          f"/{settings.whatsapp_phone_number_id}/messages"
      )
      headers = {
          "Authorization": f"Bearer {settings.whatsapp_access_token}",
          "Content-Type": "application/json",
      }
      body = {
          "messaging_product": "whatsapp",
          "recipient_type": "individual",
          "to": phone,
          "type": "text",
          "text": {"preview_url": False, "body": text},
      }
      try:
          r = httpx.post(url, headers=headers, json=body, timeout=10.0)
          r.raise_for_status()
          logger.info(f"[WHATSAPP] Sent to {phone}")
          return True
      except Exception as e:
          logger.error(f"[WHATSAPP] Failed to send: {e}")
          return False
  ```
- Manejar rate limiting de Meta: si status 429, logger warning + no retry (Meta tiene su propio rate limit).

### 4.6 `.env.example`
Agregar:
```env
# === WhatsApp Cloud API (Meta) ===
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_ACCESS_TOKEN=EAAx...
WHATSAPP_VERIFY_TOKEN=my-custom-verify-token
WHATSAPP_API_VERSION=v22.0
```

---

## 5. Testing

### 5.1 Unit Tests (nuevos en `tests/unit/test_whatsapp_webhook.py`)
- `test_webhook_meta_format_parses_correctly` — payload Meta se parsea bien.
- `test_webhook_meta_extracts_phone_from_from_field` — `message.from_` → phone.
- `test_webhook_meta_extracts_text_content` — `message.content` → texto.
- `test_webhook_meta_ignores_non_text_types` — imagen/audio → content=None → ignorado.
- `test_send_whatsapp_message_uses_meta_api` — mock httpx, verifica URL, headers, body.
- `test_send_whatsapp_message_handles_http_error` — httpx.HTTPError → return False.

### 5.2 Tests existentes que mantener
- `test_get_webhook_verification` — verifica hub.mode/challenge (misma logica, ahora usa `WHATSAPP_VERIFY_TOKEN`).
- Tests de rate limiter (no cambian).
- Tests de message_processor con nueva firma.

---

## 6. Configuracion en Meta

El usuario debe configurar en Meta Business:

1. **Crear App** en developers.facebook.com → tipo "Business".
2. **Agregar producto WhatsApp** → obtener Phone Number ID y test number.
3. **Generar Access Token**: System User con permisos `whatsapp_business_messaging` y `whatsapp_business_management`. Token permanente via System User → Generate Token.
4. **Configurar Webhook**: URL `https://{dominio}/webhook/whatsapp` + Verify Token (`WHATSAPP_VERIFY_TOKEN`). Suscribir a `messages`.
5. **Pasar a produccion**: Verificar Business, agregar metodo de pago si se necesita.

---

## 7. Orden de Implementacion

| Paso | Archivo | Que hacer |
|------|---------|-----------|
| 1 | `schemas.py` | Agregar Meta schemas (no rompe nada existente) |
| 2 | `settings.py` | Agregar 4 campos Meta |
| 3 | `.env.example` | Documentar nuevas vars |
| 4 | `tests/unit/test_whatsapp_webhook.py` | Escribir tests RED (TDD) |
| 5 | `message_processor.py` | Cambiar firma de `process()` (RED) |
| 6 | `webhook.py` | Adaptar POST para dual-format (GREEN) |
| 7 | `tasks.py` | Implementar `_send_whatsapp_message` real (GREEN) |
| 8 | Tests | Todos pasan → REFACTOR |

---

## 8. Riesgos

- **Rate limit Meta**: 250 msgs/sec por phone number. Si se excede, Meta devuelve 429. No reintentar en Celery; log + skip.
- **Token expiracion**: Tokens de prueba duran 24h. Para prod se necesita token permanente via System User.
- **Webhook doble**: Si el usuario tiene ambos (Evolution + Meta) corriendo, el dual-format parsing evita conflictos.
