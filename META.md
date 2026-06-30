# 🎯 META — Agencia IA Platform

> Documento de visión y roadmap técnico.
> Basado en la arquitectura actual + los módulos objetivo.

---

## 📊 Estado actual vs Meta final

| Módulo | Funcionalidad | Estado | Prioridad |
|--------|--------------|:------:|:---------:|
| **1** | Chatbots Multicanal | ⚠️ | 🔴 |
| **2** | Automatizaciones (n8n) | ✅ | 🟢 |
| **3** | Agentes IA Especializados | ✅ | 🔴 |
| **4** | Prospección Automática | ✅ | 🟡 |
| **5** | Panel para clientes | ⚠️ | 🟢 |
| **6** | Plantillas de servicios | ✅ | 🟢 |
| **7** | Landing Pages + Formularios | 🔲 | 🟡 |
| **8** | Email Marketing | 🔲 | 🟡 |
| **9** | Contenido IA | 🔲 | 🟢 |
| **10** | Meta Ads API | 🔲 | 🔴 |

---

## Módulo 1 — Chatbots Multicanal

| Canal | Estado | Notas |
|-------|:------:|-------|
| **WhatsApp** | ✅ | Meta Cloud API + webhook listo. Faltan credenciales reales |
| **Telegram** | ❌ | Sin implementar |
| **Webchat** | ❌ | Sin implementar (widget web) |
| **Instagram DM** | ❌ | Sin implementar |
| **Facebook Messenger** | ❌ | Sin implementar |

### 🔧 Lo que tenemos
- Arquitectura hexagonal con puertos (`LLMPort`)
- Un solo webhook unificado (`/webhook/whatsapp`)
- Message processor genérico (phone + text → agente)
- LangGraph para orquestación del agente

### 📋 Lo que falta
- Adaptador para cada canal (Telegram, Webchat, etc.)
- Enrutador de canales (identificar origen y aplicar lógica distinta)
- Webhook único que reciba de todos los canales y los normalice

### 💡 Cómo integrarlo
Cada canal nuevo es un **adaptador** en `app/infrastructure/channels/`:

```
app/infrastructure/channels/
├── whatsapp_adapter.py     ← ya existe como webhook + message_processor
├── telegram_adapter.py     ← nuevo
├── webchat_adapter.py      ← nuevo
└── channel_router.py       ← unifica todos los webhooks
```

**Concepto**: Todos los canales convergen al mismo `LLMPort.generate()`. El agente no sabe si el mensaje vino de WhatsApp o Telegram.

---

## Módulo 2 — Automatizaciones (n8n como motor)

| Aspecto | Estado |
|---------|:------:|
| n8n instalado | ✅ |
| Tools en agentes | ✅ |
| Endpoints en tools | ✅ |
| AgentGraph llama a tools | ✅ |
| Flujos n8n creados | ❌ |

### 🔧 Lo que tenemos
- n8n corriendo en `:5678`
- `tools` en el formulario de agente (nombre, descripción, endpoint)
- `agent_tools_to_openai_format()` convierte tools → OpenAI function calling
- `execute_tool()` llama al endpoint configurado

### 📋 Lo que falta
- Crear los flujos en n8n (agendar_cita, consultar_precios, etc.)
- Conectar n8n con servicios externos (Google Calendar, Gmail, etc.)

### 💡 Flujo completo
```
Agente IA → detecta tool "agendar_cita"
  → POST al endpoint: http://n8n:5678/webhook/agendar-cita
  → n8n recibe → crea evento en Google Calendar
  → n8n responde → agente muestra confirmación al usuario
```

---

## Módulo 3 — Agentes IA Especializados

| Aspecto | Estado |
|---------|:------:|
| Crear agente | ✅ |
| Personalidad (prompt base) | ✅ |
| Tools | ✅ |
| Memoria | ❌ |
| Acciones externas | ⚠️ (parcial) |
| Roles (ventas, soporte, etc.) | ❌ |

### 🔧 Lo que tenemos
- `AgentForm` con: nombre, personalidad, tools dinámicos, KB refs
- `AgentDetailPage` con: info completa, editar, desactivar, eliminar
- System prompt construido con `build_system_prompt()` (personalidad + negocio + tools)

### 📋 Lo que falta (para rol de agente)
- **Memoria/conversaciones**: el agente no recuerda conversaciones anteriores
- **Historial de chat**: no se guarda ni recupera el contexto
- **Roles predefinidos**: plantillas de agente (ventas, soporte, reservas)

### 💡 Cómo implementar memoria
```python
# 1. Al recibir mensaje, buscar conversaciones previas en Supabase
# 2. Incluir últimas N interacciones en el prompt
# 3. Guardar cada mensaje + respuesta en messages

async def get_conversation_history(client_id, phone, limit=5):
    """Obtener historial reciente de la conversación."""
    result = await supabase.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    return result.data
```

---

## Módulo 4 — Prospección Automática + Feedback

**Descripción**: El agente IA sale a buscar clientes proactivamente, no solo espera mensajes.

**Submódulos**:

### 4.1 Pipeline de Leads

- Tabla `leads` en Supabase (id, client_id, phone, name, status, source, score, notes, created_at, updated_at)
- Estados: `new`, `contacted`, `interested`, `not_interested`, `converted`, `archived`
- Cada lead tiene un score (0-100) según probabilidad de conversión

### 4.2 Mensajes Proactivos

- El agente puede **iniciar** conversaciones (no solo responder)
- Programación: "enviar mensaje a leads nuevos cada 24h"
- n8n orquesta los envíos programados
- Límites por día para evitar spam/ban

### 4.3 Clasificación Automática

Cuando un lead responde, el agente clasifica la intención:
- **Interesado** → cambia status a `interested`, programa seguimiento
- **No interesado** → archiva
- **Neutro** → mantiene en `contacted`
- Score se actualiza según la respuesta

### 4.4 Seguimiento Programado

- n8n + Celery: tareas programadas para re-contactar leads
- "Si no responde en 3 días → re-enviar"
- "Si interesado → enviar oferta en 1 día"

### 4.5 Feedback y Calificación

- Después de servicio → agente pide feedback
- Calificación 1-5 estrellas
- Comentario opcional
- Tabla `feedback` (id, client_id, lead_id, rating, comment, created_at)
- Dashboard muestra promedio de calificaciones

### 4.6 Reportes para el cliente

- Cuántos leads generados esta semana
- Tasa de conversión
- Calificación promedio
- Leads por estado (embudo visual)

### Arquitectura

- Las tablas `leads` y `feedback` van en Supabase
- Los mensajes proactivos van via WhatsApp Cloud API (mismo webhook)
- n8n programa los envíos masivos
- El dashboard muestra los reportes
- Todo dentro del mismo backend (nuevos endpoints + use cases)

---

## Módulo 5 — Panel para clientes

| Aspecto | Estado |
|---------|:------:|
| Dashboard | ✅ |
| Estadísticas | ⚠️ (básicas) |
| Conversaciones | ❌ |
| Leads | ❌ |
| Agentes (CRUD) | ✅ |
| Editar agente | ✅ |

### 📋 Lo que falta
- Página de **Conversaciones** (historial de chats)
- Página de **Estadísticas** (gráficos, métricas reales)
- Sección de **Leads**

---

## Módulo 6 — Plantillas de servicios

| Aspecto | Estado |
|---------|:------:|
| Chatbot restaurantes | ✅ |
| Chatbot inmobiliarias | ✅ |
| Chatbot clínicas | ✅ |
| Chatbot e-commerce | ✅ |
| Automatización reservas | ✅ |
| Automatización leads | ✅ |

### 💡 Implementación
Son **templates de agente** (personalidad + tools preconfiguradas):

```json
{
  "restaurante": {
    "name": "Bot Restaurante",
    "personality": "Eres el asistente virtual de un restaurante...",
    "tools": [
      {"name": "reservar_mesa", "description": "Reserva una mesa...", "endpoint": "..."},
      {"name": "ver_menu", "description": "Muestra el menú del día..."}
    ]
  }
}
```

Se crearían en el `AgentForm` con un selector de plantilla.

---

### ✅ Lo implementado
- **Selector de plantilla** en el `AgentForm` — dropdown con rubros preconfigurados
- **10 plantillas** listas para usar: restaurante, inmobiliaria, clínica, e-commerce, peluquería, bar, contador, fletes, tienda, gimnasio
- Cada plantilla incluye: **personalidad + tools preconfiguradas** según el rubro
- Tools típicas: `agendar_cita`, `consultar_precios`, `ver_horarios`, `hacer_pedido`, `calcular_envio`, etc.
- Al seleccionar una plantilla, el formulario se auto-completa con los valores del template

### 💡 Cómo funciona
```json
{
  "plantillas": {
    "restaurante": {
      "name": "Bot Restaurante",
      "personality": "Eres el asistente virtual de un restaurante...",
      "tools": ["agendar_reserva", "ver_menu", "consultar_horarios"]
    },
    "inmobiliaria": {
      "name": "Bot Inmobiliaria",
      "personality": "Eres un asesor inmobiliario virtual...",
      "tools": ["agendar_visita", "consultar_propiedades", "calcular_hipoteca"]
    },
    "clinica": {
      "name": "Bot Clínica",
      "personality": "Eres el asistente administrativo de una clínica...",
      "tools": ["agendar_cita", "consultar_medicos", "cancelar_cita"]
    }
  }
}
```

---

## 📈 Growth Funnel — De la Atracción a la Conversión

La plataforma cubre las **3 fases del ciclo de ventas** de un negocio local:

```
┌─────────────────────────────────────────────────────────┐
│                    GROWTH FUNNEL                         │
│                                                         │
│  🧲 ATTRACTION          🌱 NURTURE         💰 CONVERSION │
│  ─────────────         ──────────         ───────────── │
│  Landing Pages     →   Email Mktg    →   Agente IA      │
│  Meta Ads          →   Contenido IA  →   Leads Pipeline │
│  Formularios       →   Automatización→   Feedback       │
│                                                         │
│  Módulos: 7,10          Módulos: 8,9        Módulos:1-6 │
└─────────────────────────────────────────────────────────┘
```

### 🧲 Fase 1 — Atracción (ATTRACT)

El negocio necesita ser encontrado. El cliente potencial llega desde:

- **Meta Ads**: anuncios en Facebook/Instagram que apuntan a landing pages o WhatsApp
- **Landing Pages**: páginas optimizadas con formularios de captura
- **Formularios**: capturan nombre, teléfono y necesidad del prospecto

> Cada formulario completado = un lead automático en el pipeline (Módulo 4).

### 🌱 Fase 2 — Nutrición (NURTURE)

El lead no compra de inmediato. Hay que nutrirlo:

- **Email Marketing**: secuencias automáticas de emails según el interés
- **Contenido IA**: el agente genera contenido relevante para mantener el interés
- **Automatización n8n**: recordatorios, seguimientos, ofertas personalizadas

> El objetivo es mantener al lead "caliente" hasta que esté listo para comprar.

### 💰 Fase 3 — Conversión (CONVERT)

El lead está listo. El agente IA cierra:

- **Agente IA en WhatsApp**: responde dudas, agenda citas, cierra ventas
- **Pipeline de Leads**: tracking del estado de cada prospecto
- **Feedback**: mide satisfacción y genera referidos

> Todo el funnel se mide: cuántos entran, cuántos nutren, cuántos convierten.

---

## Módulo 7 — Landing Pages + Formularios

| Aspecto | Estado |
|---------|:------:|
| Builder de landing pages | 🔲 |
| Templates de páginas | 🔲 |
| Formularios de captura | 🔲 |
| Integración con pipeline de leads | 🔲 |
| Analíticas de conversión | 🔲 |

### 🎯 Objetivo

Crear páginas de aterrizaje optimizadas para convertir visitantes en leads. Cada formulario completado alimenta automáticamente el pipeline de prospección.

### 📋 Lo planeado

- **Builder visual**: editor drag & drop para crear landing pages sin código
- **Templates por industria**: páginas pre-diseñadas para cada rubro (restaurante, clínica, etc.)
- **Formularios inteligentes**: campos dinámicos según el tipo de negocio
- **Auto-lead**: cada submit del formulario → `POST /api/v1/leads` automático
- **Tracking**: pixel de conversión para medir cuántos visitantes → leads → clientes

### 💡 Arquitectura prevista

```
Landing Page (HTML estático)
  └── Formulario → POST /api/v1/landing/{slug}/submit
        └── Crea lead automático
        └── Dispara secuencia de nutrición (email + WhatsApp)
        └── Notifica al agente IA para seguimiento
```

---

## Módulo 8 — Email Marketing

| Aspecto | Estado |
|---------|:------:|
| Plantillas de email | 🔲 |
| Secuencias automáticas (drip) | 🔲 |
| Segmentación de leads | 🔲 |
| Integración con SendGrid/Mailgun | 🔲 |
| Métricas de apertura/click | 🔲 |

### 🎯 Objetivo

Mantener contacto con los leads que no responden por WhatsApp. Secuencias de email automáticas según el estado del lead y el tipo de negocio.

### 📋 Lo planeado

- **Drip campaigns**: secuencias de 3-5 emails predefinidas por industria
- **Segmentación**: leads fríos, tibios, calientes reciben distinto contenido
- **Integración n8n**: los flujos de n8n disparan emails según eventos (lead nuevo, cita agendada, feedback recibido)
- **Resend/SendGrid**: proveedor de envío (elegir el más económico para LATAM)
- **Dashboard de email**: tasa de apertura, clicks, conversiones

### 💡 Flujo de ejemplo

```
Lead nuevo (restaurante) 
  → Día 0: Email "Bienvenido, conocé nuestro menú"
  → Día 3: Email "Reservá tu mesa con 10% descuento"
  → Día 7: Email "Última oportunidad — cupón de bienvenida"
  → Si no abre ningún email → descartar lead
```

---

## Módulo 9 — Contenido IA

| Aspecto | Estado |
|---------|:------:|
| Generación de textos para redes | 🔲 |
| Ideas de contenido por rubro | 🔲 |
| Calendario editorial automático | 🔲 |
| Adaptación de tono por negocio | 🔲 |
| Programación de publicaciones | 🔲 |

### 🎯 Objetivo

El agente IA no solo atiende clientes — también genera contenido para redes sociales del negocio. Posts, stories, descripciones de productos, respuestas a comentarios.

### 📋 Lo planeado

- **Generador de posts**: "Creá 5 posts para esta semana para una peluquería"
- **Calendario editorial**: el agente sugiere qué publicar cada día
- **Tono personalizado**: usa la misma personalidad del agente IA del cliente
- **Ideas automáticas**: según temporada (Navidad, San Valentín, vuelta a clases) sugiere contenido
- **Programación**: vía n8n conectado a Facebook/Instagram Graph API

### 💡 Ejemplo

```
Usuario (dashboard): "Generá contenido para esta semana"
Agente IA: 
  Lunes: "💇‍♀️ Los 5 cortes de moda esta temporada"
  Martes: "🎨 Promo: coloración + corte 20% off"
  Miércoles: "⭐ Testimonio de cliente feliz"
  Jueves: "❓ ¿Cada cuánto hay que cortarse el pelo?"
  Viernes: "📲 Reservá tu turno por WhatsApp"
```

---

## Módulo 10 — Meta Ads API

| Aspecto | Estado |
|---------|:------:|
| Conexión con Meta Ads API | 🔲 |
| Creación de campañas desde dashboard | 🔲 |
| Segmentación automática | 🔲 |
| Optimización por IA | 🔲 |
| Reportes de ROI publicitario | 🔲 |

### 🎯 Objetivo

Crear y gestionar campañas de Facebook/Instagram Ads directamente desde el dashboard. La IA optimiza segmentación, presupuesto y creatividades.

### 📋 Lo planeado

- **Meta Business API**: autenticación OAuth para conectar cuentas publicitarias
- **Campañas pre-armadas**: templates por industria con públicos sugeridos
- **Segmentación IA**: el agente analiza los leads convertidos y sugiere públicos similares (lookalike)
- **Auto-optimización**: pausar anuncios de bajo rendimiento, escalar los que convierten
- **ROI dashboard**: costo por lead, costo por conversión, retorno de inversión

### 💡 Arquitectura prevista

```
Dashboard → Crear campaña
  → Meta Ads API → Facebook/Instagram
  → Lead de anuncio llega a landing page
  → Formulario → pipeline de leads
  → Agente IA hace seguimiento por WhatsApp
  → Dashboard muestra: inversión vs. ventas generadas
```

### 🔗 Integración con el funnel

Meta Ads (M10) alimenta Landing Pages (M7), que generan Leads (M4), que reciben Emails (M8) y Contenido (M9), y eventualmente convierten con el Agente IA (M3).

---

## 🧠 Definiciones clave

| Término | Qué es en nuestro sistema |
|---------|--------------------------|
| **Chatbot** | = **Agente IA** en nuestro dashboard |
| **Canal** | = De dónde viene el mensaje (WhatsApp, Telegram, webchat) |
| **Tool** | = Una acción que el agente puede ejecutar (llama a n8n) |
| **Flujo n8n** | = La automatización visual que ejecuta la tool |
| **Personalidad** | = El "system prompt" del agente |
| **Memoria** | = Historial de conversaciones (futuro) |
| **Plantilla** | = Agente + tools preconfigurados para un rubro |
| **Lead** | = Cliente potencial capturado por formulario, anuncio o chat |
| **Funnel** | = Embudo de ventas: Atracción → Nutrición → Conversión |
| **Landing Page** | = Página de aterrizaje con formulario de captura |
| **Drip Campaign** | = Secuencia automática de emails de nutrición |
| **Meta Ads** | = Anuncios en Facebook/Instagram gestionados desde el dashboard |

---

## 🚀 Roadmap priorizado

```
FASE 1 (AHORA) — Core funcional ✅
├── Dashboard cliente/admin
├── CRUD clientes + agentes
├── WhatsApp (Meta Cloud API)
├── LLM conectado
├── n8n listo
└── LangGraph agent flow

FASE 2 — Canales + Memoria ✅
├── Webchat widget
├── Telegram adapter
├── Memoria de conversaciones ✅
└── Historial de chats en dashboard ✅

FASE 3 — Prospección Automática ✅
├── Pipeline de leads (tabla `leads`)
├── Mensajes proactivos via n8n
├── Clasificación automática de intención
├── Seguimiento programado (n8n + Celery)
├── Feedback y calificación (tabla `feedback`)
└── Reportes para el cliente (dashboard)

FASE 4 — Productización ✅
├── Plantillas de servicio (10 rubros) ✅
├── Panel de clientes con login
├── Roles de agente (ventas, soporte)
└── Facturación / cobro mensualidad

FASE 5 — Marketing Digital 🔲
├── Landing Pages + Formularios (M7)
├── Email Marketing — secuencias automáticas (M8)
├── Contenido IA para redes sociales (M9)
└── Meta Ads API — campañas desde dashboard (M10)
```

---

## 📐 Decisión arquitectónica clave

**Un solo motor, múltiples canales:**

```
WhatsApp ─┐
Telegram ─┤
Webchat ──┤──→ unificar mensaje → LLMPort.generate() → LangGraph → respuesta
Insta ────┤
Messenger ┘
```

El agente NO sabe por qué canal llegó el mensaje. Solo sabe el contenido y quién es el cliente. El canal es un detalle de infraestructura (adapter).

---

*Este documento define la META. Cada nuevo desarrollo debe apuntar a estos módulos sin romper lo existente.*

> 🎯 **Proyecto en evolución — Fase 5: Marketing Digital en desarrollo**
