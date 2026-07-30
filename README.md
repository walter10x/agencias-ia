# Agencia IA

Plataforma multi-tenant de agentes de IA por WhatsApp para negocios locales
(peluquerías, restaurantes, clínicas, etc.). Cada cliente conecta su número
de WhatsApp Business, tiene un agente que responde con memoria de
conversación, consulta disponibilidad y agenda/cancela citas, y todo es
visible desde un panel de control.

## Documentación (qué leer)

| Documento | Para qué |
|-----------|----------|
| **`CONFIGURACION-ECOSISTEMA-COMPLETO.md`** | **Fuente de verdad operativa** — YCloud, Orinoco, roadmap, panel onboarding, prod |
| **`PRODUCTO-CRM-CONTACTOS.md`** | Diseño CRM ligero (ficha contacto) — siguiente capa de producto |
| `PLAN-MVP.md` | Plan técnico histórico por fases de código |
| `SECURITY-TODO.md` | Rotación de credenciales |
| `GUIA-DESPLIEGUE-DOKPLOY.md` | Detalle de deploy |
| `scripts/onboard-tenant-template.sql` | Alta tenant por SQL (alternativa al panel) |

**Prod:** https://agencias.orinocostudios.org  
**Estado (2026-07-30):** bot Orinoco vivo (YCloud Coexistence). Panel listo para 2º tenant (aprobar + horario + connect WA). Falta solo el 2º número WhatsApp y la aprobación Meta de la plantilla de recordatorio.

## Estructura

```
backend-core/        FastAPI + LangGraph — motor de IA multi-tenant
frontend-dashboard/  React + Vite — panel de control
docker/              Configuración de Postgres (init) y nginx (proxy PostgREST)
docker-compose.yml               Stack de desarrollo local
docker-compose.production.yml    Stack de producción (Dokploy)
```

## Canal de WhatsApp

**Producción (Orinoco y tenants):** [YCloud](https://www.ycloud.com) + **WhatsApp Business App Coexistence**.

- Webhook: `POST /webhook/ycloud`
- Envío: `YCloudWhatsAppSender` (`WHATSAPP_PROVIDER=ycloud`)
- Por tenant: `phone_number_id` = E.164 del negocio + API Key cifrada (`connect-whatsapp` / panel)

El adaptador **Meta Cloud API** (`/webhook/whatsapp`) sigue en el código por compatibilidad; el camino activo en prod es YCloud.

Variables globales típicas (valores solo en Dokploy / `.env`, nunca en Git):

```
WHATSAPP_PROVIDER=ycloud
YCLOUD_API_KEY
YCLOUD_WEBHOOK_SECRET
YCLOUD_FROM_NUMBER
TEAM_NOTIFY_WHATSAPP
WHATSAPP_REMINDER_TEMPLATE_NAME
CREDENTIALS_ENCRYPTION_KEY
```

## Seguridad

Ver `SECURITY-TODO.md` para credenciales a rotar si alguna circuló en chat o historial de git.
