# Plan MVP — agencias-ia

**Decisiones tomadas (2026-07-05):** canal WhatsApp = Meta Cloud API · agenda propia en Postgres (sync Google Calendar en fase 2 post-MVP) · ejecución por el equipo.

## Definición de MVP funcional

Un cliente (negocio) puede: conectar su número de WhatsApp Business, tener un agente IA que responde a sus clientes finales con memoria de conversación, que consulta disponibilidad y agenda/cancela citas, envía recordatorios automáticos, y todo visible desde el panel. Multi-tenant, desplegado en Dokploy, sin secretos versionados.

**Criterio de aceptación global (demo de venta):** mensaje real de WhatsApp → respuesta del bot en <15s → cita agendada visible en panel → recordatorio recibido → conversación completa consultable en el dashboard.

---

## Fase 0 — Saneamiento y prerequisitos (1-2 días)

> Empezar el trámite de Meta el DÍA 1: es el único elemento con lead time externo.

| # | Tarea | Criterio de aceptación |
|---|-------|------------------------|
| 0.1 | Iniciar verificación de negocio en Meta Business + crear WABA y número de pruebas | Cuenta WABA activa con número de test funcionando |
| 0.2 | Sacar secretos del repo: `evolution-api.env`, password PostgREST hardcodeada (`docker-compose.production.yml`, `init.sql`) → variables de entorno en Dokploy | `git grep` no encuentra credenciales; deploy sigue funcionando |
| 0.3 | Rotar cualquier credencial ya versionada | Credenciales antiguas revocadas |
| 0.4 | Resolver TODOs de `main.py` (lifecycle de conexiones Supabase/Redis) | Arranque y shutdown limpios en logs |
| 0.5 | Decidir y documentar: eliminar código Evolution API o dejarlo dormido | README refleja que el canal es Meta Cloud API |

## Fase 1 — Persistencia de conversaciones (2-3 días)

El pipeline responde pero no guarda nada ni tiene memoria (`tasks.py`, paso 8 = stub). Las tablas `conversations` y `messages` ya existen.

| # | Tarea | Criterio de aceptación |
|---|-------|------------------------|
| 1.1 | En `process_whatsapp_message`: buscar/crear conversación por (client_id, phone) y guardar mensaje entrante | Fila en `messages` por cada mensaje recibido |
| 1.2 | Guardar respuesta del agente tras el envío, con estado (sent/failed) | Respuestas persistidas con status real, no "sent" ficticio |
| 1.3 | Cargar últimos N mensajes como historial en el prompt (`build_user_message`/`agent_graph`) | El bot recuerda el contexto en una conversación de 5+ turnos |
| 1.4 | Verificar que `ConversationsPage`/`ConversationDetailPage` del frontend muestran los datos reales | Conversación de prueba visible end-to-end en el panel |
| 1.5 | Tests: integración del flujo webhook → persistencia → historial | Suite en verde |

## Fase 2 — Módulo de agenda (4-6 días) ⟵ corazón del producto

| # | Tarea | Criterio de aceptación |
|---|-------|------------------------|
| 2.1 | Migración `003_appointments.sql`: tabla `appointments` (client_id, conversation_id, contact_phone, contact_name, starts_at, ends_at, status, notes) + `business_hours`/config de disponibilidad por cliente | Migración aplica limpia sobre BD existente |
| 2.2 | Dominio + repositorio + use cases: crear, cancelar, reprogramar, listar, consultar disponibilidad (respetando horario del negocio y solapes) | Tests unitarios de reglas de disponibilidad en verde |
| 2.3 | Tools nativas del agente: `consultar_disponibilidad`, `agendar_cita`, `cancelar_cita` ejecutadas localmente en `execute_tool` (reemplaza la delegación a n8n de `infrastructure/ai/tools.py`) | El LLM agenda una cita real vía function calling en conversación de prueba |
| 2.4 | Endpoints REST `/appointments` (CRUD + filtros por fecha/estado, scoped por tenant) | Cliente A no puede ver citas de cliente B (test de aislamiento) |
| 2.5 | Frontend: página Agenda (vista lista/semana, crear/cancelar manual) | El dueño del negocio gestiona citas desde el panel |
| 2.6 | Confirmación por WhatsApp al agendar (mensaje dentro de la ventana de 24h) | Cliente final recibe confirmación con fecha/hora |

## Fase 3 — Canal Meta multi-tenant (2-3 días)

El sender actual (`tasks.py::_send_whatsapp_message`) usa credenciales **globales** de env; el dominio ya contempla `connect_whatsapp(phone_number_id)` por cliente pero no se persiste ni se usa.

| # | Tarea | Criterio de aceptación |
|---|-------|------------------------|
| 3.1 | Persistir `phone_number_id` + `access_token` (cifrado) por cliente; migración + repositorio | Cada tenant tiene sus credenciales en BD |
| 3.2 | Sender toma credenciales del cliente, no de env; error real si faltan (nada de "sent" silencioso) | Mensaje sin credenciales → estado failed visible, alerta en logs |
| 3.3 | Routing de webhook entrante: resolver tenant por `phone_number_id` del payload de Meta | Dos tenants de prueba reciben cada uno sus mensajes |
| 3.4 | Manejo de errores Meta: token expirado, número no válido, rate limits | Errores categorizados en logs y estado del mensaje |

## Fase 4 — Recordatorios (1-2 días)

| # | Tarea | Criterio de aceptación |
|---|-------|------------------------|
| 4.1 | Registrar plantilla HSM de recordatorio en Meta (obligatorio fuera de la ventana de 24h) — **iniciar aprobación en Fase 0** | Plantilla aprobada por Meta |
| 4.2 | Celery beat: job periódico que busca citas próximas y envía recordatorio (offset configurable por cliente, default 24h) | Recordatorio llega a la hora esperada; no se duplica |
| 4.3 | Marcar recordatorio enviado en `appointments` | Reintento seguro tras caída del worker |

## Fase 5 — Onboarding y pulido del panel (2-3 días)

| # | Tarea | Criterio de aceptación |
|---|-------|------------------------|
| 5.1 | Pantalla "Conectar WhatsApp": formulario phone_number_id + token, botón de prueba de envío | Cliente conecta su número sin tocar la BD |
| 5.2 | Configuración del bot desde el panel: prompt/personalidad, horario del negocio, duración de cita, offset de recordatorio | Cambios aplican sin redeploy |
| 5.3 | Estados vacíos y errores en frontend (sin conexión WA, sin citas) | Panel usable por no-técnicos |

## Fase 6 — Pruebas E2E y piloto (2-3 días)

| # | Tarea | Criterio de aceptación |
|---|-------|------------------------|
| 6.1 | Test E2E del flujo completo en staging con número real | Demo de venta reproducible |
| 6.2 | Suite completa en CI + smoke test post-deploy | Pipeline en verde |
| 6.3 | Piloto con 1 negocio amigo, 1 semana | 0 mensajes perdidos; feedback recogido |
| 6.4 | Runbook de operación: alta de tenant, rotación de token, qué mirar si el bot no responde | Otra persona puede operar el sistema |

---

## Cronograma y dependencias

Total estimado: **15-22 días de trabajo** (~3-4 semanas de calendario para 1 dev).

- Camino crítico externo: verificación Meta + aprobación de plantilla HSM (días-semanas) → **arrancar en Fase 0**.
- Fases 1 y 2 pueden solaparse si hay 2 personas (persistencia y agenda son independientes hasta 2.6).
- Fase 3 antes que 5 (el onboarding depende de credenciales por tenant).

## Fuera del MVP (fase 2 del producto)

Sync Google Calendar, billing automatizado (cobrar manual al inicio), métricas avanzadas del dashboard, knowledge base/RAG (la tabla existe, sin uso).

## Riesgos principales

1. **Meta**: tiempos de verificación y política de plantillas fuera de tu control → mitigación: empezar el trámite ya. (El código de Evolution API fue eliminado; el canal es exclusivamente Meta Cloud API.)
2. **Coste por conversación de Meta** entra en el pricing del servicio → calcular antes de fijar precios.
3. **Fiabilidad del envío**: el fallo silencioso actual es el mayor riesgo reputacional → resuelto en 3.2, no vender antes de eso.
