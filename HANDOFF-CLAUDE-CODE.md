# Prompt de continuación para Claude Code

Copia lo que sigue (bloque entre las líneas) como primer mensaje en Claude Code, abierto en la raíz del repo `agencias-ia`.

---

Estoy retomando el MVP de un SaaS multi-tenant de automatización de WhatsApp + agenda de citas (backend FastAPI hexagonal en `backend-core/`, frontend React en `frontend-dashboard/`, despliegue Docker/Dokploy, canal Meta Cloud API, Celery+Redis).

Contexto imprescindible antes de tocar nada: lee `PLAN-MVP.md` (roadmap por fases con criterios de aceptación), `INFORME-ESTADO-MVP.md` (estado y gaps), `README.md`, `SECURITY-TODO.md` y `git log --oneline -25`.

Las Fases 0-5 del plan ya están implementadas y commiteadas en `main` (persistencia de conversaciones, módulo de agenda con tools nativas del agente, canal Meta multi-tenant con credenciales cifradas por cliente, confirmación de cita, recordatorios vía Celery beat, saneamiento de secretos, página Agenda en el frontend). Todo se validó en un sandbox SIN red a PyPI/npm, así que la suite real de tests NUNCA se ejecutó de verdad — solo `python3 -m compileall` y unos smoke runners sin dependencias (`backend-core/scripts/smoke_*.py`).

Tu primera tarea es cerrar esa brecha de verificación, en este orden, y NO sigas a lo siguiente hasta que cada paso esté verde:

1. Backend: crear entorno, `pip install -r backend-core/requirements.txt` (incluye `cryptography`), y ejecutar `cd backend-core && pytest tests/ -v`. Arregla lo que falle. Presta atención especial a los tests añadidos por las fases recientes: `test_conversation_repository.py`, `test_process_whatsapp_task.py`, `test_appointment_*.py`, `test_credentials_cipher.py`, `test_whatsapp_sender.py`, `test_whatsapp_multitenant_routing.py`, `test_appointment_notifier.py`, `test_appointment_reminders_task.py`.
2. Frontend: `cd frontend-dashboard && npm install && npm run build && npm test`. Arregla errores de TypeScript o de tests (la página nueva es `src/pages/AppointmentsPage.tsx` + `src/components/AppointmentForm.tsx` + `src/api/appointment.ts`).
3. Aplicar migraciones en orden sobre la BD (Supabase/Postgres): `backend-core/migrations/001` … `005`. La `005` añade `whatsapp_access_token_encrypted` a `clients`. Verifica que casan con lo que esperan los repositorios.
4. Generar y configurar en el entorno (Dokploy) las variables nuevas: `CREDENTIALS_ENCRYPTION_KEY` (clave Fernet real), `POSTGREST_AUTHENTICATOR_PASSWORD`, y confirmar `WHATSAPP_*`. Revisa `SECURITY-TODO.md` para la lista de credenciales a ROTAR (estuvieron en git).
5. Desplegar un proceso `celery beat` además del worker (los recordatorios dependen de él) y confirmar el `beat_schedule` en `backend-core/app/infrastructure/config/celery_app.py`.

Después, prueba el flujo end-to-end contra el número de prueba de Meta (envío real a +34606572976): mensaje entrante → respuesta del bot con memoria → agendar cita por chat → confirmación → recordatorio → todo visible en el panel (Conversaciones y Agenda). Reporta qué funciona y qué no antes de proponer cambios.

Trabaja en ramas por tarea y hazme revisar antes de mergear a `main`. No inventes: si algo del plan no cuadra con el código real, dímelo.

---

## Estado técnico resumido (para tu referencia, no forma parte del prompt)

- **main** contiene, además del código base inicial, los merges de: `feat/f1-persistencia`, `feat/f2-agenda`, `feat/f3-multitenant-meta`, `feat/f5-frontend-agenda`, `feat/f4-recordatorios`, `chore/f0-saneamiento`.
- Validación disponible sin red: `python3 -m compileall backend-core/app` (exit 0) y los smoke runners `smoke_appointments.py` (102), `smoke_multitenant.py` (10), `smoke_reminders.py` (5).
- Riesgo principal pendiente: plantilla HSM de Meta para recordatorios fuera de la ventana de 24h (trámite externo, ver comentario en `backend-core/app/infrastructure/celery/reminders.py`).
- Deuda conocida: idempotencia ante reintentos de Celery en el mensaje entrante (dedupe por wa message id), sync Google Calendar (fase 2 del producto), billing.
