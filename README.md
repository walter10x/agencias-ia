# Agencia IA

Plataforma multi-tenant de agentes de IA por WhatsApp para negocios locales
(peluquerías, restaurantes, clínicas, etc.). Cada cliente conecta su número
de WhatsApp Business, tiene un agente que responde con memoria de
conversación, consulta disponibilidad y agenda/cancela citas, y todo es
visible desde un panel de control.

Ver `PLAN-MVP.md` para el plan de trabajo del MVP y su estado por fases, y
`GUIA.md` / `GUIA-DESPLIEGUE-DOKPLOY.md` / `GUIA-INTEGRACION.md` para guías
operativas detalladas de setup y despliegue.

## Estructura

```
backend-core/        FastAPI + LangGraph — motor de IA multi-tenant
frontend-dashboard/  React + Vite — panel de control
docker/              Configuración de Postgres (init) y nginx (proxy PostgREST)
docker-compose.yml               Stack de desarrollo local
docker-compose.production.yml    Stack de producción (Dokploy)
SECURITY-TODO.md     Checklist de rotación de credenciales (ver Fase 0 del plan)
```

## Canal de WhatsApp: Meta Cloud API (decisión Fase 0.5)

**El MVP usa exclusivamente [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
como canal de mensajería.** Ya está integrado y funcionando en Dokploy con
un número de prueba (WABA). Las variables relevantes son:

```
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_ACCESS_TOKEN
WHATSAPP_VERIFY_TOKEN
WHATSAPP_API_VERSION
```

Estas credenciales viven **solo** como variables de entorno (en Dokploy para
producción, en `backend-core/.env` — gitignored — para desarrollo local).
A partir de la Fase 3 del plan, además se persisten cifradas por tenant en
base de datos (`connect_whatsapp`), en vez de depender de una única
credencial global.

### Evolution API — plan B "dormido"

El proyecto contempló originalmente [Evolution API](https://doc.evolution-api.com)
(gateway self-hosted de WhatsApp, vía Baileys) como alternativa a Meta. Esa
vía queda **fuera del MVP** pero **no se elimina**:

- El webhook (`backend-core/app/infrastructure/whatsapp/webhook.py`) sigue
  detectando y procesando el formato de payload de Evolution
  (`EvolutionWebhookPayload`) además del de Meta — no se ha borrado ese
  código, solo no se usa activamente.
- No hay ningún servicio `evolution-api` activo en `docker-compose.yml` ni
  en `docker-compose.production.yml` — no se está desplegando ni
  consumiendo recursos.
- `evolution-api.env.example` documenta la configuración que tendría el
  contenedor de Evolution si se llegara a activar como fallback (por
  ejemplo, ante un rechazo o suspensión de la cuenta de Meta). El archivo
  real con valores (`evolution-api.env`) está en `.gitignore` y nunca debe
  versionarse.
- Las variables `EVOLUTION_API_URL` / `EVOLUTION_API_KEY` siguen
  declaradas (vacías por defecto) en los servicios `backend` y
  `celery-worker` de ambos `docker-compose*.yml`, sin coste ni efecto si
  no se usan.

Si en el futuro se decide reactivar Evolution: descomentar/añadir su
servicio en el `docker-compose` correspondiente, copiar
`evolution-api.env.example` a `evolution-api.env` con valores reales, y
configurar `EVOLUTION_API_URL`/`EVOLUTION_API_KEY`.

## Seguridad

Ver `SECURITY-TODO.md` para la lista de credenciales que deben rotarse
tras el saneamiento de la Fase 0 del plan (contraseñas que estuvieron
hardcodeadas o documentadas en texto plano en el historial de git).
