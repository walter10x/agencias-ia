# Configuración ecosistema completo

Documento de referencia: modelo de negocio, roles de cada pieza y **orden correcto** de trabajo.

Última actualización: 2026-07-29  
Estado: Local E2E YCloud OK · Dominio prod `agencias.orinocostudios.org` (DNS OK → 212.47.65.44) · dominio Dokploy creado · falta commit/push + redeploy.

---

## 1. Idea de negocio (2 capas, 1 plataforma)

| Capa | Qué es | Para quién |
|------|--------|------------|
| **A. Bot Orinoco** | WhatsApp de la empresa (`+34 682 74 33 15`) | Leads propios: automatizaciones IA, CRM, webs, software, soluciones IT |
| **B. Producto Agencia IA** | SaaS multi-tenant (esta app) | Clientes: chatbot + reservas/agenda + panel según su negocio |

- **A** = piloto / demo real (dogfooding).
- **B** = lo que se vende.
- Misma tecnología; Orinoco = **tenant #1**.

### Modelo de venta (resumen)

A cada negocio se le ofrece:

- Bot WhatsApp (su número; Coexistence vía YCloud si Meta directo duele).
- Reservas / agenda según su rubro.
- Panel multi-tenant.
- Cobro: setup + mensual; coste Meta (mensajes API) repercutido o incluido con margen.

| Pieza | Rol económico |
|-------|----------------|
| YCloud | Proveedor de canal (plan Free + tarifas Meta) |
| Agencia IA (esta app) | Margen y diferenciación |
| n8n | Extras / integraciones, no el core |

---

## 2. Arquitectura del flujo

```text
Cliente final (WhatsApp)
        │
        ▼
   YCloud (canal oficial Meta + Coexistence)
        │  webhook mensajes in / out
        ▼
   AGENCIA IA (esta app)  ← cerebro del producto
   · recibe mensaje
   · prompt del bot (por tenant / agente)
   · historial, agenda, leads
   · LLM en nuestro servidor / API configurada
   · responde por API YCloud
        │
        ▼ (opcional, secundario)
   n8n  ← automatizaciones extra
   · CRM, email, Sheets, avisos
   · NO el chatbot principal
```

### Confirmación: prompt + LLM en nuestra app

Sí. El modelo correcto es:

1. En **Agencia IA** se configura el **prompt** del bot (por tenant/agente).
2. El backend llama a un **LLM** (OpenAI, Claude u otro endpoint en nuestro servidor).
3. YCloud **solo** transporta WhatsApp; no sustituye prompt ni LLM.

Sin LLM configurado en la app no hay bot inteligente propio (solo Inbox humano en YCloud).

### Decisión importante

| Opción | Uso |
|--------|-----|
| AI Agent de YCloud | Rápido, sin código; malo para multi-tenant y para vender “nuestra plataforma” |
| Bot en Agencia IA + canal YCloud | **Elegido** — cerebro en nuestra app, canal en YCloud |

**No activar** el AI Agent de YCloud en paralelo al bot de Agencia IA (se pisan).

---

## 3. Qué hace cada pieza

### YCloud — teléfono / operador

- Conecta el número (Coexistence) sin el dolor de Meta a pelo.
- Envía / recibe WhatsApp (API oficial).
- Inbox humano de respaldo.
- Plantillas, límites, facturación Meta.
- **No** es el producto SaaS.

### Agencia IA (esta app) — producto que vendemos

- Multi-tenant (cada cliente = su bot, agenda, credenciales).
- Agente IA, conversaciones, citas, recordatorios, panel.
- Aquí vive la lógica: “soy clínica / soy taller / soy Orinoco”.
- Históricamente el código habla **Meta Cloud API** directo; con YCloud el cambio es un **adaptador** de envío/recepción hacia la API de YCloud (mismo flujo interno).

### n8n — pegamento, no cerebro

**Sí:**

- Lead calificado → HubSpot / Sheets / email.
- Cita creada → aviso interno (Telegram, Slack…).
- Flujos one-off por cliente que no merecen código en el core.

**No:**

- Chatbot de producción.
- Sustituir agenda / auth / multi-tenant de Agencia IA.

(n8n ya está en `docker-compose`; las tools de agenda viven en código nativo a propósito.)

---

## 4. Enfoque del bot Orinoco (tenant piloto)

Un solo job: **captar y calificar leads** de servicios Orinoco.

Flujo típico:

1. Saludo + qué ofrecéis (IA, CRM, webs, software).
2. Preguntas: empresa, necesidad, presupuesto/urgencia.
3. Si califica → agendar demo / pasar a humano.
4. Si no → info + follow-up suave (plantillas más adelante).

---

## 5. Orden correcto de pasos (desde 2026-07-28)

### Fase A — Canal YCloud (sin código aún)

| # | Paso | Estado |
|---|------|--------|
| 1 | Cuenta YCloud (plan Free) | ✅ Hecho |
| 2 | WhatsApp Business App Coexistence conectado | ✅ Hecho (`+34682743315`, Connected) |
| 3 | Prueba Inbox: mensaje llega a YCloud + app Business | ✅ Hecho |
| 4 | Sacar **API Key** en YCloud (Developers) | ✅ Hecho (nombre: `agencia-ia-orinoco-api-ke`) — valor solo en gestor de secretos / `.env`, **nunca en Git ni en este MD** |
| 5 | Revisar docs: URL envío mensajes + formato **webhook** entrante | ✅ Hecho (ver §8.1) |
| 6 | Anotar: número, WABA, eventos (`inbound`, `message.updated`) | ✅ Hecho (ver §8) |
| 7 | **No** activar AI Agent de YCloud | — vigente |
| 7b | (Opcional) Probar **envío** con API Key vía curl/`sendDirectly` | ✅ Hecho (texto a +34602438307) |

### Fase B — Infra de Agencia IA

| # | Paso | Estado |
|---|------|--------|
| 8 | Deploy / entorno vivo (Dokploy o local): backend + Redis + Celery + BD | ✅ Local OK (2026-07-28) — Dokploy sigue en error / sin dominio real |
| 9 | Migraciones aplicadas + variables de entorno (LLM key, DB, etc.) | ✅ Local: init.sql 001–005 + `.env` PostgREST/Postgres |
| 10 | Confirmar pipeline WhatsApp → Celery → LLM → respuesta | ⏳ Tras Fase C (adaptador YCloud) |

**Hallazgos 2026-07-28 (Dokploy):**

| Item | Estado |
|------|--------|
| Proyecto Dokploy `agencias-ia` | Existe |
| Compose `agencias-ia-stack` | Status **error** (último deploy fallido tras merge `develop` 2026-07-06) |
| Dominios Traefik | Ninguno real (`APP_DOMAIN=agencias.dominio.com` placeholder) |
| LLM en env Dokploy | Gateway `ollama.orinocostudios.dev` configurado |
| Canal actual en código/prod env | Meta Cloud API (aún **no** YCloud) |

**Decisión de ruta:** primero **local con Docker Compose** para validar el stack; Dokploy + dominio real después (necesario para webhook público de YCloud).

### Fase C — Puente YCloud ↔ App

| # | Paso | Estado |
|---|------|--------|
| 11 | Adaptar **webhook** para payload YCloud | ✅ `POST /webhook/ycloud` |
| 12 | Adaptar **sender** para responder vía API YCloud | ✅ `YCloudWhatsAppSender` + `WHATSAPP_PROVIDER=ycloud` |
| 13 | Verificar HMAC / secret del webhook | ✅ (si `YCLOUD_WEBHOOK_SECRET` vacío → solo warning en local) |
| 14 | Probar: mensaje → API → 200 / queued | ✅ Local E2E **sent** vía YCloud (`sendDirectly` 200) — 2026-07-29 |

### Fase D — Bot Orinoco (primer tenant)

| # | Paso |
|---|------|
| 15 | Crear cliente/tenant **Orinoco Studios** en el panel |
| 16 | Guardar credenciales YCloud de ese número en el tenant |
| 17 | Configurar **agente**: prompt Orinoco (servicios, tono, calificación, agenda demo) |
| 18 | Conectar **LLM** (API key / endpoint en servidor) |
| 19 | Prueba E2E: WhatsApp → bot responde solo en &lt;15s → visible en panel |

### Fase E — Producto (agenda + operación)

| # | Paso | Estado |
|---|------|--------|
| 20 | Agenda / demos funcionando para Orinoco | ✅ Hecho (2026-07-29) — WhatsApp real OK |
| 21 | Plantillas Meta (recordatorios) vía YCloud si hace falta | 🔄 Cableado (`appointment_reminder_2`); esperando APPROVED de Meta |
| 22 | Inbox YCloud solo como **backup humano** | ✅ Hecho — playbook §5.3 + prompt handoff en prod |

### Fase F — Extras

| # | Paso | Estado |
|---|------|--------|
| 23 | Aviso al equipo al agendar demo (WhatsApp interno; n8n/CRM opcional luego) | ✅ Hecho (código + `TEAM_NOTIFY_WHATSAPP`; deploy OK) |
| 24 | Onboarding para **otros clientes** (mismo flujo, otro tenant) | 🔄 Runbook + SQL template listos (§5.4); falta 2º número WhatsApp real |

---

## 5.1 Roadmap organizado (orden de trabajo)

| Bloque | Qué | Por qué |
|--------|-----|---------|
| **A** | Paso 20 ✅ | Bot padre agenda demos |
| **B** | Paso 23 — aviso equipo ✅ | Orinoco se entera al instante sin mirar el panel |
| **C** | Paso 22 — Inbox backup ✅ | Operativa: humano solo si hace falta |
| **D** | Hardening secretos | ⏸ Aplazado (decisión 2026-07-30) |
| **E** | Paso 21 — plantillas | 🔄 Cableado; esperando APPROVED Meta |
| **F** | Paso 24 — 2º tenant | 🔄 Checklist + script; bloqueado sin 2º número |

**Regla:** Orinoco = tenant #1 (bot padre). Todo lo que funcione aquí se clona en el paso 24.

**Crítico:** dos tenants **NO** pueden compartir el mismo WhatsApp. El webhook enruta por `phone_number_id` / `to` E.164. El 2º cliente necesita su propio número (YCloud Coexistence u otro canal).

---

## 5.4 Onboarding 2º tenant (paso 24)

### Checklist (cuando tengáis el 2º número)

1. **YCloud / Meta:** conectar el número nuevo (Coexistence o Cloud API).
2. **Webhook:** misma URL `https://agencias.orinocostudios.org/webhook/ycloud` (eventos inbound).
3. **BD:** copiar `scripts/onboard-tenant-template.sql`, sustituir placeholders (`__CLIENT_UUID__`, `__PHONE_NUMBER_ID__`, prompt, horario…), ejecutar en `agencia-postgres`.
4. **Alternativa panel:** registro en `/register` → abrir cliente en panel (badge **Pendiente**) → **Aprobar** / **Rechazar** (superadmin) → configurar **Horario de negocio** en pestaña Agencia → conectar WA (`POST /clients/{id}/connect-whatsapp` con `phone_number_id` E.164; UI de connect pendiente) → crear agente con tools nativas de agenda.
5. **Smoke:** WhatsApp al número nuevo → responde el agente de ese tenant (no Orinoco).
6. **Agenda:** “quiero cita” → slot → fila en panel de ese cliente.
7. **Opcional:** `TEAM_NOTIFY_WHATSAPP` sigue global (MVP); aviso de equipo es el mismo móvil Orinoco hasta que haya notify por tenant.

### Script

- Plantilla: `scripts/onboard-tenant-template.sql`
- Referencia Orinoco (ya aplicado): `scripts/prod-configure-orinoco-agenda.sql`

### Mientras no haya 2º número

No crear un tenant “falso” con el `+34682743315` de Orinoco: rompería el enrutado. Preparar datos del cliente (nombre, rubro, prompt, horario) y el número; al llegar el número, ejecutar el script en minutos.

---

## 5.2 Plantilla Meta — recordatorio de demo (paso 21)

El beat ya envía recordatorios (~24h antes). Fuera de la ventana 24h de chat, Meta exige **plantilla HSM**.

### Qué hacer tú en YCloud / Meta

Plantilla elegida (biblioteca): **`appointment_reminder_2`** · Español.

Body (4 variables, en este orden al enviar):
1. nombre del contacto  
2. nombre del negocio (`Orinoco Studios`)  
3. fecha  
4. hora  

Botón estático: `https://agencias.orinocostudios.org`

Cuando Meta diga **APPROVED**, el env de prod ya queda así:

```env
WHATSAPP_REMINDER_TEMPLATE_NAME=appointment_reminder_2
WHATSAPP_REMINDER_TEMPLATE_LANGUAGE=es
```

Hasta entonces los recordatorios intentarán HSM; si Meta aún no aprueba, fallarán y se reintentan en el siguiente beat (o caen a texto libre solo si quitas el env).

Código: `YCloudWhatsAppSender.send_template` + `build_reminder_template_body_parameters`.

---

## 5.3 Operativa — Inbox como backup humano (paso 22)

Canal principal: **bot Agencia IA** (webhook YCloud → Celery → LLM → respuesta).  
Backup humano: **WhatsApp Business / Inbox YCloud** del número `+34 682 743 315`.  
**No** activar el AI Agent de YCloud (chocaría con nuestro bot).

### Roles

| Quién | Hace qué |
|-------|----------|
| Bot padre | Saluda, califica, agenda demos, cancela citas |
| Equipo (móvil `TEAM_NOTIFY_WHATSAPP`) | Recibe aviso al agendar; decide si hay que intervenir |
| Humano en Inbox / Business App | Solo cuando el lead pide persona, hay queja, VIP o el bot se atasca |

### Cuándo entrar tú (humano)

1. El lead dice “quiero hablar con alguien / persona / comercial”.
2. Queja, enfado o tema legal/contratos.
3. Caso muy técnico o presupuesto grande que no debe cerrar el bot.
4. El bot se repite o no entiende tras 2–3 turnos.

### Cómo intervenir

1. Abre **WhatsApp Business** (o Inbox YCloud) del número Orinoco.
2. Responde en el mismo chat del lead.
3. Sé claro: “Hola, soy [nombre] del equipo Orinoco…”.
4. Cierra el siguiente paso (demo, llamada, email) en ese hilo.
5. Revisa la **Agenda** del panel (`/app/appointments`) si ya hay cita.

### Coexistence (importante)

El mensaje llega a la API (bot) **y** a la app Business. Si el lead escribe otra vez, el bot puede volver a responder. Por ahora:

- Tras tomar el chat, di al lead que le atiende una persona y pide 1 dato concreto (así controláis el hilo).
- Si el bot “se cuela”, una frase corta del humano basta (“te sigo yo desde aquí”).
- Pausar el agente por conversación = mejora futura (no bloquea este paso).

### Checklist operativa Orinoco

- [ ] Equipo sabe mirar avisos de `TEAM_NOTIFY_WHATSAPP`
- [ ] Alguien tiene acceso a WhatsApp Business / Inbox YCloud del `+34682743315`
- [ ] AI Agent de YCloud sigue **apagado**
- [ ] Webhook YCloud sigue **Active** → `https://agencias.orinocostudios.org/webhook/ycloud`
- [ ] Ante “quiero una persona”, el bot cede (prompt actualizado) y no fuerza agenda

---

## 6. Checklist por sistema

### En YCloud

- [x] Número Coexistence Connected  
- [x] Prueba recepción Inbox  
- [x] API Key creada (`agencia-ia-orinoco-api-ke`) — rotar si se filtró; guardar solo en secretos  
- [x] Docs envío + webhook anotadas (§8.1)  
- [x] Probar envío API (`sendDirectly`) a un número que nos escribió  
- [x] Webhook → URL pública de nuestra API  
- [x] Eventos suscritos: `whatsapp.inbound_message.received` (+ updated según dashboard)  
- [ ] Plantillas (demo reminder, follow-up) cuando hagan falta  
- [x] Inbox como backup humano (playbook §5.3) 

### En Agencia IA (esta app)

- [ ] Tenant Orinoco  
- [ ] Adaptador recibir/enviar vía YCloud  
- [ ] Agente + prompt Orinoco  
- [ ] LLM configurado  
- [ ] Panel: conversaciones, citas, conectar WhatsApp  
- [ ] Onboarding multi-cliente  

### En n8n (después)

- [ ] Lead calificado → CRM / email  
- [ ] Cita creada → aviso interno  
- [ ] Extras custom por cliente  

---

## 7. Buenas prácticas de canal (oficial, no “trucos”)

- Cumplir políticas Meta: opt-in, plantillas correctas, no spam.
- No campañas masivas el día 1.
- Coexistence: no desinstalar WhatsApp Business; abrir la app periódicamente (~cada 2 semanas).
- Retrasar respuestas “para parecer humano” **no** es regla anti-ban en API oficial; lo crítico es quality rating, quejas y volumen abusivo.
- Cerebro del bot = Agencia IA; YCloud = canal.

---

## 8. Datos actuales Orinoco (referencia)

| Campo | Valor |
|-------|--------|
| Negocio | Orinoco Studios OÜ |
| Número negocio (from) | `+34682743315` |
| WABA ID | `10509904038849970` (visto en YCloud WhatsApp accounts) |
| Integración | YCloud · Coexistence |
| Estado (2026-07-28) | Connected · Inbox OK · API Key creada |
| Negocio Meta | Verificado (WhatsApp Manager) |
| API Key (nombre) | `agencia-ia-orinoco-api-ke` |

### 8.1 Referencia técnica YCloud (para el adaptador)

Docs: [Webhook guide](https://docs.ycloud.com/reference/webhook-integration-guide) · [Events](https://docs.ycloud.com/reference/webhook-events-payloads) · [Send guide](https://docs.ycloud.com/reference/whatsapp-message-sending-guide)

#### Auth

```http
X-API-Key: <YCLOUD_API_KEY>
Content-Type: application/json
```

#### Enviar mensaje (bot / respuesta rápida)

- **Síncrono (recomendado para replies del bot):**  
  `POST https://api.ycloud.com/v2/whatsapp/messages/sendDirectly`
- **Cola asíncrona:**  
  `POST https://api.ycloud.com/v2/whatsapp/messages`

Ejemplo texto (ventana 24h):

```json
{
  "from": "+34682743315",
  "to": "+34XXXXXXXXX",
  "type": "text",
  "text": { "body": "Hola, prueba Agencia IA" }
}
```

`from` / `to` en formato **E.164** (con `+`).

#### Webhook (cuando haya URL pública de Agencia IA)

Eventos a suscribir:

| Evento | Para qué |
|--------|----------|
| `whatsapp.inbound_message.received` | Cliente escribe → entra al bot |
| `whatsapp.message.updated` | Estados sent/delivered/read/failed |

Firma: header `YCloud-Signature: t={unix},s={hmac}`  
Verificar: `HMAC-SHA256( "{t}.{raw_body}" , webhook_secret )` en hex.  
Responder **200** rápido (&lt; ~6s); procesar async (Celery).

Payload inbound (resumen): `event.type` + `whatsappInboundMessage` con `from`, `to`, `type`, `text.body`, `wabaId`, etc.

Routing multi-tenant: resolver tenant por **`to`** (nuestro número E.164) y/o `wabaId`.

#### Crear webhook en el dashboard (Fase C)

YCloud → Developers → Webhooks → crear endpoint con URL  
`https://<nuestra-api>/webhook/ycloud` (o la ruta que definamos)  
+ secret + eventos de arriba.

---

## 9. Secretos (importante)

| Secreto | Dónde vive | Dónde NO |
|---------|------------|----------|
| YCloud API Key | Gestor de contraseñas, Dokploy env, `.env` local (gitignore) | Git, MD, chat, capturas públicas |
| Webhook signing secret | Igual | Igual |

Si una key se pega en chat o se sube al repo → **revocar/rotar** en YCloud y crear una nueva.

Variables sugeridas (cuando conectemos la app):

```env
YCLOUD_API_KEY=...
YCLOUD_WEBHOOK_SECRET=...
YCLOUD_FROM_NUMBER=+34682743315
```

---

## 10. Siguiente acción inmediata

**Fase B local ✅ · Fase C código ✅.** Stack arriba:

| Servicio | URL / puerto |
|----------|----------------|
| API docs | http://localhost:8000/docs |
| Panel | http://localhost:5051 |
| Webhook YCloud | `POST http://localhost:8000/webhook/ycloud` |
| Webhook Meta | `GET/POST /webhook/whatsapp` (intacto) |

### Pendiente para que el bot **responda por WhatsApp**

1. En `backend-core/.env` pon tu key:

```env
WHATSAPP_PROVIDER=ycloud
YCLOUD_FROM_NUMBER=+34682743315
YCLOUD_API_KEY=pega_tu_key_aqui
```

2. Recrea workers:

```powershell
docker compose up -d --force-recreate backend celery-worker celery-beat
```

3. Reprueba el webhook simulado (debe acabar en `send_status=sent`).

### Ya validado en local

- Webhook → `queued`
- Celery + LLM Orinoco → genera respuesta
- Envío → `skipped` (falta `YCLOUD_API_KEY`)
- Tests: **63 passed** (YCloud + Meta sender + notifier + reminders + tasks)
- Tenant sembrado: Orinoco + agente activo (`phone_number_id=+34682743315`)

### Después (webhook real desde YCloud)

URL HTTPS pública (Dokploy/dominio o ngrok) → YCloud Developers → Webhooks → `https://…/webhook/ycloud`.

