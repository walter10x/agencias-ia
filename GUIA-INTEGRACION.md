# Guía de Integración: WhatsApp + IA + n8n

> **Última actualización**: 3 Julio 2026
> **Estado**: Meta configurado, webhook funcionando, Cloudflare Tunnel activo, pipeline verificado. **Falta: API key del LLM.**

---

## SETUP COMPLETADO (3 Julio 2026)

| Componente | Estado | Detalle |
|------------|--------|---------|
| PostgreSQL local (9 tablas, pgvector) | ✅ | `docker exec agencia-postgres psql -U postgres -d agencias_db` |
| Admin panel | ✅ | `http://localhost:5051` — login: <email-admin> / <password-admin> (rotado; ver SECURITY-TODO.md) |
| Meta WhatsApp Cloud API | ✅ | Phone Number ID: `<phone-number-id-de-ejemplo>`, Token configurado en `.env` |
| Webhook verification | ✅ | `GET /webhook/whatsapp?hub.mode=subscribe...` → 200 OK |
| Message processing | ✅ | Cliente encontrado por WhatsApp, agente encontrado, Celery encolado |
| Cloudflare Tunnel | ✅ | URL: `https://<tu-subdominio>.trycloudflare.com` |
| **LLM (IA del bot)** | ❌ | API key de OpenAI es placeholder (`sk-...`). Respuesta 401. |

Para completar: conseguir API key real de OpenAI, Anthropic, o instalar Ollama local.

---

## Arquitectura actual

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────┐
│  WhatsApp    │────▶│  Meta Cloud   │────▶│  Cloudflare    │────▶│ Backend  │
│  (cliente)   │     │  API (webhook)│     │  Tunnel (HTTPS)│    │  :8000   │
└─────────────┘     └──────────────┘     └───────────────┘     └────┬─────┘
                                                                   │
                   ┌───────────────────────────────────────────────┤
                   │                                               │
                   ▼                                               ▼
           ┌──────────────┐                               ┌──────────────┐
           │  PostgreSQL   │                               │  LLM (IA)     │
           │  (clientes,   │                               │  OpenAI /      │
           │   agentes,    │                               │  Claude /      │
           │   conversac.) │                               │  Ollama        │
           └──────────────┘                               └──────┬────────┘
                                                                 │
                                                                 ▼
                                                        ┌──────────────┐
                                                        │  Respuesta    │
                                                        │  enviada al   │
                                                        │  WhatsApp     │
                                                        └──────────────┘
```

---

## Lo que ya funciona

| Componente | Estado |
|------------|--------|
| Docker (8 contenedores) | ✅ `docker ps` |
| PostgreSQL local (9 tablas, pgvector) | ✅ |
| Admin panel (`http://localhost:5051`) | ✅ Login con <email-admin> / <password-admin> (rotado; ver SECURITY-TODO.md) |
| Crear clientes y agentes | ✅ Desde el panel o API |
| Plantillas (10 rubros, 40 herramientas para n8n) | ✅ |
| n8n (contenedor corriendo) | ✅ `http://localhost:5678` (sin flujos aún) |
| Celery + Redis para tareas asíncronas | ✅ |
| Webhook endpoint `/webhook/whatsapp` | ✅ Soporta Meta + Evolution API |
| Rate limiting (10 msg/60s por número) | ✅ |
| **Meta WhatsApp Cloud API** | ✅ Phone Number ID: `<phone-number-id-de-ejemplo>` |
| **Cloudflare Tunnel (webhook público)** | ✅ `https://<tu-subdominio>.trycloudflare.com` |
| **Message processor** | ✅ Busca cliente por WhatsApp, busca agente, encola Celery |
| **JWT secret** | ✅ Configurado |
| **Superadmin access a agentes cross-client** | ✅ Agente router arreglado |
| **PostgREST sin JWT** | ✅ SupabaseHttpClient arreglado (webhook + auth) |

## Lo que falta configurar

| Componente | Qué falta |
|------------|-----------|
| **LLM (IA del bot)** | API key real de OpenAI/Anthropic, o instalar Ollama |
| **n8n flows** | Crear workflows de webhook (posterior) |
| **Despliegue a producción** | Subir a servidor, cambiar webhook URL, dominio HTTPS |

---

## FASE 1: Credenciales de Meta

### 1.1 Obtener Phone Number ID

1. Entra a [developers.facebook.com](https://developers.facebook.com)
2. Selecciona tu App > **WhatsApp** > **Configuración de la API**
3. En la sección "Enviar mensajes de prueba" verás:
   - **Número de teléfono de prueba** (WhatsApp te da uno gratuito)
   - **Phone Number ID** (un número largo, ej: `123456789012345`)
4. Copia el Phone Number ID

### 1.2 Generar Access Token

1. En la misma pantalla de WhatsApp > Configuración de la API
2. Busca **Token de acceso temporal** (válido 24h, para desarrollo)
3. O genera uno permanente desde **Configuración del negocio** > **Usuarios del sistema** > **Generar token**
4. El token se ve así: `EAAx...largaCadena...`
5. Copia el token

### 1.3 Agregar número de prueba a WhatsApp

1. En Meta > WhatsApp > Configuración de la API > **Enviar mensajes de prueba**
2. Agrega tu número de teléfono personal como destinatario
3. Te llegará un mensaje de WhatsApp con un código de verificación
4. Ese número de Meta será el que "atiende" a tus clientes

---

## FASE 2: LLM (la IA que responde)

### Opción A: OpenAI (recomendado, ~$0.15/millon tokens)

```bash
# En el archivo backend-core/.env:
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-tu-key-real-aqui
LLM_MODEL=gpt-4o-mini
```

1. Ve a [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Crea una API key
3. Carga saldo (mínimo $5)
4. Pega la key en el `.env`

### Opción B: Anthropic Claude (~$0.25/millon tokens)

```bash
# En el archivo backend-core/.env:
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-tu-key-real-aqui
LLM_MODEL=claude-3-5-sonnet-20240620
```

1. Ve a [console.anthropic.com](https://console.anthropic.com)
2. Crea una API key
3. Pega la key en el `.env`

### Opción C: Ollama local (gratis, sin límites)

```bash
# Instalar Ollama:
brew install ollama

# Bajar un modelo:
ollama pull llama3.2

# En el archivo backend-core/.env:
LLM_PROVIDER=ollama
LLM_API_KEY=not-needed
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_MODEL=llama3.2
```

> Ollama corre en tu Mac. Como el backend está en Docker, usa `host.docker.internal` en vez de `localhost`.

---

## FASE 3: Exponer webhook con Cloudflare Tunnel

Usamos Cloudflare Tunnel (gratis, sin registro) para darle URL pública a tu backend local.

### 3.1 Instalar cloudflared

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz -o /tmp/cloudflared.tgz
tar xzf /tmp/cloudflared.tgz -C /tmp/
chmod +x /tmp/cloudflared
sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
```

### 3.2 Iniciar túnel

```bash
cloudflared tunnel --url http://localhost:8000
```

Te dará una URL tipo `https://xxx.trycloudflare.com`. Esa es tu webhook público.

> **Ya está corriendo**: `https://<tu-subdominio>.trycloudflare.com` (si se cae, reinicia el comando arriba y actualiza la URL en Meta).

### 3.3 Configurar webhook en Meta

1. En [developers.facebook.com](https://developers.facebook.com) > Tu App > WhatsApp > Configuración
2. En **Webhook**:
   - **URL de callback**: `https://<tu-subdominio>.trycloudflare.com/webhook/whatsapp`
   - **Token de verificación**: `my-verify-token`
3. Suscríbete a `messages`

---

## FASE 4: Configurar el .env

Edita el archivo `backend-core/.env` con los valores reales:

```bash
# === Meta WhatsApp Cloud API ===
WHATSAPP_PHONE_NUMBER_ID=123456789012345        # ← tu Phone Number ID real
WHATSAPP_ACCESS_TOKEN=EAAx...tuTokenRealAqui     # ← tu Access Token real
WHATSAPP_VERIFY_TOKEN=my-verify-token            # ← mismo que pusiste en Meta
WHATSAPP_API_VERSION=v22.0

# === LLM (elige UNA opción) ===
# OpenAI:
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-tu-key-real
LLM_MODEL=gpt-4o-mini

# O Anthropic:
# LLM_PROVIDER=anthropic
# LLM_API_KEY=sk-ant-tu-key-real
# LLM_MODEL=claude-3-5-sonnet-20240620

# O Ollama:
# LLM_PROVIDER=ollama
# LLM_API_KEY=not-needed
# LLM_BASE_URL=http://host.docker.internal:11434/v1
# LLM_MODEL=llama3.2

# === n8n (por ahora déjalo, luego configuramos) ===
N8N_URL=http://n8n:5678
N8N_API_KEY=

# === Seguridad ===
JWT_SECRET=cambia-esto-por-un-string-largo-y-aleatorio
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

### Aplicar cambios:

```bash
docker compose restart backend celery-worker
```

---

## FASE 5: Verificar todo

### 5.1 Health check

```bash
curl http://localhost:8000/health
# Debe responder: {"status":"ok","version":"0.1.0"}
```

### 5.2 Verificar webhook

```bash
curl "http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=my-verify-token&hub.challenge=ping123"
# Debe responder: ping123
```

### 5.3 Crear un cliente de prueba (si no tienes)

Desde el admin panel (`http://localhost:5051`):
- Ve a Clientes > Nuevo Cliente
- Nombre: "Restaurante Prueba"
- Negocio: restaurante
- WhatsApp: el número de prueba de Meta (ej: 15551234567)
- Guardar

### 5.4 Crear un agente de prueba

Desde el detalle del cliente:
- Pestaña Agentes > Nuevo Agente
- Nombre: "Bot Prueba"
- Personalidad: "Eres un asistente amable de un restaurante. Responde siempre en español."
- Sin herramientas por ahora
- Guardar

### 5.5 Enviar mensaje de prueba

Desde tu WhatsApp personal (el que agregaste como destinatario en Meta):

Envía un mensaje al **número de prueba de Meta** (el que configuraste en la Fase 1).

### 5.6 Ver logs

```bash
docker logs agencia-backend -f
docker logs agencia-celery -f
```

Debes ver:
```
INFO: Received WhatsApp message from 57xxxxxxxxx
INFO: Message processed. Agent=Bot Prueba
INFO: [WHATSAPP] Sent to 57xxxxxxxxx
```

---

## Cómo funciona el flujo (resumen técnico)

```
1. CLIENTE ESCRIBE POR WHATSAPP
   → Meta recibe el mensaje
   → Meta hace POST a https://abc123.ngrok-free.app/webhook/whatsapp

2. BACKEND RECIBE WEBHOOK (webhook.py)
   → Detecta formato Meta (object == "whatsapp_business_account")
   → Extrae: teléfono, texto, nombre
   → Valida teléfono (mín 10 dígitos)

3. PROCESADOR DE MENSAJES (message_processor.py)
   → Busca cliente por número de WhatsApp en BD
   → Busca agentes activos del cliente
   → Rate limiting (10 msg/60s por número vía Redis)
   → Sanitiza mensaje (borra bytes nulos, trunca a 4096 chars)
   → Encola tarea Celery (responde en < 500ms)

4. CELERY WORKER (tasks.py)
   → Carga el agente de la BD
   → Construye system prompt con personalidad del agente
   → Convierte herramientas a formato OpenAI function-calling
   → Corre LangGraph Agent con LLM:
      - Si el LLM decide responder: genera texto
      - Si el LLM decide usar herramienta: POST a n8n webhook
   → Envía respuesta vía Meta Cloud API:
      POST https://graph.facebook.com/v22.0/{PHONE_ID}/messages

5. CLIENTE RECIBE RESPUESTA EN WHATSAPP
```

---

## FASE 6: n8n (flujos automáticos) - FUTURO

Una vez que el bot responda texto, configuramos n8n:

1. Abrir `http://localhost:5678` y crear cuenta admin
2. Crear workflows de webhook (ej: `reservar_mesa`)
3. Conectar con Google Calendar, Sheets, APIs externas
4. Activar workflows

Esto lo hacemos después. Primero texto, luego automatizaciones.

---

## Troubleshooting

### Meta rechaza el webhook

- Verifica que ngrok esté corriendo y la URL sea HTTPS
- El `verify_token` en `.env` debe ser **exactamente igual** al de Meta
- Prueba: `curl "https://TUNGROK.ngrok-free.app/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=my-verify-token&hub.challenge=test"`

### El bot no responde

- Revisa `docker logs agencia-celery` para ver errores del LLM
- Verifica que el cliente tenga WhatsApp number = el número que escribió
- Verifica que el agente esté activo
- Verifica que la API key del LLM sea válida

### Token de Meta expiró

Los tokens temporales duran 24h. Para desarrollo, regenera uno nuevo en Meta Developers.

### Cloudflare Tunnel se cayó

El túnel se cae después de un tiempo. Para reiniciarlo:

```bash
cloudflared tunnel --url http://localhost:8000
```

Luego actualiza la URL en Meta Developers si cambió.

---

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `backend-core/.env` | Variables de entorno (Meta, LLM, n8n, Redis) |
| `backend-core/app/infrastructure/whatsapp/webhook.py` | Recibe mensajes de Meta + Evolution API |
| `backend-core/app/infrastructure/whatsapp/message_processor.py` | Busca cliente/agente, encola Celery |
| `backend-core/app/infrastructure/config/tasks.py` | Celery: LLM inference, tools, enviar respuesta |
| `backend-core/app/infrastructure/ai/tools.py` | Convierte herramientas a OpenAI format, ejecuta n8n |
| `backend-core/app/infrastructure/templates/data.py` | 10 plantillas con 40 herramientas predefinidas |
| `backend-core/app/infrastructure/config/settings.py` | Configuración Pydantic (todas las variables) |
| `docker-compose.yml` | Servicios: backend, n8n, redis, celery, postgres, postgrest |
| `docker/postgres/init.sql` | Esquema de BD + migraciones |
