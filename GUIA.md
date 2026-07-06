# 🚀 Guía Completa — Agencia IA (de Cero a Producción)

> **¿Qué es Agencia IA?**  
> Plataforma multi-tenant para crear agentes de IA que atienden clientes por WhatsApp.  
> Una peluquería, un restaurante, un contador... cada uno tiene su agente entrenado con su negocio.

---

## Índice

1. [Requisitos](#1-requisitos)
2. [Clonar y entender el proyecto](#2-clonar-y-entender-el-proyecto)
3. [Crear cuenta en Supabase](#3-crear-cuenta-en-supabase)
4. [Configurar el LLM (cerebro IA)](#4-configurar-el-llm-cerebro-ia)
5. [Configurar `.env` — variables de entorno](#5-configurar-env--variables-de-entorno)
6. [Levantar todo con Docker](#6-levantar-todo-con-docker)
7. [Probar la API](#7-probar-la-api)
8. [Conectar WhatsApp (Meta Cloud API)](#8-conectar-whatsapp-meta-cloud-api)
9. [n8n — Flujos de automatización](#9-n8n--flujos-de-automatización)
10. [Flujo completo de prueba](#10-flujo-completo-de-prueba)
11. [Leads y Prospección Automática](#11-leads-y-prospección-automática)
12. [Feedback y Calificación](#12-feedback-y-calificación)
13. [Plantillas de Servicio](#13-plantillas-de-servicio)
14. [Landing Pages (Próximamente)](#14-landing-pages-próximamente)
15. [Novedades y Changelog](#15-novedades-y-changelog)

---

## 1. Requisitos

### Software obligatorio

| Herramienta | ¿Para qué? | Descarga |
|---|---|---|
| **Docker Desktop** | Ejecutar todos los servicios (API, frontend, Redis, WhatsApp, n8n) | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Cuenta Supabase** (gratis) | Base de datos PostgreSQL con pgvector para RAG | [supabase.com](https://supabase.com) |
| **Cuenta LLM** (gratis) | Cerebro de la IA — elige una opción abajo | Ver sección 4 |

### Opciones de LLM (elige una)

| Proveedor | Costo | Modelo recomendado |
|---|---|---|
| **OpenCode** | Gratis (créditos) | Usa el modelo por defecto |
| **Google Gemini** | Gratis (límite generoso) | `gemini-2.0-flash` |
| **OpenAI** | Pagas por uso (~$0.15/1M tokens) | `gpt-4o-mini` |
| **Ollama** (local) | Gratis (tu propia máquina) | `llama3`, `mistral` |

> **Recomendación para empezar**: Gemini (gratis, sin tarjeta). Luego migras a OpenAI si necesitas más calidad.

---

## 2. Clonar y entender el proyecto

### Descargar

```bash
# Opción A: Git clone
git clone <url-del-repo> Agencia-ia-Au
cd Agencia-ia-Au

# Opción B: Descargar ZIP y extraer en C:\Users\walte\Desktop\Agencia-ia-Au
```

### Estructura de carpetas

```
Agencia-ia-Au/
├── docker-compose.yml          ← Orquesta todos los servicios
├── GUIA.md                      ← Esta guía :)
│
├── backend-core/                ← Motor de IA (FastAPI + LangGraph)
│   ├── .env.example             ← Template de variables de entorno
│   ├── .env                     ← Tú creas este archivo (copiando .env.example)
│   ├── Dockerfile               ← Imagen Docker del backend
│   ├── requirements.txt         ← Dependencias Python
│   ├── migrations/
│   │   └── 001_initial_schema.sql ← SQL para crear tablas en Supabase
│   ├── app/
│   │   ├── main.py              ← Punto de entrada FastAPI
│   │   ├── domain/              ← Entidades y reglas de negocio
│   │   ├── application/         ← Casos de uso (crear cliente, crear agente…)
│   │   └── infrastructure/      ← HTTP routers, WhatsApp webhook, Supabase, AI
│   └── tests/                   ← Tests unitarios e integración
│
├── frontend-dashboard/          ← Panel de control (React + Vite + Tailwind)
│   ├── Dockerfile               ← Build con Node, serve con nginx
│   ├── src/
│   │   ├── pages/               ← DashboardPage, ClientsPage, AgentsPage…
│   │   └── components/          ← Sidebar, Toast, AgentForm, ClientForm…
│   └── dist/                    ← Build de producción (servido por nginx)
│
└── .agents/                     ← Skills y configuración del agente OpenCode
```

### ¿Qué hace cada servicio?

| Servicio | Puerto | Descripción |
|---|---|---|
| **frontend** | `5050` | Dashboard React — gestionás clientes y agentes IA desde el navegador |
| **backend** | `8000` | API FastAPI — lógica de negocio, CRUD de clientes/agentes, webhook WhatsApp |
| **redis** | `6379` | Caché y broker de mensajes para Celery |
| **celery-worker** | — | Tareas asíncronas (procesar mensajes, generar PDFs, embeddings) |
| **celery-beat** | — | Scheduler de tareas periódicas (recordatorios de citas) |
| **n8n** | `5678` | Automatización visual — flujos secundarios (ej: sincronizar CRM) |

---

## 3. Crear cuenta en Supabase

Supabase es tu base de datos PostgreSQL con pgvector para búsqueda semántica (RAG). El plan gratuito da 500 MB de datos — más que suficiente para empezar.

### Paso a paso

1. **Crear cuenta**  
   Ve a [supabase.com](https://supabase.com) → "Start your project" → Inicia sesión con GitHub.

2. **Crear proyecto**  
   - Organization: la que viene por defecto
   - Name: `agencia-ia`
   - Database Password: **generá una segura y guardala** (ej: `MiPasswordSeguro123!`)
   - Region: la más cercana (ej: `South America (São Paulo)` o `US East`)
   - Plan: **Free**
   - Click "Create project" → Esperá 2 minutos.

3. **Copiar credenciales**  
   Ve a Project Settings → API:
   - Copia **Project URL** → formato: `https://xxxxxxxxxxxx.supabase.co`
   - Copia **service_role key** → formato: `eyJhbGciOiJIUzI1NiIs...`  
     ⚠️ Es la **service_role**, NO la `anon` key.

   > Estas dos credenciales van en tu `.env`. Guardalas ya.

4. **Ejecutar la migración SQL**  
   Ve a **SQL Editor** (en el menú izquierdo) → "New query".  
   Pega TODO el contenido del archivo `backend-core/migrations/001_initial_schema.sql`:

   ```sql
   -- Habilita extensión pgvector para búsqueda semántica RAG
   CREATE EXTENSION IF NOT EXISTS vector;

   -- Tabla de clientes (negocios multi-tenant)
   CREATE TABLE clients (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       name TEXT NOT NULL,
       business_type TEXT NOT NULL CHECK (business_type IN (
           'peluqueria', 'bar', 'restaurante', 'contador',
           'fonatero', 'tienda', 'gimnasio', 'clinica', 'otro'
       )),
       whatsapp_number TEXT NOT NULL UNIQUE,
       is_active BOOLEAN NOT NULL DEFAULT true,
       created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );

   CREATE INDEX idx_clients_whatsapp ON clients(whatsapp_number);
   CREATE INDEX idx_clients_active ON clients(is_active) WHERE is_active = true;
   CREATE INDEX idx_clients_business_type ON clients(business_type);

   -- Tabla de agentes IA (cada cliente puede tener varios)
   CREATE TABLE agents (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
       name TEXT NOT NULL,
       personality TEXT NOT NULL CHECK (length(personality) >= 10),
       tools JSONB NOT NULL DEFAULT '[]'::jsonb,
       knowledge_base_refs TEXT[] NOT NULL DEFAULT '{}',
       is_active BOOLEAN NOT NULL DEFAULT true,
       created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );

   CREATE INDEX idx_agents_client ON agents(client_id);
   CREATE INDEX idx_agents_active ON agents(is_active) WHERE is_active = true;

   -- Tabla de conversaciones (chats de WhatsApp)
   CREATE TABLE conversations (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
       agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
       wa_phone_number TEXT NOT NULL,
       status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed', 'archived')),
       created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );

   CREATE INDEX idx_conversations_client ON conversations(client_id);
   CREATE INDEX idx_conversations_phone ON conversations(wa_phone_number);

   -- Tabla de mensajes individuales
   CREATE TABLE messages (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
       role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
       content TEXT NOT NULL,
       tokens_used INTEGER DEFAULT 0,
       created_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );

   CREATE INDEX idx_messages_conversation ON messages(conversation_id);
   CREATE INDEX idx_messages_created ON messages(conversation_id, created_at);

   -- Tabla de base de conocimiento RAG (documentos con embeddings)
   CREATE TABLE knowledge_base (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
       title TEXT NOT NULL,
       content TEXT NOT NULL,
       embedding vector(1536),
       source_url TEXT,
       created_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );

   CREATE INDEX idx_kb_client ON knowledge_base(client_id);
   CREATE INDEX idx_kb_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

   -- Función para actualizar updated_at automáticamente
   CREATE OR REPLACE FUNCTION update_timestamp()
   RETURNS TRIGGER AS $$
   BEGIN
       NEW.updated_at = now();
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;

   -- Triggers para updated_at en todas las tablas
   CREATE TRIGGER trg_clients_updated
       BEFORE UPDATE ON clients
       FOR EACH ROW EXECUTE FUNCTION update_timestamp();

   CREATE TRIGGER trg_agents_updated
       BEFORE UPDATE ON agents
       FOR EACH ROW EXECUTE FUNCTION update_timestamp();

   CREATE TRIGGER trg_conversations_updated
       BEFORE UPDATE ON conversations
       FOR EACH ROW EXECUTE FUNCTION update_timestamp();

   -- Row Level Security: solo el dueño (admin) puede ver/editar
   ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
   ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
   ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
   ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
   ALTER TABLE knowledge_base ENABLE ROW LEVEL SECURITY;

   -- Política: el service_role (backend) tiene acceso total
   CREATE POLICY "Service role full access" ON clients FOR ALL USING (true);
   CREATE POLICY "Service role full access" ON agents FOR ALL USING (true);
   CREATE POLICY "Service role full access" ON conversations FOR ALL USING (true);
   CREATE POLICY "Service role full access" ON messages FOR ALL USING (true);
   CREATE POLICY "Service role full access" ON knowledge_base FOR ALL USING (true);
   ```

   Click **"Run"**. Si ves "Success. No rows returned", todo perfecto.

   Para verificar: ve a **Table Editor** (menú izquierdo). Deberías ver 5 tablas:  
   `clients`, `agents`, `conversations`, `messages`, `knowledge_base`.

---

## 4. Configurar el LLM (cerebro IA)

El backend habla con cualquier LLM compatible con API OpenAI. Elige tu proveedor:

### Opción A: Google Gemini (gratis, recomendado)

1. Ve a [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Click "Create API Key" → Copia la key.
3. Usa la URL base: `https://generativelanguage.googleapis.com/v1beta/openai/`

### Opción B: OpenAI (calidad máxima, pagas por uso)

1. Ve a [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key" → Copia la key (solo se muestra una vez).
3. No necesitas URL base (usa la por defecto).

### Opción C: OpenCode (gratis con créditos)

1. Usa tu API key de OpenCode.
2. URL base: la que te proporcione OpenCode.

### Opción D: Ollama (local, 100% gratis)

1. Instala [Ollama](https://ollama.com).
2. Descarga un modelo: `ollama pull llama3.2`
3. La URL base es `http://localhost:11434/v1` (si corre en tu máquina host) o `http://host.docker.internal:11434/v1` (desde Docker en Windows/Mac).

---

## 5. Configurar `.env` — variables de entorno

### Crear el archivo

```bash
# Desde la raíz del proyecto:
cd backend-core
copy .env.example .env
```

### Abrí `.env` con tu editor y completá todas las variables

Este es el template completo que debes llenar:

```env
# === Base de datos (Supabase) ===
# Pega la URL y service_role key que copiaste en la sección 3
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# === LLM Provider (agnostic) ===
# Elige UNO de estos bloques. Comenta o borra los otros.

# --- Opción 1: OpenAI ---
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-...
LLM_BASE_URL=
LLM_MODEL=gpt-4o-mini

# --- Opción 2: Google Gemini (gratis) ---
# LLM_PROVIDER=openai
# LLM_API_KEY=AIzaSy...
# LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
# LLM_MODEL=gemini-2.0-flash

# --- Opción 3: OpenCode ---
# LLM_PROVIDER=opencode
# LLM_API_KEY=tu-api-key-de-opencode
# LLM_BASE_URL=https://api.opencode.ai/v1
# LLM_MODEL=opencode-default

# --- Opción 4: Ollama (local, gratis) ---
# LLM_PROVIDER=ollama
# LLM_API_KEY=not-needed
# LLM_BASE_URL=http://host.docker.internal:11434/v1
# LLM_MODEL=llama3.2

# === Claves legacy (opcional si usas LLM agnostic) ===
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# === WhatsApp Cloud API (Meta) ===
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_VERIFY_TOKEN=my-verify-token

# === n8n Automatización ===
N8N_URL=http://n8n:5678
N8N_API_KEY=

# === Redis / Celery ===
# Estos ya apuntan a los contenedores Docker. No cambiar.
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# === Seguridad ===
# CAMBIAR en producción por una cadena larga aleatoria
JWT_SECRET=change-me-in-production-use-a-long-random-string
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# === App ===
DEBUG=true
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://localhost:5050"]
```

### Resumen: 4 variables críticas

| Variable | ¿Dónde la consigo? | Obligatoria |
|---|---|---|
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL | ✅ |
| `SUPABASE_SERVICE_KEY` | Supabase → Project Settings → API → service_role key | ✅ |
| `LLM_API_KEY` | Sección 4 de esta guía | ✅ |
| `LLM_PROVIDER` | `openai` (también para Gemini/Ollama/OpenCode) | ✅ |

> **Nota importante**: Gemini y Ollama usan el adaptador `openai` porque sus APIs son compatibles con el formato OpenAI. Por eso `LLM_PROVIDER=openai` aunque uses Gemini.

---

## 6. Levantar todo con Docker

### Comando mágico

Desde la raíz del proyecto (`C:\Users\walte\Desktop\Agencia-ia-Au`):

```bash
docker-compose up -d
```

Esto levanta **6 contenedores** en segundo plano. La primera vez tarda unos minutos (descarga imágenes, instala dependencias).

### Verificar que todo anda

```bash
docker-compose ps
```

Debes ver 6 servicios con `Up`:

```
NAME                STATUS          PORTS
agencia-frontend    Up              0.0.0.0:5050->80/tcp
agencia-backend     Up              0.0.0.0:8000->8000/tcp
agencia-redis       Up (healthy)    0.0.0.0:6379->6379/tcp
agencia-celery      Up
agencia-n8n         Up              0.0.0.0:5678->5678/tcp
```

### Puertos — qué abrir en el navegador

| URL | ¿Qué es? |
|---|---|
| `http://localhost:5050` | Dashboard — panel de control para gestionar clientes y agentes |
| `http://localhost:8000/docs` | Swagger de la API — probar endpoints manualmente |
| `http://localhost:8000/health` | Health check — responde `{"status":"ok"}` |
| `http://localhost:5678` | n8n — editor visual de automatizaciones |

### Comandos útiles de Docker

```bash
# Ver logs de un servicio
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Reiniciar un servicio
docker-compose restart backend

# Detener todo
docker-compose down

# Detener todo y borrar volúmenes (⚠️ borra datos de n8n)
docker-compose down -v

# Reconstruir imágenes después de cambiar código
docker-compose up -d --build
```

---

## 7. Probar la API

### Health Check

```bash
curl http://localhost:8000/health
```

Respuesta: `{"status":"ok","version":"0.1.0"}` ✅

### Crear un cliente

Opción A — **Swagger UI** (`http://localhost:8000/docs`):

1. Abrí `http://localhost:8000/docs`
2. Buscá `POST /api/v1/clients`
3. Click "Try it out"
4. Pegá este JSON:

```json
{
  "name": "Peluquería Estilo Total",
  "business_type": "peluqueria",
  "whatsapp_number": "5491134567890",
  "is_active": true
}
```

5. Click "Execute"

Opción B — **curl**:

```bash
curl -X POST http://localhost:8000/api/v1/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Peluquería Estilo Total",
    "business_type": "peluqueria",
    "whatsapp_number": "5491134567890",
    "is_active": true
  }'
```

### Crear un agente IA

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "<ID-DEL-CLIENTE-QUE-CREASTE>",
    "name": "Asistente de Peluquería",
    "personality": "Sos un asistente amable de una peluquería. Ayudás a reservar turnos, informás precios y recomendás servicios. Siempre saludás con '¡Hola! ¿En qué puedo ayudarte hoy?'",
    "tools": ["agendar_turno", "consultar_precios", "enviar_ubicacion"],
    "is_active": true
  }'
```

> **Tip**: El `client_id` lo obtenés de la respuesta del POST anterior, o haciendo un `GET /api/v1/clients`.

### Opción C — Dashboard

Abrí `http://localhost:5050`:
1. Ve a la sección **Clientes** → "Nuevo Cliente" → llená el formulario
2. Ve a la sección **Agentes** → "Nuevo Agente" → seleccioná el cliente, definí personalidad

---

## 8. Conectar WhatsApp (Meta Cloud API)

El canal es **Meta WhatsApp Cloud API**. Cada tenant conecta su número
guardando su `phone_number_id` y `access_token` (cifrado) vía el endpoint
`POST /clients/{client_id}/connect-whatsapp`. El alta en Meta Business, la
suscripción del webhook y su verificación están detalladas en
`GUIA-INTEGRACION.md`.

Resumen del cableado:

| Campo | Valor |
|---|---|
| Webhook URL (Meta) | `https://<tu-dominio>/webhook/whatsapp` |
| Verify token | `WHATSAPP_VERIFY_TOKEN` (variable de entorno) |
| Routing multi-tenant | por `phone_number_id` del payload de Meta |

### Verificar conexión

Enviá un mensaje de WhatsApp al número de prueba de Meta desde otro teléfono.  
Revisá los logs del backend:

```bash
docker-compose logs -f backend
```

Deberías ver algo como:
```
INFO: Received WhatsApp message from 54911XXXXXXXX
INFO: Processing message for client Peluquería Estilo Total
```

---

## 9. n8n — Flujos de automatización

> **El agente piensa, n8n ejecuta.** Sin n8n tu agente solo habla. Con n8n tu agente HACE cosas: agenda citas, consulta stock, crea pedidos, envía recordatorios.

n8n es un editor visual de automatizaciones que corre en `http://localhost:5678`. Se usa para conectar al agente IA con acciones reales: Google Calendar, Google Sheets, APIs externas, emails, WhatsApp proactivo.

### 9.1 Abrir n8n y crear cuenta

Abrí `http://localhost:5678` en el navegador. La primera vez te pide crear un usuario (email + contraseña). Guardalos — es tu cuenta de administrador.

### 9.2 Cómo funciona la conexión Agente → n8n

El flujo es simple:

```
Agente IA detecta intención → elige tool → POST al webhook de n8n
→ n8n ejecuta la acción (Google Calendar, API, etc.)
→ n8n responde con el resultado
→ Agente IA le informa al cliente con datos REALES
```

El backend ya está configurado para llamar a n8n automáticamente. Lo único que tenés que hacer es crear los flujos en n8n para cada tool que quieras exponer.

### 9.3 Ejemplo paso a paso: Tool `agendar_mesa` para un restaurante

Este es el ejemplo más común. Vas a crear la tool en el Dashboard y el flujo en n8n.

#### 🔹 Paso A: Crear la tool en el Dashboard

Andá a `http://localhost:5050/agents` → seleccioná el agente → sección **Tools** → agregar nueva:

| Campo | Valor |
|-------|-------|
| **Nombre** | `agendar_mesa` |
| **Descripción** | `Reserva una mesa en el restaurante para una fecha, hora y cantidad de personas. Usar cuando el cliente pide reservar, agendar mesa, o hacer una reservación. Parámetros: fecha (YYYY-MM-DD), hora (HH:MM), personas (número), nombre (texto).` |
| **Endpoint** | `http://n8n:5678/webhook/agendar-mesa` |
| **Método** | `POST` |

> ⚠️ **La descripción es CLAVE.** El agente decide qué tool usar leyendo ÚNICAMENTE el nombre y la descripción. Escribila como si le explicaras a una persona qué hace, cuándo usarla, y qué datos necesita. Incluí frases textuales que diría un cliente real (ej: "reservar", "agendar mesa", "hacer una reservación").

#### 🔹 Paso B: Crear el flujo en n8n

Abrí `http://localhost:5678` → **"Add workflow"**:

**Nodo 1 — Webhook:**
- Buscá "Webhook" en el panel derecho y arrastralo
- HTTP Method: `POST`
- Path: `agendar-mesa`
- Response Mode: `Last Node`

**Nodo 2 — IF (opcional, para manejar errores):**
- Agregá un nodo "IF" para verificar que los datos lleguen completos
- Condición: `{{ $json.body.fecha }}` existe Y `{{ $json.body.hora }}` existe

**Nodo 3 — Google Calendar:**
- Agregá el nodo "Google Calendar"
- Conectá tu cuenta de Google (te va a pedir autorización la primera vez)
- Operation: `Create Event`
- Calendar: elegí el calendario del restaurante
- Start: `{{ $json.body.fecha }}T{{ $json.body.hora }}:00`
- Summary: `Reserva: {{ $json.body.nombre }} — {{ $json.body.personas }} personas`

**Nodo 4 — Respond to Webhook:**
- Este es el ÚLTIMO nodo (n8n responde al agente con lo que salga de acá)
- Agregá un nodo "Respond to Webhook"
- Respond With: `JSON`
- Response Body:
```json
{
  "status": "confirmado",
  "fecha": "{{ $json.body.fecha }}",
  "hora": "{{ $json.body.hora }}",
  "personas": "{{ $json.body.personas }}",
  "mensaje": "Mesa para {{ $json.body.personas }} personas confirmada."
}
```

**Click "Test Workflow"** (arriba a la derecha) para ejecutar una prueba. Después activá el flujo con el toggle **"Active"** (esquina superior derecha, se pone verde).

#### 🔹 Paso C: Probar que funciona

```bash
# Probá que n8n responde correctamente:
curl -X POST http://localhost:5678/webhook/agendar-mesa \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "agendar_mesa",
    "fecha": "2026-06-15",
    "hora": "21:00",
    "personas": 4,
    "nombre": "Carlos López"
  }'
```

Si ves `{"status": "confirmado", ...}`, ¡ya está! El agente ahora puede reservar mesas de verdad. Para probar con WhatsApp real, escribile al número del negocio: *"Hola, ¿tienen mesa para 4 esta noche a las 21?"*

### 9.4 Cómo escribir buenas descripciones de tools

La descripción de la tool es **lo único que el agente lee** para decidir si usarla. Si es mala, la tool nunca se activa.

#### ❌ Descripciones que NO funcionan

| Descripción | Por qué falla |
|-------------|---------------|
| `"Tool para agendar"` | Muy vaga. El agente no sabe para qué sirve |
| `"POST /webhook/agendar-mesa"` | Es un endpoint, no una descripción funcional |
| `"Agenda cosas en el calendario"` | "Cosas" no le dice nada al agente |

#### ✅ Descripciones que SÍ funcionan

| Descripción | Por qué funciona |
|-------------|------------------|
| `"Reserva una mesa en el restaurante para una fecha, hora y cantidad de personas. Usar cuando el cliente pide 'reservar', 'agendar una mesa', o 'hacer una reservación'. Parámetros: fecha (YYYY-MM-DD), hora (HH:MM), personas (número), nombre (texto)."` | Dice QUÉ hace, CUÁNDO usarlo, y QUÉ datos necesita |
| `"Consulta la disponibilidad de turnos para peluquería. Usar cuando el cliente pregunta '¿cuándo tienen turno?', '¿hay lugar?', o quiere saber horarios."` | Incluye frases textuales del cliente |
| `"Envía el menú del día. Usar cuando el cliente pide 'menú', 'carta', 'qué hay de comer', 'platos del día'."` | Palabras clave exactas |

**Fórmula**: `[Qué hace la tool]. Usar cuando el cliente [frases textuales del cliente]. Parámetros: [lista de datos necesarios].`

### 9.5 Herramienta genérica `tools` (para el agente)

Si preferís manejar todas las tools con UN solo webhook, podés crear un flujo genérico:

1. Nodo **Webhook**: Path `tools`, Method `POST`
2. Nodo **Switch**: según `{{ $json.body.tool }}` redirige a la rama correspondiente
3. Cada rama ejecuta la acción específica (Google Calendar, Google Sheets, etc.)
4. Nodo **Respond to Webhook** al final de CADA rama

El agente envía `{ "tool": "agendar_mesa", "fecha": "...", ... }` y n8n decide qué hacer según el nombre de la tool.

> **Recomendación**: Para proyectos chicos (< 5 tools), usá un flujo por tool (más simple de mantener). Para proyectos grandes, usá el flujo genérico con Switch (todo en un solo lugar).

### 9.6 Ideas de flujos para empezar

Estos son los flujos que más valor generan, ordenados por impacto:

| # | Flujo n8n | ¿Qué hace? | Dificultad |
|---|-----------|------------|:----------:|
| 1 | **Agendar en Google Calendar** | Webhook → Google Calendar → Responder | ⭐ Fácil |
| 2 | **Consultar Google Sheets** | Webhook → Google Sheets (leer) → Responder | ⭐ Fácil |
| 3 | **Enviar recordatorio por WhatsApp** | Celery beat → recordatorio vía Meta Cloud API (ya nativo, sin n8n) | ⭐⭐ Medio |
| 4 | **Crear pedido en e-commerce** | Webhook → Shopify/WooCommerce API → Responder | ⭐⭐ Medio |
| 5 | **Notificar a un humano** | Webhook → Enviar WhatsApp/email al dueño | ⭐ Fácil |
| 6 | **Buscar en base de conocimiento** | Webhook → HTTP Request a Supabase → Responder | ⭐⭐ Medio |
| 7 | **Encuesta post-servicio** | n8n Schedule (24h después) → WhatsApp al cliente | ⭐⭐ Medio |

### 9.7 Solución de problemas comunes en n8n

| Problema | Causa probable | Solución |
|----------|---------------|----------|
| El flujo no recibe nada | Webhook no está "Active" | Activá el toggle verde en la esquina superior derecha |
| Error "Connection refused" | n8n no está corriendo | `docker-compose ps` — verificá que `agencia-n8n` esté Up |
| Google Calendar no conecta | Cuenta no autorizada | En el nodo Google Calendar, click "Connect" y autorizá de nuevo |
| El agente no usa la tool | Descripción mala | Reescribila usando la fórmula de la sección 9.4 |
| n8n responde pero el agente no entiende | Formato JSON incorrecto | La respuesta DEBE ser JSON válido con `Content-Type: application/json` |
| "Workflow execution failed" | Error en algún nodo | Click en "Executions" (menú izquierdo) → revisá el error en detalle |

### 9.8 Buenas prácticas

- ✅ **Activá el flujo** (toggle Active) siempre después de probarlo
- ✅ **Probá con curl primero**, después con WhatsApp
- ✅ **Usá nombres descriptivos**: `agendar-mesa`, no `webhook1`
- ✅ **Respondé siempre JSON**: el agente espera `Content-Type: application/json`
- ✅ **Manejo de errores**: si algo falla, respondé `{ "status": "error", "mensaje": "..." }` en vez de un error 500
- ✅ **Guardá las credenciales** en n8n, nunca en el código
- ❌ **No pongas lógica de negocio compleja** en n8n — para eso está el backend
- ❌ **No expongas n8n a internet** sin autenticación — `:5678` es solo local

---

## 10. Flujo completo de prueba

Probemos el sistema de punta a punta. Vas a simular un cliente real:

### Escenario: Cliente de peluquería pide turno

```
👤 Cliente (WhatsApp):  Hola, ¿tienen turno para mañana a las 15?
🤖 Agente IA:           ¡Hola! Soy el asistente de Peluquería Estilo Total.
                        Déjame revisar la disponibilidad...
                        ¡Sí! Tenemos un lugar mañana a las 15:00.
                        ¿Querés que lo reserve a tu nombre?

👤 Cliente:             Sí, por favor. Soy María.
🤖 Agente IA:           ¡Listo, María! Tu turno está confirmado para
                        mañana 10/06/2026 a las 15:00.
                        Te esperamos en Av. Principal 123.
                        ¿Necesitás algo más?
```

### Lo que pasa por detrás

```
WhatsApp ──→ Meta Cloud API ──→ Webhook Backend (:8000) ──→ LangGraph (agente IA)
                                    │
                                    ├── Resuelve tenant por phone_number_id en Supabase
                                    ├── Carga personalidad y tools del agente
                                    ├── Consulta LLM (Gemini/OpenAI/Ollama)
                                    ├── Si detecta "tool": agendar_cita (nativa)
                                    │   └──→ AppointmentRepository ──→ Supabase
                                    │                         └──→ Confirmación
                                    └── Guarda mensajes en Supabase
                                        │
                                        └──→ Meta Cloud API ──→ WhatsApp (respuesta al cliente)
```

### Verificar en el Dashboard

Abrí `http://localhost:5050`:
- **Dashboard**: ves métricas de conversaciones activas
- **Clientes**: ves los clientes registrados
- **Agentes**: ves los agentes IA configurados
- **Conversaciones**: podés ver el historial de cada chat

### Verificar en Supabase

Ve a Supabase → Table Editor:
- `conversations`: aparece una nueva conversación
- `messages`: aparecen los mensajes del cliente y del agente

---

## 11. Leads y Prospección Automática

> El agente puede **salir a buscar clientes activamente**, no solo esperar mensajes.  
> Incluye pipeline de leads, mensajes proactivos y clasificación automática.

### 11.1 Pipeline de Leads

Los leads se gestionan desde `http://localhost:5050/leads` o via API:

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/leads` | `POST` | Crear un lead manualmente |
| `/api/v1/leads` | `GET` | Listar leads con filtros (client_id, status, source, search) |
| `/api/v1/leads/{id}` | `PATCH` | Actualizar status, score o notas |
| `/api/v1/leads/{id}/send-message` | `POST` | Enviar mensaje proactivo al lead |
| `/api/v1/leads/stats` | `GET` | Estadísticas del pipeline |

Estados del lead: `new` → `contacted` → `interested` / `not_interested` → `converted` / `archived`

Cada lead tiene un **score** (0-100) que representa la probabilidad de conversión.

### 11.2 Mensajes Proactivos

Desde la página de detalle del lead (`/leads/{id}`) podés:

1. **Cambiar estado** del lead con un clic
2. **Enviar mensaje** directo al lead desde el panel
3. **Ver feedback** recibido de ese lead

El mensaje se envía via WhatsApp Cloud API (mismo webhook que los mensajes entrantes).

### 11.3 Base de datos

La tabla `leads` en Supabase almacena:

```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    phone TEXT NOT NULL,
    name TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    source TEXT,
    score INTEGER DEFAULT 0,
    notes TEXT,
    last_contacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 11.4 Clasificación Automática (próximamente)

Cuando un lead responde, el agente clasificará la intención automáticamente:
- **Interesado** → status `interested`, programa seguimiento
- **No interesado** → archiva
- **Score** se actualiza según la respuesta

### 11.5 Seguimiento Programado (próximamente)

- n8n + tareas programadas para re-contactar leads
- "Si no responde en 3 días → re-enviar"
- "Si interesado → enviar oferta en 1 día"

---

## 12. Feedback y Calificación

> Sistema de calificación post-servicio. Los clientes califican la atención y dejan comentarios.

### 12.1 Endpoints

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/feedback` | `POST` | Crear feedback (rating 1-5 + comentario opcional) |
| `/api/v1/feedback` | `GET` | Listar feedbacks por cliente |
| `/api/v1/feedback/stats` | `GET` | Estadísticas: promedio, distribución de ratings |

### 12.2 Cómo se usa

El feedback se muestra en la página de detalle del lead (`/leads/{id}`):

```
⭐ ⭐ ⭐ ⭐ ⭐  "Muy buena atención, resolvieron rápido"
⭐ ⭐ ⭐ ⭐     "Buen servicio, llegaron a tiempo"
```

Cada feedback tiene:
- **Rating**: 1 a 5 estrellas
- **Comentario**: texto opcional
- **Vinculación**: a un lead y/o conversación específica

### 12.3 Estadísticas

El endpoint `/api/v1/feedback/stats` devuelve:

```json
{
  "total": 42,
  "average_rating": 4.3,
  "rating_distribution": { "1": 2, "2": 1, "3": 5, "4": 15, "5": 19 }
}
```

### 12.4 Base de datos

```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 13. Plantillas de Servicio

> Templates preconfigurados de agente IA + tools según el rubro del negocio.  
> Creá un agente listo para usar en segundos sin escribir personalidad ni tools manualmente.

### 13.1 Listar Plantillas Disponibles

Desde la API:

```bash
GET /api/v1/templates
```

Ejemplo de respuesta:

```json
{
  "templates": [
    {
      "slug": "restaurante",
      "name": "Restaurante",
      "emoji": "🍕",
      "description": "Atención al cliente para restaurantes: reservas, menú, horarios y pedidos a domicilio.",
      "tools_count": 4
    },
    {
      "slug": "peluqueria",
      "name": "Peluquería",
      "emoji": "💈",
      "description": "Asistente para salones de belleza: agendamiento de citas, precios y servicios.",
      "tools_count": 4
    },
    {
      "slug": "clinica",
      "name": "Clínica / Consultorio",
      "emoji": "🏥",
      "description": "Asistente médico-odontológico: agendamiento de consultas, horarios y preguntas frecuentes.",
      "tools_count": 4
    }
  ]
}
```

Hay **10 plantillas** disponibles: `restaurante`, `peluqueria`, `clinica`, `tienda`, `inmobiliaria`, `gimnasio`, `contador`, `taller`, `hotel`, `ecommerce`.

### 13.2 Aplicar una Plantilla (1-Click Setup)

> **La forma más rápida de poner un cliente en producción.**  
> Un solo endpoint crea: Cliente + Agente IA + Tools preconfiguradas.

**Opción A — Dashboard** (`http://localhost:5050/templates`):

1. Ve a la sección **Plantillas**
2. Click en una plantilla (ej: "Restaurante")
3. Llená: nombre del negocio + número de WhatsApp
4. Click **"Aplicar Plantilla"**
5. ¡Listo! El cliente y su agente IA quedan creados automáticamente

**Opción B — API**:

```bash
curl -X POST http://localhost:8000/api/v1/templates/restaurante/apply \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pizzería La Nona",
    "whatsapp_number": "5491134567890"
  }'
```

Respuesta:

```json
{
  "template_slug": "restaurante",
  "client": { "id": "...", "name": "Pizzería La Nona", ... },
  "agent": { "id": "...", "name": "Mi Restaurante", "tools": [...] },
  "message": "Cliente y agente creados exitosamente con plantilla 'restaurante'"
}
```

### 13.3 Crear Agente con Plantilla (Manual)

**Opción A — Dashboard** (`http://localhost:5050/agents`):

1. Ve a **Agentes** → "Nuevo Agente"
2. Seleccioná un **Cliente** existente
3. En el campo **Plantilla**, elegí un rubro del dropdown (ej: "Restaurante")
4. El formulario se auto-completa con:
   - **Nombre**: predefinido según la plantilla
   - **Personalidad**: el system prompt del rubro
   - **Tools**: las herramientas que necesita ese tipo de negocio
5. Ajustá lo que quieras y click **"Guardar"**

**Opción B — API**:

```bash
curl -X POST http://localhost:8000/api/v1/clients/{client_id}/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bot Restaurante",
    "personality": "Eres el asistente virtual de un restaurante...",
    "tools": [
      {"name": "reservar_mesa", "description": "Reserva una mesa", "endpoint": "http://n8n:5678/webhook/reservar_mesa"},
      {"name": "ver_menu", "description": "Muestra el menú del día", "endpoint": "http://n8n:5678/webhook/ver_menu"}
    ]
  }'
```

> **Tip**: Si pasás `template` en el body, el backend lo usa para sugerir valores por defecto. No es obligatorio — podés crear un agente sin plantilla también.

### 13.4 Personalizar una Plantilla

Cada plantilla es un **punto de partida**. Podés editar cualquier campo después de aplicarla:

- Cambiar el **nombre** del agente
- Ajustar la **personalidad** (hacerla más formal, más friendly, etc.)
- Agregar o quitar **tools**
- Vincular la **base de conocimiento** del negocio (PDFs, páginas web)

Las plantillas están definidas en `backend-core/app/infrastructure/templates/data.py`. Para agregar un nuevo rubro, agregá una entrada al array `TEMPLATES` con su `slug`, `personality` y `tools`.

### 13.5 Tabla de Plantillas Disponibles

| Slug | Rubro | Emoji | Tools incluidas |
|------|-------|:-----:|-----------------|
| `restaurante` | Restaurante | 🍕 | reservar_mesa, ver_menu, consultar_horarios, pedir_domicilio |
| `peluqueria` | Peluquería | 💈 | agendar_cita, consultar_precios, ver_servicios, recordatorio |
| `clinica` | Clínica / Consultorio | 🏥 | agendar_consulta, ver_horarios, recordar_cita, preguntas_frecuentes |
| `tienda` | Tienda / Retail | 🏪 | buscar_producto, ver_precio, disponibilidad, seguimiento_pedido |
| `inmobiliaria` | Inmobiliaria | 🏠 | agendar_visita, ver_propiedades, calcular_hipoteca, contacto_asesor |
| `gimnasio` | Gimnasio / Fitness | 💪 | agendar_clase, ver_planes, consultar_horarios, pausar_membresia |
| `contador` | Contador / Estudio Contable | ⚖️ | agendar_consulta, recordar_vencimientos, preguntas_fiscales, enviar_documentos |
| `taller` | Taller Mecánico | 🔧 | agendar_revision, consultar_servicios, pedir_repuestos, seguimiento |
| `hotel` | Hotel / Hospedaje | 🏨 | reservar_habitacion, ver_disponibilidad, check_in, servicios_hotel |
| `ecommerce` | E-commerce / Tienda Online | 📦 | buscar_producto, ver_precio, seguimiento_pedido, cambios_devoluciones |

---

## 14. Landing Pages (Próximamente)

> Páginas de aterrizaje con formularios de captura que alimentan automáticamente el pipeline de leads.

### 🎯 Qué va a hacer

1. **Crear landing page**: desde el dashboard, elegís un template y publicás
2. **Formulario de captura**: nombre, WhatsApp, necesidad
3. **Auto-lead**: cada submit → lead nuevo en el pipeline (Módulo 4)
4. **Secuencia automática**: lead recibe mensaje de WhatsApp + email de bienvenida
5. **Analíticas**: cuántos visitantes → leads → clientes

### 📐 Cómo se integra

```
Visitante → Landing Page → Completa formulario
  → POST /api/v1/landing/{slug}/submit
  → Crea lead en Supabase
  → Dispara webhook en n8n
  → n8n envía WhatsApp + email de bienvenida
  → Agente IA toma el seguimiento
```

> Este módulo forma parte de la **Fase 5 — Marketing Digital**. Ver [META.md](./META.md) para el roadmap completo.

---

## 15. Novedades y Changelog

### Sesión 1 — Setup Inicial

- Estructura del proyecto: backend (FastAPI), frontend (React + Vite + Tailwind), Docker
- Schema de Supabase: `clients`, `agents`, `conversations`, `messages`, `knowledge_base`
- CRUD completo de clientes y agentes (API + frontend)
- Autenticación JWT básica
- Configuración de Redis + Celery para tareas asíncronas

### Sesión 2 — WhatsApp + Motor IA

- Integración con Meta WhatsApp Cloud API
- Webhook `/webhook/whatsapp` para recibir mensajes
- Arquitectura hexagonal: `LLMPort` para conectar cualquier LLM
- LangGraph para orquestación del agente (system prompt + herramientas)
- `build_system_prompt()` con personalidad, tools y contexto de negocio

### Sesión 3 — n8n + Dashboard

- n8n como motor de automatización (`:5678`)
- Sistema de Tools en agentes (nombre, descripción, endpoint)
- `agent_tools_to_openai_format()` transforma tools → OpenAI function calling
- `execute_tool()` ejecuta llamadas a n8n/webhooks externos
- Dashboard con cards de métricas (clientes, agentes)

### Sesión 4 — Conversaciones

- Página de listado de conversaciones con filtro por cliente
- Página de detalle de conversación con historial de mensajes
- Auto-scroll a último mensaje
- Sidebar con navegación completa

### Sesión 5 — Leads (Prospección)

- Tabla `leads` en Supabase con pipeline de estados
- CRUD completo de leads: crear, listar, actualizar, enviar mensaje proactivo
- Página de leads con estadísticas del pipeline
- Detalle del lead con cambio de estado + envío de mensajes
- Endpoint `/api/v1/leads/stats` con métricas por estado

### Sesión 6 — Feedback

- Tabla `feedback` en Supabase con rating y comentarios
- CRUD de feedback: crear, listar por cliente, estadísticas
- Sección de feedback en la página de detalle del lead
- Endpoint `/api/v1/feedback/stats` con promedio y distribución

### Sesión 7 — Webhook Meta + Plantillas v2

- Webhook de Meta WhatsApp Cloud API con routing multi-tenant por `phone_number_id`
- Webhook verification (`GET /webhook/whatsapp` con challenge)
- Rate limiter con Redis para evitar spam/abuso
- Endpoint `POST /api/v1/templates/{slug}/apply` — 1-click setup (Cliente + Agente + Tools)
- Página `/templates` en el dashboard con catálogo visual de 10 plantillas
- Página `/templates/:slug/apply` con formulario de aplicación
- Endpoints n8n preconfigurados para cada tool de cada plantilla

### Sesión 8 — Documentación Completa + Growth Funnel

- Documento `META.md` actualizado con módulos 7-10 (Marketing Digital)
- Sección Growth Funnel: Atracción → Nutrición → Conversión
- Roadmap con Fase 5 — Marketing Digital
- Documento `PRODUCTIVIDAD.md` con guía práctica de uso diario
- `GUIA.md` con tabla completa de URLs y secciones nuevas (Landing Pages, Plantillas)
- Definiciones clave expandidas con nuevos términos (Lead, Funnel, Drip Campaign)

### Sesión 9 — Próximamente (Fase 5)

- 🔲 Módulo 7: Landing Pages + Formularios de captura
- 🔲 Módulo 8: Email Marketing (secuencias automáticas drip)
- 🔲 Módulo 9: Contenido IA para redes sociales
- 🔲 Módulo 10: Meta Ads API (crear campañas desde el dashboard)

---

## 🎉 ¡Listo! Tu Agencia IA está funcionando.

### ¿Qué sigue?

- **Aplicar plantillas 1-click**: usá `/templates` para crear clientes con agente IA en segundos
- **Agregar más clientes**: cada negocio es un registro en `clients`
- **Crear agentes especializados**: peluquería, restaurante, contador… cada uno con su personalidad
- **Cargar base de conocimiento**: subí PDFs, páginas web o texto con información del negocio (ej: menú, lista de precios, horarios)
- **Diseñar flujos en n8n**: agendar citas, enviar recordatorios, generar facturas
- **Explorar leads**: usá el pipeline de prospección para gestionar clientes potenciales
- **Recolectar feedback**: configurá el envío automático de encuestas post-servicio
- **Leer PRODUCTIVIDAD.md**: guía práctica para sacarle el máximo provecho a la plataforma
- **Próximamente**: Landing Pages, Email Marketing, Contenido IA, Meta Ads
- **Poner en producción**: contratá un VPS ($20/mes), apuntá un dominio, activá HTTPS

### Resumen de URLs

| URL | Servicio | Módulo |
|-----|----------|--------|
| `http://localhost:5050` | Dashboard principal | Panel de control |
| `http://localhost:5050/login` | Login | Autenticación |
| `http://localhost:5050/clients` | Gestión de clientes | M5 |
| `http://localhost:5050/clients/:id` | Detalle de cliente | M5 |
| `http://localhost:5050/agents` | Gestión de agentes IA | M3 |
| `http://localhost:5050/agents/:id` | Detalle de agente | M3 |
| `http://localhost:5050/conversations` | Historial de conversaciones | M1 |
| `http://localhost:5050/conversations/:id` | Detalle de conversación | M1 |
| `http://localhost:5050/leads` | Pipeline de leads | M4 |
| `http://localhost:5050/leads/:id` | Detalle de lead + feedback | M4 |
| `http://localhost:5050/templates` | Catálogo de plantillas | M6 |
| `http://localhost:5050/templates/:slug/apply` | Aplicar plantilla (1-click) | M6 |
| `http://localhost:8000/docs` | Swagger API | Backend |
| `http://localhost:8000/health` | Health Check | Monitoreo |
| `http://localhost:8000/api/v1/clients` | API Clientes | Backend |
| `http://localhost:8000/api/v1/agents` | API Agentes | Backend |
| `http://localhost:8000/api/v1/conversations` | API Conversaciones | Backend |
| `http://localhost:8000/api/v1/leads` | API Leads | Backend |
| `http://localhost:8000/api/v1/feedback` | API Feedback | Backend |
| `http://localhost:8000/api/v1/templates` | API Plantillas | Backend |
| `http://localhost:8000/webhook/whatsapp` | Webhook WhatsApp (Meta Cloud API) | M1 |
| `http://localhost:5678` | n8n Automation | M2 |

### Solución de problemas comunes

| Problema | Solución |
|---|---|
| `docker-compose up` falla | ¿Docker Desktop está corriendo? ¿Puertos 5050/8000/5678 están libres? |
| Backend no arranca | `docker-compose logs backend` — probablemente falta `.env` o credenciales incorrectas |
| "Invalid API key" en Supabase | Verificá que sea la **service_role** key, no la anon key |
| El bot no recibe mensajes | Verificá el webhook en Meta (verify token) y que el `phone_number_id` del tenant esté configurado |
| Agente IA no responde | Revisá `LLM_API_KEY` y `LLM_BASE_URL` en `.env`. Probá `curl http://localhost:8000/health` primero |
| Celery no procesa tareas | `docker-compose logs celery-worker` — probablemente Redis no está healthy |
| Leads no se cargan | Verificá la tabla `leads` en Supabase y que el `client_id` sea correcto |
| Feedback no aparece | La tabla `feedback` debe existir. Usá `POST /api/v1/feedback` para crear uno de prueba |
| Plantilla no se aplica | Verificá que el slug exista en `GET /api/v1/templates`. Usá `POST /api/v1/templates/{slug}/apply` |
| Webhook no recibe mensajes | Probá `GET /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=...&hub.challenge=test` |

---

> **Hecho con ❤️ para emprendedores que quieren automatizar su negocio con IA.**
