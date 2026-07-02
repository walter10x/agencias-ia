# Guía de la Aplicación — Agencia IA

> Guía de USO de la plataforma. Qué hace cada página, cómo se usa y cómo acceder.
> Para el roadmap técnico y plan de desarrollo ver `GUIA-CONEXION-CLIENTES.md`.

---

## 1. ¿Qué es?

Plataforma SaaS multi-tenant donde **dueños de negocio** obtienen un **agente de IA** que atiende a SUS clientes por WhatsApp automáticamente.

### 3 Roles

| Rol | Quién | Qué puede hacer |
|-----|-------|----------------|
| **Superadmin** | Walter | Ver todo, crear/configurar agentes, aprobar registros |
| **Client Admin** | Dueño del negocio | Ver su dashboard, leads, conversaciones, perfil |
| **Client Final** | Cliente del negocio | Manda WhatsApp al número del negocio, el agente IA responde |

---

## 2. Cómo acceder

### Desarrollo (local)

```bash
# Frontend (Vite dev server)
cd frontend-dashboard && npm run dev
→ http://localhost:3000

# Backend (FastAPI)
cd backend-core
python -m uvicorn app.main:app --reload
→ http://localhost:8000
→ Documentación API: http://localhost:8000/docs

# n8n
→ http://localhost:5678
```

### Docker (producción local)

```bash
docker compose up -d
→ Frontend:  http://localhost:5050
→ Backend:   http://localhost:8000
→ n8n:       http://localhost:5678
```

---

## 3. Páginas del Frontend

### Públicas (sin login)

| Ruta | Página | Qué hace |
|------|--------|----------|
| `/` | HomePage | Nuestra página de marketing. Muestra qué ofrecemos, cómo funciona, planes. CTA para registrarse |
| `/login` | LoginPage | Inicio de sesión para superadmin y clientes |
| `/register` | RegisterPage | Registro de nuevos clientes (dueños de negocio) |
| `/landing/:slug` | LandingPage | Página pública de captación de leads del cliente (ej: `/landing/peluqueria-juan`) |

### Admin (requieren login — superadmin)

Todas bajo `/app/*`:

| Ruta | Página | Qué hace |
|------|--------|----------|
| `/app` | Dashboard | Métricas globales: clientes activos, agentes, mensajes |
| `/app/clients` | ClientsPage | Lista de todos los clientes registrados. Ver estado, aprobar/rechazar |
| `/app/clients/:id` | ClientDetailPage | Detalle del cliente: editar, ver estado WhatsApp, crear agente |
| `/app/agents` | AgentsPage | Lista de todos los agentes IA configurados |
| `/app/agents/:id` | AgentDetailPage | Editar personalidad, tools, activar/desactivar agente |
| `/app/conversations` | ConversationsPage | Historial de chats WhatsApp de todos los clientes |
| `/app/conversations/:id` | ConversationDetailPage | Mensajes individuales de una conversación |
| `/app/leads` | LeadsPage | Todos los leads capturados (formularios, WhatsApp) |
| `/app/leads/:id` | LeadDetailPage | Detalle del lead, enviar mensaje proactivo |
| `/app/templates` | TemplatesPage | Plantillas de agente preconfiguradas por rubro |
| `/app/templates/:slug/apply` | TemplateApplyPage | Aplicar plantilla a un cliente |

### Cliente (futuro — requerirán login como client_admin)

Todas bajo `/app/*` pero filtradas por su propio `client_id`:

| Ruta | Página | Qué ve el cliente |
|------|--------|-------------------|
| `/app` | Dashboard | Solo sus métricas: leads, conversaciones, mensajes |
| `/app/conversations` | ConversationsPage | Solo los chats de SU WhatsApp |
| `/app/leads` | LeadsPage | Solo los leads de SU negocio |
| `/app/perfil` | ProfilePage | Editar datos de su negocio |
| `/app/whatsapp` | ConnectWhatsAppPage | Estado de su WhatsApp conectado |
| `/app/agente` | AgentViewPage | Ver (no editar) su agente IA |
| `/app/facturacion` | BillingPage | Plan y pagos (futuro) |

---

## 4. Flujo de trabajo (Walter)

```
1. Llegada del cliente
   └─ Cliente entra a tudominio.com → ve HomePage → click "Comenzar"
   └─ Se registra en /register → status = "pending"

2. Tú apruebas
   └─ Entras a /login (tu email superadmin)
   └─ Vas a /app/clients → ves badge "Pendientes: N"
   └─ Abres el cliente → botón "Aprobar"
   └─ Status cambia a "approved"

3. Configuras el agente
   └─ En ClientDetailPage → "Crear Agente"
   └─ Seleccionas plantilla o configuras manual
   └─ Activas el agente → status = "active"

4. El cliente usa su agente
   └─ Sus clientes finales mandan WhatsApp al número
   └─ El agente IA responde automáticamente
   └─ El cliente ve leads y conversaciones en su dashboard
```

---

## 5. Módulos del backend

| Módulo | Endpoints | Descripción |
|--------|-----------|-------------|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | Registro, login, perfil |
| **Clientes** | `GET/POST/PATCH/DELETE /clients` | CRUD de clientes. Approve/reject/disconnect-whatsapp (solo superadmin) |
| **Agentes** | `GET/POST/PATCH/DELETE /agents` | CRUD de agentes IA con personalidad y tools |
| **Leads** | `GET/POST /leads`, `POST /leads/{id}/send-message` | Pipeline de prospección |
| **Conversaciones** | `GET /conversations`, `GET /conversations/{id}` | Historial de chats WhatsApp |
| **Email** | `POST /emails/send`, `GET /emails`, `GET /emails/stats` | Email marketing con 30 templates |
| **Feedback** | `POST /feedback`, `GET /feedback` | Feedback y NPS |
| **Landing Pages** | `GET /landing/{slug}/config`, `POST /landing/{slug}/submit` | Landing pública con formulario de captura |
| **Templates** | `GET /templates` | Plantillas de agente por rubro |
| **WhatsApp** | `POST /webhook/whatsapp` | Webhook que recibe y procesa mensajes |

---

## 6. Tecnologías

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19, Vite 8, Tailwind v4, TanStack Query, react-router-dom v7 |
| Backend | FastAPI, LangGraph, Pydantic v2 |
| Base de datos | Supabase (PostgreSQL) |
| Auth | JWT (HS256) + bcrypt |
| WhatsApp | Meta Cloud API (Graph v22.0) |
| Tareas async | Celery + Redis |
| Automatización | n8n |
| Contenedores | Docker Compose |

---

> Versión: Julio 2026 · Documento de USO de la aplicación
