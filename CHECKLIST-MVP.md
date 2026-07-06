# Checklist MVP — agencias-ia (2026-07-06)

Versión corta y accionable. Detalle en `GUIA-CAMBIOS-2026-07-06.md` y
`HANDOFF-2026-07-06.md`.

## ✅ Hecho (en rama `develop`, sin mergear a `main`)

- [x] **Backend `pytest` verde** — 881 passed, 20 skipped, 0 failed (primera corrida real)
- [x] **Frontend `build` + `test` verde** — 47 tests, sin fixes
- [x] **Evolution API eliminado** — código, docker, docs, specs y tests
- [x] **Routing estricto por `phone_number_id`** — sin fallback legacy
- [x] **7 bugs backend arreglados** — mapeo de errores PG, envío defensivo, fakes de tests
- [x] **Servicio `celery-beat` añadido** — faltaba (los recordatorios no se disparaban)
- [x] **Migraciones 001–005 verificadas vs repos** — cero discrepancias
- [x] **Clave Fernet generada y validada** — cierra el fallback base64 inseguro

## ⏳ Pendiente (necesita acceso a infra)

- [ ] **Migración 005** → aplicar a la BD (correr la query de verificación primero; ver HANDOFF §P1)
- [ ] **Dokploy env** → añadir `CREDENTIALS_ENCRYPTION_KEY` + quitar `EVOLUTION_API_*` → redeploy
- [ ] **Confirmar** que `WHATSAPP_PHONE_NUMBER_ID=1202123836308611` = número real +34682743314
- [ ] **Mergear** `develop` → `main` + deploy con `celery-beat` corriendo
- [ ] **E2E** contra Meta: mensaje → respuesta con memoria → cita → confirmación → recordatorio → panel

## 🔒 Seguridad — rotaciones pendientes (con caveats, ver HANDOFF §P2)

- [ ] `JWT_SECRET` (es `...CHANGE-ME`) — cierra sesiones
- [ ] `POSTGRES_PASSWORD` (es `CHANGE_ME...`) — requiere `ALTER USER`
- [ ] `POSTGREST_AUTHENTICATOR_PASSWORD` — requiere `ALTER ROLE`
- [ ] `WHATSAPP_VERIFY_TOKEN` (es `my-verify-token`) — requiere re-suscribir webhook

## 📦 Ramas (apiladas; `develop` contiene todo)

| Rama | Contenido |
|------|-----------|
| `chore/remove-evolution-api` | Elimina Evolution API |
| `fix/backend-tests-green` | 7 bugs → suite verde |
| `feat/celery-beat-service` | Servicio celery-beat |
| **`develop`** | **Todo lo anterior + docs (este checklist, guía, handoff)** |
