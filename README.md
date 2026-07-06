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

El canal de WhatsApp del producto es **exclusivamente Meta Cloud API**. El
webhook (`backend-core/app/infrastructure/whatsapp/webhook.py`) sólo procesa
payloads de Meta y hace routing multi-tenant por `phone_number_id`.

## Seguridad

Ver `SECURITY-TODO.md` para la lista de credenciales que deben rotarse
tras el saneamiento de la Fase 0 del plan (contraseñas que estuvieron
hardcodeadas o documentadas en texto plano en el historial de git).
