# Informe de estado — agencias-ia (2026-07-05)

Objetivo de negocio: vender automatización de mensajes WhatsApp + manejo de agenda para clientes (SaaS multi-tenant).

## Qué hay hoy

**Arquitectura sólida.** Monorepo con backend FastAPI (arquitectura hexagonal: domain/application/infrastructure), frontend React, Docker Compose dev y producción (Dokploy), PostgREST, Redis, Celery, n8n. 6 guías de documentación en la raíz. 32 archivos de tests.

**Implementado y funcional (en apariencia):**
- Auth multi-tenant con JWT, roles, aprobación/rechazo de clientes (`app/application/auth/`, migración `002_auth_multi_tenant.sql`).
- CRUD de clientes, agentes IA, leads, feedback, landing, templates (routers en `infrastructure/http/`).
- Webhook WhatsApp que acepta payloads de Meta Cloud API y Evolution API, con rate limiting Redis (`infrastructure/whatsapp/webhook.py`).
- Pipeline IA: Celery → carga agente → system prompt → LangGraph → LLM (OpenAI adapter) → envío de respuesta vía **Meta Cloud API** (`infrastructure/config/tasks.py`).
- Frontend: 15 páginas (dashboard, agentes, clientes, conversaciones, leads, templates, login/registro) con guards de ruta.
- BD: tablas `clients`, `agents`, `conversations`, `messages`, `knowledge_base`.

## Gaps críticos para el MVP

1. **La agenda NO existe.** No hay tabla de citas, ni modelo, ni endpoint, ni lógica de disponibilidad. "agendar_cita" solo aparece como nombre de tool que delega a un webhook de n8n (`infrastructure/ai/tools.py`), y no hay workflows de n8n en el repo. Sin esto, la mitad de la propuesta de venta no es entregable.
2. **Las conversaciones no se persisten en el flujo real.** El pipeline de Celery no guarda mensajes ni respuestas ("Paso 8: stub") y no carga historial — cada mensaje se responde sin memoria. Las páginas de Conversaciones del frontend no tendrán datos reales.
3. **Envío de WhatsApp sin configurar = silencioso.** Si faltan credenciales Meta, el mensaje solo se loguea y la tarea devuelve "sent". Además hay ambigüedad de canal: se recibe por Evolution API pero solo se envía por Meta Cloud API — no hay cliente de envío para Evolution.
4. **Sin recordatorios ni mensajes proactivos** (confirmación de cita, recordatorio 24h antes) — no hay tareas programadas más allá del procesamiento reactivo.
5. **Sin onboarding self-service del canal**: conectar el WhatsApp de un cliente (QR de Evolution / número de Meta) no tiene flujo en el panel.
6. **Sin billing** (aceptable para MVP si se cobra manual).

## Deuda / riesgos

- Password de PostgREST hardcodeada (commit `4016791`, comentario en `docker-compose.production.yml`).
- TODOs en `main.py` (pool de conexiones sin inicializar).
- `evolution-api.env` en el repo (posibles credenciales versionadas).
- Tests no ejecutados en esta revisión; cobertura aparente buena en unidad, pero el flujo E2E WhatsApp→LLM→respuesta→persistencia no está cubierto ni completo.

## Ruta al MVP vendible (orden propuesto)

1. **Persistencia de conversaciones e historial** en el pipeline Celery (las tablas ya existen). ~1-2 días.
2. **Módulo de agenda**: tabla `appointments` + servicios de disponibilidad + tools nativas del agente (`consultar_disponibilidad`, `agendar_cita`, `cancelar_cita`) ejecutadas localmente en vez de n8n. ~3-5 días.
3. **Cerrar el canal de envío**: decidir Evolution API (barato, QR, no oficial) vs Meta Cloud API (oficial, requiere verificación) y implementar el sender que falte + manejo de errores real. ~1-2 días.
4. **Recordatorios**: Celery beat con recordatorio de cita configurable. ~1 día.
5. **Onboarding del canal en el panel**: pantalla para conectar WhatsApp del cliente y probar el bot. ~2-3 días.
6. Sanear secretos (PostgREST, evolution-api.env) antes de tener clientes reales. ~medio día.

Estimación total al MVP: **~2-3 semanas** de trabajo enfocado. La base (auth multi-tenant, CRUD, pipeline IA, deploy) ya está hecha y es la parte más difícil; lo que falta es precisamente la funcionalidad que se vende: agenda, memoria de conversación y fiabilidad del envío.
