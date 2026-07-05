# SECURITY-TODO — Rotación de credenciales (Fase 0.3)

Generado durante el saneamiento de Fase 0 del `PLAN-MVP.md` (2026-07-05).
El agente que hizo el saneamiento **no tiene acceso** a Meta, Supabase, Dokploy
ni a los entornos donde estas credenciales pudieron usarse — por eso esto es
una lista de acción para el equipo, no una rotación ya hecha.

## Qué se encontró y por qué importa

El repo no tenía API keys ni tokens reales de proveedores externos (OpenAI,
Anthropic, Meta) versionados — todos los `.env.example`/guías usaban
placeholders (`sk-...`, `EAAxxxx...`, etc.). Sí se encontraron estas
credenciales/datos operativos reales o potencialmente reales:

| # | Credencial / dato | Dónde estaba | Riesgo | Acción requerida |
|---|---|---|---|---|
| 1 | Password de superadmin `SuperAdmin123!` para `walter@admin.com` | Hardcodeada como default en `backend-core/scripts/seed_superadmin.py` (ya corregido) y documentada en texto plano en `GUIA-INTEGRACION.md` (ya saneado) | **Medio** — es una credencial de acceso admin real y conocida por cualquiera con acceso al repo | **ROTAR**: si existe algún entorno (local, staging, o el que sea) donde se ejecutó `seed_superadmin.py` sin `SUPERADMIN_PASSWORD` propio, cambiar esa contraseña ya (login admin → cambiar password, o re-ejecutar el script con `SUPERADMIN_PASSWORD` nuevo). El script ya no permite crear el admin sin especificar email/password explícitos. |
| 2 | Password del rol `authenticator` de PostgREST: `postgrest` hardcodeada en `docker/postgres/init.sql` | `init.sql`, referenciada en `docker-compose.production.yml` y `docker-compose.yml` | **Medio** — si algún deploy de Dokploy ya corrió con esa password fija | **ROTAR**: generar un valor nuevo (`openssl rand -hex 24`), definir `POSTGREST_AUTHENTICATOR_PASSWORD` en las variables de entorno del proyecto en Dokploy, y re-desplegar. Si el volumen de Postgres ya existe (no es un init limpio), hay que además correr manualmente `ALTER ROLE authenticator WITH PASSWORD '<nuevo-valor>';` en la base de datos existente, porque los scripts de `docker-entrypoint-initdb.d` **solo corren la primera vez** que se crea el volumen. |
| 3 | `AUTHENTICATION_API_KEY=change-me-to-a-secure-key` en `evolution-api.env` | Tracked en git (ya se quitó del tracking; ver `evolution-api.env.example`) | **Bajo** — es un valor placeholder ("change-me"), no una key real, y Evolution API no está activo en el MVP (Meta Cloud API es el canal, ver README.md) | Si en el futuro se activa Evolution como plan B, generar una key real con `openssl rand -hex 32` y guardarla SOLO en `evolution-api.env` local (gitignored), nunca commitear. |
| 4 | Phone Number ID de Meta (`1202123836308611`) y URL de Cloudflare Tunnel de un entorno de trabajo real | `GUIA-INTEGRACION.md`, `GUIA-DESPLIEGUE-DOKPLOY.md` (ya sanados a placeholders) | **Bajo** — el Phone Number ID no autentica nada sin el access token (que nunca estuvo versionado en claro), y el tunnel de Cloudflare es efímero (probablemente ya expirado) | Ninguna rotación estrictamente necesaria, pero si ese túnel sigue activo, apagarlo y generar uno nuevo cuando se retome el trabajo con Meta. |

## Checklist de rotación

- [ ] Cambiar/rotar el password del superadmin `walter@admin.com` en cualquier
      entorno donde exista (local, staging, Dokploy).
- [ ] Generar nuevo `POSTGREST_AUTHENTICATOR_PASSWORD`, configurarlo en
      Dokploy, y aplicar `ALTER ROLE authenticator WITH PASSWORD '...'` en
      cualquier base de datos ya desplegada con la password vieja
      (`postgrest`).
- [ ] Confirmar que el `JWT_SECRET` usado en cualquier deploy previo no sea
      el default de desarrollo (`change-me-in-production...`) — si lo es,
      rotarlo también (invalida todas las sesiones activas).
- [ ] Confirmar que `CREDENTIALS_ENCRYPTION_KEY` (Fernet, cifra los access
      tokens de WhatsApp por tenant) tiene un valor real generado en
      producción y no está vacío (vacío degrada a un fallback base64
      inseguro — ver `app/infrastructure/security/credentials_cipher.py`).
- [ ] Revisar si el túnel de Cloudflare
      `charter-compute-identified-testament.trycloudflare.com` (mencionado
      en docs, ya saneado) sigue activo en algún proceso; si es así,
      detenerlo.

## Nota sobre 0.1 (Meta) y 0.5 (Evolution)

Este documento no cubre credenciales de la cuenta de Meta Business/WABA
(tarea 0.1 del plan) porque ese trámite es externo y no gestionado desde
código. Cuando el equipo tenga el access token de producción de Meta,
debe ir SOLO en variables de entorno de Dokploy (`WHATSAPP_ACCESS_TOKEN`),
nunca en el repo.
