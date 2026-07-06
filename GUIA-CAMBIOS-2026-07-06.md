# Guía de cambios — Sesión 2026-07-06

Qué se hizo, por qué, y cómo queda el sistema. Complementa el
`HANDOFF-2026-07-06.md` (pasos para continuar) y el `CHECKLIST-MVP.md`
(vista rápida).

---

## Contexto de partida

Las Fases 0–5 del `PLAN-MVP.md` estaban commiteadas en `main`, pero
**validadas solo con `compileall` + smoke runners en un sandbox sin red**
— la suite real de `pytest`/`vitest` nunca se había ejecutado. El objetivo
de la sesión fue **cerrar esa brecha de verificación** y, además, una
decisión nueva: **eliminar Evolution API** del producto.

---

## 1. Verificación del backend

Se creó el entorno (`python3 -m venv`, `pip install -r requirements.txt`
con `cryptography`) y se ejecutó `pytest` por primera vez de verdad.

**Resultado inicial: 909 passed, 22 failed.** Los 22 fallos eran dos cosas:

- **14 tests de Evolution API** (`test_whatsapp_webhook.py`): contrato
  obsoleto (payloads `EvolutionWebhookPayload`, parsing de JID, eventos
  `messages.upsert`). Se eliminaron junto con Evolution (ver §3).
- **7 bugs reales** que nunca se habían ejecutado:

| Bug | Causa | Arreglo |
|-----|-------|---------|
| `client_repository` / `agent_repository` no mapeaban 23505/23503 | `_raise_domain_error` solo leía el código PG del body `"Supabase error:"`, ignoraba `exc.code` | Añadido fallback `getattr(exc, "code")` |
| `_send_whatsapp_message` se caía ante error de red | Solo capturaba `httpx.HTTPError`, no `ConnectionError` genérico | Envuelto en `try/except` → devuelve `"failed"` (la tarea Celery nunca se cae) |
| 4 fallos en `appointment_notifier` / `process_whatsapp_task` | Los fakes de `settings` no tenían `supabase_url`/`supabase_service_key` → `SupabaseHttpClient` reventaba antes del repo mockeado | Completados los fakes |
| `test_get_business_schedule...` | Línea huérfana `assert payload[...]` (variable inexistente) | Eliminada |

**Resultado final: 881 passed, 20 skipped, 0 failed.**

## 2. Verificación del frontend

`npm install && npm run build && npm test` → **build OK (incluye
`AppointmentsPage`) + 47 tests passed**. No hizo falta ningún fix.
(Nota: `npm run lint` tiene ~10 errores pre-existentes de `any` en tests
de Login/Register/Home, no relacionados con la agenda ni con el build.)

## 3. Eliminación de Evolution API

Decisión de Diego: sacar Evolution por completo. El canal del producto es
**exclusivamente Meta Cloud API**.

**Backend:**
- `whatsapp/schemas.py`: borradas las clases `Evolution*`; solo quedan los
  schemas de Meta + `WebhookResponse`.
- `whatsapp/message_processor.py`: borrados `extract_phone_number`,
  `process_evolution_message` y el alias `process`. **El routing ahora es
  estricto por `phone_number_id`** — se quitó el fallback legacy
  `find_by_whatsapp(número_del_remitente)`, que era semántica Evolution y
  además incorrecto para Meta (el número entrante es el del cliente final,
  no el del negocio).
- `whatsapp/webhook.py`: `receive_message` solo procesa payloads de Meta;
  `verify_webhook` usa solo `whatsapp_verify_token`.
- `config/settings.py`: quitados `evolution_api_url` / `evolution_api_key`.

**Tests:**
- Borrado `test_whatsapp_webhook.py` (1516 líneas, contrato Evolution).
- Añadido `test_whatsapp_webhook_meta.py` (superficie HTTP de Meta: verify
  GET + POST + payloads no soportados).
- Ajustado `test_whatsapp_multitenant_routing.py` (quitados los tests de
  fallback legacy; añadidos "pnid desconocido/ausente → ignored").

**Infra y docs:** `docker-compose*.yml`, `.env.example`, `.gitignore`,
README, GUIAs, PLAN-MVP, SECURITY-TODO limpiados. Borrados
`evolution-api.env.example` y los 2 specs de diseño de esa era
(`spec-whatsapp-webhook.md`, `spec-whatsapp-direct.md`).

## 4. Servicio `celery-beat` (hallazgo importante)

El `beat_schedule` de `send_appointment_reminders` **existía** en
`celery_app.py` desde la Fase 4, **pero ningún proceso `beat` lo
ejecutaba**: no había servicio `celery-beat` en ningún `docker-compose`.
Es decir, **los recordatorios nunca se habrían enviado**.

Se añadió el servicio `celery-beat` (`celery ... beat`) a
`docker-compose.yml` y `docker-compose.production.yml`, espejando el
worker. Debe correr como **proceso único** en el despliegue.

## 5. Migraciones (verificación estática)

Se verificaron las 5 migraciones (`001`–`005`) columna a columna contra
los 4 repositorios: **consistencia total, cero discrepancias**. Puntos
clave confirmados: `phone_number_id` (002) y
`whatsapp_access_token_encrypted` (005) en `clients`; `business_hours` +
`appointment_duration_minutes` (003); tabla `appointments` completa (003);
`messages.status` (004). Dato no obvio: `reminder_offset_minutes` **no es
columna** — vive dentro del JSONB `business_hours`.

Aplicarlas a la BD quedó pendiente (necesita acceso a Supabase). Ojo:
**001–004 no son idempotentes**; solo la 005 usa `IF NOT EXISTS`.

## 6. Dokploy / secretos

- Se **generó y validó** la clave Fernet `CREDENTIALS_ENCRYPTION_KEY`
  (probada contra el backend real, no el fallback base64).
- Al inspeccionar el env de producción (compose `agencias-ia-stack`) se
  detectó que **falta `CREDENTIALS_ENCRYPTION_KEY`** → el cifrado de
  tokens por tenant corre ahora mismo en **fallback base64 inseguro**. Y
  que hay placeholders inseguros vivos (`JWT_SECRET`, `POSTGRES_PASSWORD`
  = `CHANGE-ME`).
- El cambio seguro (añadir la clave + quitar vars Evolution) quedó listo
  pero **pendiente de aplicar** (el intento de escritura automática al env
  de producción fue bloqueado por el sistema de permisos; se aplica
  manualmente o con permiso explícito). Las rotaciones de riesgo se
  dejaron documentadas con su runbook (ver HANDOFF §P2).

---

## Estado final

| Área | Estado |
|------|--------|
| Backend | ✅ verde (881 tests) |
| Frontend | ✅ verde (build + 47 tests) |
| Evolution API | ✅ eliminado |
| Celery beat | ✅ servicio añadido |
| Migraciones | ✅ verificadas · ⏳ aplicar 005 |
| Dokploy env | ⏳ 1 cambio seguro + rotaciones |
| E2E Meta | ⏳ pendiente deploy + confirmaciones |

Todo el trabajo está en la rama **`develop`** (sin mergear a `main`).
Continuación paso a paso en `HANDOFF-2026-07-06.md`.
