# Agencia IA — Frontend Dashboard

> Panel de control SaaS multi-tenant para gestión de agentes IA sobre WhatsApp.

`frontend-dashboard` es la aplicación web del proyecto **Agencia IA**. Es un SPA construido con React 19, Vite 8 y Tailwind v4 que consume la API REST del backend FastAPI (`backend-core`) y le permite a un superadmin gestionar clientes, agentes IA, leads y conversaciones, y a cada cliente final administrar su propio agente desde una vista limitada a su `client_id`.

---

## Tabla de Contenidos

1. [Qué es Agencia IA](#1-qué-es-agencia-ia)
2. [Tech Stack](#2-tech-stack)
3. [Roles del Sistema](#3-roles-del-sistema)
4. [Quick Start Local](#4-quick-start-local)
5. [Estructura del Proyecto](#5-estructura-del-proyecto)
6. [Rutas del Frontend](#6-rutas-del-frontend)
7. [Módulos del Backend (Routers)](#7-módulos-del-backend-routers)
8. [API Reference — Módulos del Frontend](#8-api-reference--módulos-del-frontend)
9. [Componentes Principales](#9-componentes-principales)
10. [Autenticación y Autorización](#10-autenticación-y-autorización)
11. [Testing](#11-testing)
12. [Deployment](#12-deployment)
13. [Documentación Adicional](#13-documentación-adicional)
14. [Contribuciones y Licencia](#14-contribuciones-y-licencia)

---

## 1. Qué es Agencia IA

**Agencia IA** es una plataforma SaaS multi-tenant estilo "Meta Business para Agentes IA". Su objetivo es que cualquier dueño de negocio local pueda desplegar un agente conversacional que atienda a sus clientes automáticamente por WhatsApp, sin programar y con onboarding guiado.

### Problema que resuelve

Los negocios locales (peluquerías, restaurantes, clínicas, tiendas, contadores) reciben consultas repetitivas por WhatsApp que un humano responde a mano muchas veces al día. Eso:

- consume tiempo del dueño o de sus empleados,
- genera demoras fuera de horario,
- pierde leads que no se contestan a tiempo.

Agencia IA estandariza ese flujo: el dueño se registra, se le aprueba, se le conecta WhatsApp, se le asigna un agente IA configurado por rubro (personalidad + tools + base de conocimiento) y desde ese momento el agente responde por él. El dueño ve los leads y conversaciones en su dashboard.

### Para quién

| Actor | Necesidad que cubre |
|-------|---------------------|
| **Dueño de negocio** (client_admin) | Atender clientes 24/7, no perder leads, ver métricas de su WhatsApp. |
| **Superadmin** (operador de la plataforma) | Aprobar registros, configurar agentes, monitorear todas las conversaciones. |
| **Cliente final** del negocio | Hablarle a un WhatsApp y recibir respuesta inmediata. |

---

## 2. Tech Stack

### Frontend (este repositorio)

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **React** | 19.2 | UI declarativa con hooks y Suspense |
| **Vite** | 8.0 | Build tool, dev server con HMR, code-splitting |
| **TypeScript** | 6.0 | Tipado estático estricto |
| **Tailwind CSS** | 4.3 | Estilos utility-first (tema oscuro) |
| **@tanstack/react-query** | 5.x | Cache de servidor, mutaciones, invalidación |
| **react-router-dom** | 7.17 | Ruteo SPA con loaders y guards |
| **lucide-react** | 1.17 | Iconos |
| **Vitest** | 4.x | Test runner |
| **@testing-library/react** | 16.x | Render y queries de tests |
| **jsdom** | 29.x | Entorno DOM para tests |

### Backend (`../backend-core`)

| Tecnología | Uso |
|------------|-----|
| **FastAPI** | API REST + documentación OpenAPI |
| **LangGraph** | Orquestación del agente IA (state graph) |
| **Celery + Redis** | Tareas asíncronas (procesamiento de mensajes, PDFs) |
| **Arquitectura hexagonal** | `domain/` · `application/` · `infrastructure/` (puertos y adaptadores) |
| **Pydantic v2** | Validación de DTOs y schemas |
| **python-jose + passlib[bcrypt]** | JWT + hash de contraseñas |

### Datos y Servicios Externos

| Servicio | Uso |
|----------|-----|
| **Supabase (PostgreSQL)** | Persistencia multi-tenant, RLS deseado |
| **Meta Cloud API (WhatsApp Graph v22.0)** | Recepción y envío de mensajes por WABA central |
| **n8n** | Automatización de flujos secundarios |
| **JWT (HS256)** | Tokens stateless firmados con `python-jose` |

---

## 3. Roles del Sistema

El backend emite un JWT que incluye un campo `role` y un `client_id`. El frontend decide qué rutas y qué secciones de la UI se renderizan según ese rol.

| Rol | Quién | Permisos |
|-----|-------|----------|
| `superadmin` | Walter (operador de la plataforma) | Ve todos los clientes, aprueba/rechaza registros, crea y configura agentes IA, aplica plantillas, ve todas las conversaciones y todos los leads. |
| `client_admin` | Dueño del negocio (registrado) | Ve sólo los datos de su propio `client_id`: leads, conversaciones, perfil, agente en modo lectura, facturación (futuro). |
| `client_user` | Empleado del negocio (previsto) | Acceso limitado a conversaciones y leads de su tenant, sin configuración. |

> Nota: el rol `client_user` está contemplado en el modelo pero las páginas dedicadas se construyen en una fase posterior.

### Estados de un cliente

`pending` → `approved` → `active`

- `pending`: se acaba de registrar, no puede operar, espera aprobación manual del superadmin.
- `approved`: aprobado, todavía sin agente configurado.
- `active`: tiene un agente activo respondiendo por WhatsApp.

---

## 4. Quick Start Local

### Prerrequisitos

- Node.js 24+ y npm
- Python 3.12+ y `uv` (o `pip`)
- Backend levantado en `http://localhost:8000`

### Levantar el frontend (desarrollo)

```bash
cd frontend-dashboard
npm install
npm run dev
# → http://localhost:3000
```

El dev server de Vite (puerto 3000) proxya automáticamente `/api/*` y `/webhook/*` al backend en `http://localhost:8000`. Configurado en `vite.config.ts`.

### Levantar el backend (FastAPI + Celery + Redis)

```bash
cd ../backend-core
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Levantar Redis (requerido para Celery)
docker run -d -p 6379:6379 --name redis-agencia redis:7-alpine

# API
uvicorn app.main:app --reload
# → http://localhost:8000
# → Docs OpenAPI: http://localhost:8000/docs

# Worker de Celery (otra terminal)
celery -A app.infrastructure.config.celery_app worker --loglevel=info
```

### Levantar todo con Docker Compose

```bash
# Desde la raíz del repo (/)
docker compose up -d
# → Frontend:  http://localhost:5050
# → Backend:   http://localhost:8000
# → n8n:       http://localhost:5678
# → Redis:     localhost:6379
```

### Crear el superadmin inicial

El registro público en `/register` crea cuentas con rol `client_admin` y estado `pending`. Para crear el superadmin (Walter) se debe insertar directamente en la tabla `clients` con `role='superadmin'`. Ver `backend-core/specs/spec-auth.md` y la migración `002_auth_multi_tenant.sql`.

### Scripts npm disponibles

```bash
npm run dev          # dev server con HMR (puerto 3000)
npm run build        # tsc -b && vite build → dist/
npm run preview      # sirve dist/ localmente
npm run lint         # ESLint
npm test             # Vitest (una pasada)
npm run test:watch   # Vitest (modo watch)
```

---

## 5. Estructura del Proyecto

### `frontend-dashboard/`

```
frontend-dashboard/
├── docs/                                  # Documentación técnica detallada
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── COMPONENTS.md
│   ├── TESTING.md
│   └── DEPLOYMENT.md
├── specs/                                 # Specs de comportamiento (SDD)
│   └── spec-frontend-pages.md
├── public/                                # Assets estáticos
│   ├── favicon.svg
│   └── icons.svg
├── src/
│   ├── api/                               # 10 módulos de cliente HTTP
│   │   ├── agent.ts                       # CRUD agentes IA
│   │   ├── auth.ts                        # login / register / me
│   │   ├── client.ts                      # CRUD clientes
│   │   ├── config.ts                      # apiFetch, ApiError, JWT interceptor
│   │   ├── conversation.ts                # conversaciones WhatsApp
│   │   ├── email.ts                       # email marketing
│   │   ├── feedback.ts                    # feedback y NPS
│   │   ├── landing.ts                     # landing pages públicas
│   │   ├── lead.ts                        # leads del pipeline
│   │   └── template.ts                    # plantillas de agente por rubro
│   │   └── __tests__/                     # tests de api
│   ├── assets/                            # Imágenes y SVGs
│   ├── components/                        # 8 componentes reutilizables
│   │   ├── AdminRoute.tsx                 # guard: superadmin
│   │   ├── AgentForm.tsx                  # modal crear/editar agente
│   │   ├── ClientForm.tsx                 # modal crear/editar cliente
│   │   ├── ClientRoute.tsx                # guard: client_admin
│   │   ├── Pagination.tsx                 # paginación genérica
│   │   ├── ProtectedRoute.tsx             # guard: autenticado
│   │   ├── Sidebar.tsx                    # navegación colapsable
│   │   └── Toast.tsx                      # sistema de notificaciones
│   │   └── __tests__/                     # tests de componentes
│   ├── context/
│   │   ├── AuthContext.tsx                # estado de auth (token, user)
│   │   └── __tests__/
│   ├── hooks/
│   │   └── useAuth.ts                     # acceso al AuthContext
│   ├── pages/                             # 15 páginas (lazy-loaded)
│   │   ├── HomePage.tsx                   # marketing pública
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── LandingPage.tsx                # /landing/:slug (pública por cliente)
│   │   ├── DashboardPage.tsx              # /app
│   │   ├── ClientsPage.tsx                # /app/clients (superadmin)
│   │   ├── ClientDetailPage.tsx           # /app/clients/:id
│   │   ├── AgentsPage.tsx                 # /app/agents
│   │   ├── AgentDetailPage.tsx            # /app/agents/:id
│   │   ├── ConversationsPage.tsx          # /app/conversations
│   │   ├── ConversationDetailPage.tsx     # /app/conversations/:id
│   │   ├── LeadsPage.tsx                  # /app/leads
│   │   ├── LeadDetailPage.tsx             # /app/leads/:id
│   │   ├── TemplatesPage.tsx              # /app/templates
│   │   └── TemplateApplyPage.tsx          # /app/templates/:slug/apply
│   │   └── __tests__/
│   ├── test/
│   │   └── setup.ts                       # jest-dom para vitest
│   ├── App.tsx                            # rutas, providers, layout
│   ├── main.tsx                           # entrypoint (createRoot)
│   └── index.css                          # tailwind + estilos base
├── Dockerfile                             # build multi-stage con nginx
├── eslint.config.js
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
└── vite.config.ts                         # alias @/, proxy /api, /webhook
```

### `backend-core/` (referencia)

```
backend-core/
├── app/
│   ├── domain/                            # entidades + errores de dominio
│   │   ├── agent/  client/  conversation/  email/  feedback/
│   │   ├── landing/  lead/  channels/  shared/
│   ├── application/                       # casos de uso (orquestación)
│   │   ├── agent/  auth/  client/  conversation/  email/
│   │   ├── feedback/  landing/  lead/  templates/  ports/
│   │   └── dtos.py
│   ├── infrastructure/                    # adaptadores
│   │   ├── http/                          # routers FastAPI + schemas
│   │   ├── persistence/                   # Supabase repos
│   │   ├── whatsapp/                      # webhook + Meta Cloud API
│   │   ├── ai/                            # LangGraph
│   │   ├── security/                      # JWT, password hasher
│   │   ├── templates/                     # plantillas de agente
│   │   └── config/                        # settings, celery_app
│   └── main.py
├── migrations/                            # SQL versionado
├── specs/                                 # specs SDD (spec-*.md)
├── tests/                                 # pytest (631 tests)
├── scripts/
├── Dockerfile
└── requirements.txt
```

---

## 6. Rutas del Frontend

Todas las páginas se cargan con `React.lazy` + `Suspense` (ver `App.tsx`). El árbol de rutas aplica guards anidados: `ProtectedRoute` valida sesión, `AdminRoute` valida rol.

### Públicas (sin autenticación)

| Ruta | Página | Componente | Notas |
|------|--------|------------|-------|
| `/` | HomePage | `pages/HomePage.tsx` | Marketing: hero, servicios, planes, CTA "Comenzar". |
| `/login` | LoginPage | `pages/LoginPage.tsx` | Form email + password. POST `/auth/login`. |
| `/register` | RegisterPage | `pages/RegisterPage.tsx` | Form público de alta: email, password, business_name, whatsapp_number. Estado resultante: `pending`. |
| `/landing/:slug` | LandingPage | `pages/LandingPage.tsx` | Captación de leads del cliente. Render dinámico por slug. |

### Protegidas (requieren login)

Todas bajo `/app/*`, envueltas en `<ProtectedRoute><AppLayout/></ProtectedRoute>`. La `Sidebar` muestra secciones distintas según el rol.

| Ruta | Página | Acceso | Función |
|------|--------|--------|---------|
| `/app` | DashboardPage | superadmin y client_admin | Métricas globales o del tenant. |
| `/app/clients` | ClientsPage | superadmin | Lista de todos los clientes. Badge "Pendientes: N", aprobar/rechazar. |
| `/app/clients/:id` | ClientDetailPage | superadmin | Detalle del cliente. Crear/editar agente, ver estado WhatsApp, disconnect. |
| `/app/agents` | AgentsPage | superadmin | Lista de todos los agentes IA configurados. |
| `/app/agents/:id` | AgentDetailPage | superadmin | Editar personalidad, tools, knowledge_base_refs, activar/desactivar. |
| `/app/conversations` | ConversationsPage | ambos | Historial de chats WhatsApp (filtrado por client_id para `client_admin`). |
| `/app/conversations/:id` | ConversationDetailPage | ambos | Mensajes individuales de una conversación. |
| `/app/leads` | LeadsPage | ambos | Pipeline de leads (filtrado por tenant). |
| `/app/leads/:id` | LeadDetailPage | ambos | Detalle y envío de mensaje proactivo. |
| `/app/templates` | TemplatesPage | superadmin | Plantillas de agente preconfiguradas por rubro. |
| `/app/templates/:slug/apply` | TemplateApplyPage | superadmin | Aplicar plantilla a un cliente (crea cliente + agente). |
| `/app/profile` | (reservado) | client_admin | Perfil del propio negocio. |

### Guards en el árbol de rutas

```tsx
<Route path="/" element={<HomePage />} />
<Route path="/login" element={<LoginPage />} />
<Route path="/register" element={<RegisterPage />} />
<Route path="/landing/:slug" element={<LandingPage />} />

<Route element={<ProtectedRoute />}>
  <Route element={<AppLayout />}>
    <Route path="/app" element={<DashboardPage />} />
    <Route path="/app/clients" element={<ClientsPage />} />
    {/* ... resto de rutas protegidas ... */}
  </Route>
</Route>
```

`AdminRoute` y `ClientRoute` están implementados como componentes y se pueden anidar dentro de `ProtectedRoute` cuando se necesite una restricción dura por rol (por ejemplo, redirigir a un `client_admin` que intenta entrar a `/app/clients`).

---

## 7. Módulos del Backend (Routers)

Cada router está registrado en `backend-core/app/main.py` con su prefijo `/api/v1`.

| Router | Prefijo | Tags | Endpoints principales |
|--------|---------|------|----------------------|
| `auth_router` | `/api/v1/auth` | Auth | `POST /register`, `POST /login`, `GET /me` |
| `client_router` | `/api/v1/clients` | Clients | `GET /`, `POST /`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, `POST /{id}/agents`, `GET /{id}/agents`, `POST /{id}/approve`, `POST /{id}/reject`, `POST /{id}/disconnect-whatsapp` |
| `agent_router` | `/api/v1/agents` | Agents | `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, `DELETE /{id}/permanent` |
| `conversation_router` | `/api/v1/conversations` | Conversations | `GET /`, `GET /{id}/messages`, `GET /stats` |
| `lead_router` | `/api/v1/leads` | Leads | `POST /`, `GET /`, `GET /stats`, `PATCH /{id}`, `POST /{id}/send-message` |
| `feedback_router` | `/api/v1/feedback` | Feedback | `POST /`, `GET /`, `GET /stats` |
| `template_router` | `/api/v1/templates` | Templates | `GET /`, `POST /{slug}/apply` |
| `landing_public_router` | `/api/v1/landing` | Landing Pages | `GET /{slug}/config`, `POST /{slug}/submit` |
| `landing_admin_router` | `/api/v1/clients` | Landing Admin | `GET /{client_id}/landing`, `PATCH /{client_id}/landing` |
| `email_router` | `/api/v1/emails` | Email Marketing | `POST /send`, `GET /`, `GET /stats`, `GET /templates` |
| `whatsapp_router` | `/webhook` | WhatsApp | `GET /whatsapp` (verificación), `POST /whatsapp` (mensajes entrantes) |

> Detalle de cada esquema Pydantic: ver `docs/API.md` y los `spec-*.md` en `backend-core/specs/`.

---

## 8. API Reference — Módulos del Frontend

Todos los módulos viven en `src/api/` y exportan funciones tipadas que envuelven `apiFetch` (definido en `src/api/config.ts`). `apiFetch` aplica el prefijo `/api/v1`, inyecta `Authorization: Bearer <token>` desde `localStorage.auth_token` y normaliza errores a `ApiError`.

### `apiFetch<T>(url, options?)` — `api/config.ts`

```ts
class ApiError extends Error {
  detail: string;
  error_type: string;
}

function apiFetch<T>(url: string, options?: RequestInit): Promise<T>;
```

- Lee `localStorage.getItem("auth_token")` y agrega `Authorization: Bearer <token>` si existe.
- En respuesta 204 devuelve `undefined` tipado.
- En respuesta no-OK, intenta parsear `{ detail, error_type }` y lanza `ApiError`.

### Tabla de funciones

| Módulo | Función | Firma | Endpoint backend | Verbo |
|--------|---------|-------|------------------|-------|
| `auth` | `login` | `(email, password) => Promise<LoginResponse>` | `/api/v1/auth/login` | POST |
| `auth` | `register` | `(data: RegisterData) => Promise<RegisterResponse>` | `/api/v1/auth/register` | POST |
| `auth` | `fetchMe` | `() => Promise<CurrentClientResponse>` | `/api/v1/auth/me` | GET |
| `client` | `fetchClients` | `(limit, offset) => Promise<ClientListData>` | `/api/v1/clients?limit=&offset=` | GET |
| `client` | `fetchClient` | `(id) => Promise<ClientData>` | `/api/v1/clients/{id}` | GET |
| `client` | `searchClientByWhatsapp` | `(whatsapp) => Promise<ClientListData>` | `/api/v1/clients?whatsapp=` | GET |
| `client` | `createClient` | `(data) => Promise<ClientData>` | `/api/v1/clients` | POST |
| `client` | `updateClient` | `(id, data) => Promise<ClientData>` | `/api/v1/clients/{id}` | PATCH |
| `client` | `deactivateClient` | `(id) => Promise<ClientData>` | `/api/v1/clients/{id}` | DELETE |
| `agent` | `fetchAgentsByClient` | `(clientId) => Promise<AgentListData>` | `/api/v1/clients/{clientId}/agents` | GET |
| `agent` | `fetchAgent` | `(id) => Promise<AgentData>` | `/api/v1/agents/{id}` | GET |
| `agent` | `createAgent` | `(clientId, data) => Promise<AgentData>` | `/api/v1/clients/{clientId}/agents` | POST |
| `agent` | `updateAgent` | `(id, data) => Promise<AgentData>` | `/api/v1/agents/{id}` | PATCH |
| `agent` | `deactivateAgent` | `(id) => Promise<AgentData>` | `/api/v1/agents/{id}` | DELETE |
| `agent` | `deleteAgent` | `(id) => Promise<void>` | `/api/v1/agents/{id}/permanent` | DELETE |
| `conversation` | `fetchConversations` | `(clientId, limit?, offset?) => Promise<ConversationListData>` | `/api/v1/conversations?client_id=&limit=&offset=` | GET |
| `conversation` | `fetchConversationMessages` | `(id) => Promise<ConversationMessagesData>` | `/api/v1/conversations/{id}/messages` | GET |
| `conversation` | `fetchConversationStats` | `() => Promise<ConversationStatsData>` | `/api/v1/conversations/stats` | GET |
| `email` | `sendEmail` | `(data) => Promise<EmailSendResult>` | `/api/v1/emails/send` | POST |
| `email` | `fetchEmails` | `(clientId, leadId?, limit?, offset?) => Promise<EmailListData>` | `/api/v1/emails?client_id=&...` | GET |
| `email` | `fetchEmailStats` | `(clientId) => Promise<EmailStatsData>` | `/api/v1/emails/stats?client_id=` | GET |
| `email` | `fetchEmailTemplates` | `() => Promise<{ rubros: string[] }>` | `/api/v1/emails/templates` | GET |
| `feedback` | `fetchFeedbackList` | `(clientId, limit?, offset?) => Promise<FeedbackListData>` | `/api/v1/feedback?client_id=&...` | GET |
| `feedback` | `createFeedback` | `(data) => Promise<FeedbackData>` | `/api/v1/feedback` | POST |
| `feedback` | `fetchFeedbackStats` | `(clientId) => Promise<FeedbackStatsData>` | `/api/v1/feedback/stats?client_id=` | GET |
| `landing` | `fetchLandingPublicConfig` | `(slug) => Promise<LandingPublicConfig>` | `/api/v1/landing/{slug}/config` | GET |
| `landing` | `submitLandingForm` | `(slug, data) => Promise<LandingSubmitOutput>` | `/api/v1/landing/{slug}/submit` | POST |
| `landing` | `fetchLandingConfig` | `(clientId) => Promise<LandingConfig>` | `/api/v1/clients/{clientId}/landing` | GET |
| `landing` | `updateLandingConfig` | `(clientId, data) => Promise<LandingConfig>` | `/api/v1/clients/{clientId}/landing` | PATCH |
| `lead` | `fetchLeads` | `(clientId, status?, limit?, offset?) => Promise<LeadListData>` | `/api/v1/leads?client_id=&...` | GET |
| `lead` | `updateLead` | `(id, data) => Promise<LeadData>` | `/api/v1/leads/{id}` | PATCH |
| `lead` | `fetchLeadStats` | `(clientId) => Promise<LeadStatsData>` | `/api/v1/leads/stats?client_id=` | GET |
| `lead` | `sendProactiveMessage` | `(leadId, text) => Promise<void>` | `/api/v1/leads/{leadId}/send-message` | POST |
| `lead` | `createLead` | `(data) => Promise<LeadData>` | `/api/v1/leads` | POST |
| `template` | `fetchTemplates` | `() => Promise<TemplateListData>` | `/api/v1/templates` | GET |
| `template` | `applyTemplate` | `(slug, data) => Promise<ApplyTemplateOutput>` | `/api/v1/templates/{slug}/apply` | POST |

> Todos los tipos de respuesta (`LoginResponse`, `ClientData`, `AgentData`, etc.) están exportados desde cada módulo.

---

## 9. Componentes Principales

Documentación extendida en `docs/COMPONENTS.md`.

### `Toast` — sistema de notificaciones

Context API + portal fijo en la esquina inferior derecha. Auto-dismiss a los 4 segundos.

```tsx
<ToastProvider>
  <App />
</ToastProvider>

const { toast } = useToast();
toast("success", "Cliente creado correctamente");
toast("error",   "Error al guardar");
```

| Elemento | Tipo | Descripción |
|----------|------|-------------|
| `toast(type, message)` | `("success" \| "error", string) => void` | Muestra notificación. |
| `ToastProvider` | `({ children }) => JSX` | Envuelve la app (ya está en `App.tsx`). |

### `ProtectedRoute` — guard de autenticación

Lee `useAuth()`. Muestra spinner durante `isLoading`, redirige a `/login` si no hay sesión, renderiza `<Outlet/>` si está autenticado. Se usa como layout padre en el árbol de rutas.

### `AdminRoute` — guard de superadmin

Además de autenticar, valida `user?.role === "superadmin"`. Si no, redirige a `/`. Anidar dentro de `ProtectedRoute`.

### `ClientRoute` — guard de client_admin

Valida `user?.role === "client_admin"`. Si no, redirige a `/app`. Anidar dentro de `ProtectedRoute`.

### `Sidebar` — navegación principal

- Colapsable, estado persistido en `localStorage.sidebar_collapsed`.
- Menú condicional por rol (ver `Sidebar.tsx:88-122`).
- Cierre de sesión vía `useAuth().logout()`.
- Avatar con iniciales del usuario, email truncado.
- Soporte mobile: el `AppLayout` muestra el sidebar dentro de un overlay cuando el ancho es `<lg`.

```tsx
<Sidebar className="hidden md:flex" onCloseMobile={() => setOpen(false)} />
```

### `ClientForm` — modal crear/editar cliente

Modal controlado por `isOpen` / `onClose`. Validación client-side.

| Campo | Regla |
|-------|-------|
| `name` | Requerido, máx 200 chars |
| `business_type` | Requerido, selección de `peluqueria / bar / restaurante / contador / fonatero / tienda / gimnasio / clinica / otro` |
| `whatsapp_number` | Solo dígitos, mínimo 10 |

Maneja `createClient` y `updateClient` con `useMutation`, muestra toast, invalida `["clients"]` y `["client", id]`.

### `AgentForm` — constructor de agentes

Modal con `name`, `personality`, lista dinámica de **tools** y **knowledge_base_refs** (CSV). Mismas convenciones de mutación que `ClientForm`.

| Campo | Regla |
|-------|-------|
| `name` | Requerido |
| `personality` | Mínimo 10 caracteres |
| tools | Cada uno requiere `name` y `description`; `endpoint` opcional. |

### `Pagination` — navegación de páginas

Pura presentación, sin lógica de fetching.

```tsx
<Pagination
  currentPage={page}
  totalPages={totalPages}
  onPageChange={setPage}
/>
```

No renderiza nada si `totalPages <= 1`.

---

## 10. Autenticación y Autorización

### Stack

- **Algoritmo**: JWT HS256 firmado con `python-jose` en el backend.
- **Hash de contraseñas**: bcrypt vía `passlib[bcrypt]`.
- **Storage del token en el frontend**: `localStorage` bajo la clave `auth_token`.
- **Interceptor**: `apiFetch` lo lee en cada request y agrega `Authorization: Bearer <token>`.

### Flujo

```
1. Usuario envía POST /api/v1/auth/login (email, password)
2. Backend valida con bcrypt y emite { access_token, client_id, role, status, token_type }
3. AuthProvider.login() guarda el token en localStorage y llama GET /api/v1/auth/me
4. AuthProvider setea `user` (CurrentClientResponse)
5. ProtectedRoute deja pasar, AppLayout + Sidebar renderizan el menú según role
6. apiFetch adjunta el token en cada request subsecuente
7. Logout: localStorage.removeItem('auth_token') + setUser(null) + navigate('/login')
```

### Persistencia de sesión

`AuthProvider` ejecuta un `useEffect` al montar la app:

- Si hay `auth_token` en localStorage, hace `GET /api/v1/auth/me`.
- Si la promesa falla (token expirado o inválido), limpia el token y deja `user = null`.
- En cualquier caso, marca `isLoading = false` al final.

### Guards de ruta

```tsx
// Pública
<Route path="/login" element={<LoginPage />} />

// Cualquier usuario autenticado
<Route element={<ProtectedRoute />}>
  <Route path="/app" element={<DashboardPage />} />
</Route>

// Solo superadmin (futuro: anidar dentro de ProtectedRoute)
<Route element={<AdminRoute />}>
  <Route path="/app/clients" element={<ClientsPage />} />
</Route>

// Solo client_admin
<Route element={<ClientRoute />}>
  <Route path="/app/profile" element={<ProfilePage />} />
</Route>
```

### Aislamiento por tenant

El backend aplica filtro por `client_id` (proveniente del JWT) en los routers: `lead`, `conversation`, `agent`, `email`, `feedback`. Un `client_admin` que manipule el `client_id` en la URL recibe `403 Forbidden` (handler `ForbiddenError → HTTP 403`).

---

## 11. Testing

### Stack de testing

| Herramienta | Versión | Uso |
|-------------|---------|-----|
| Vitest | 4.x | Runner (config en `vite.config.ts`) |
| @testing-library/react | 16.x | Render + queries |
| @testing-library/jest-dom | 6.x | Matchers (`toBeInTheDocument`, etc.) |
| @testing-library/user-event | 14.x | Simulación realista de eventos |
| jsdom | 29.x | DOM virtual |

### Configuración

`vite.config.ts` declara `test.globals = true`, `environment = "jsdom"` y `setupFiles = ["./src/test/setup.ts"]`. El setup importa `@testing-library/jest-dom/vitest`.

### Comandos

```bash
npm test             # una pasada (CI)
npm run test:watch   # modo watch (desarrollo)
```

### Cobertura actual

**40 tests en 8 archivos** (vitest + @testing-library):

| Archivo | Tests | Cubre |
|---------|-------|-------|
| `src/api/__tests__/auth.test.ts` | 4 | `login`, `register`, `fetchMe` — happy path + 401/409 |
| `src/api/__tests__/config.test.ts` | 4 | `apiFetch` — sin token, con token, 204, error HTTP |
| `src/components/__tests__/ProtectedRoute.test.tsx` | 2 | autenticado → outlet; sin auth → redirect |
| `src/components/__tests__/AdminRoute.test.tsx` | 2 | superadmin → outlet; client → redirect |
| `src/components/__tests__/ClientRoute.test.tsx` | 2 | client → outlet; superadmin → redirect |
| `src/context/__tests__/AuthContext.test.tsx` | 1+ | contexto de auth |
| `src/pages/__tests__/HomePage.test.tsx` | 2 | render básico |
| `src/pages/__tests__/LoginPage.test.tsx` | 2 | render + submit |
| `src/pages/__tests__/RegisterPage.test.tsx` | 2 | render + submit |

### Convenciones

1. **Mockear API calls** con `vi.mock("@/api/<modulo>")` o con `globalThis.fetch = vi.fn()`.
2. **Buscar elementos** por rol accesible (`getByRole`) o por test-id.
3. **Simular eventos** con `userEvent` (no `fireEvent`).
4. **Casos**: happy path + error path + casos borde.
5. **Archivos**: `<Nombre>.test.tsx` o `__tests__/`.

### Pendiente de testing (próximas iteraciones)

- `DashboardPage`, `ClientsPage`, `ClientDetailPage`, `ClientForm`
- `AgentsPage`, `AgentForm`
- `ConversationsPage`, `LeadsPage`
- `Sidebar`, `Toast`, `Pagination`

### Tests del backend (referencia)

`backend-core/tests/` corre con `pytest`. Estado actual: **631 tests passing** (auth, tenant isolation, use cases). Ver `backend-core/specs/spec-auth.md` y `GUIA-CONEXION-CLIENTES.md`.

---

## 12. Deployment

### Build de producción

```bash
npm run build
# → genera frontend-dashboard/dist/ (chunks optimizados con prefetching)
```

### Servir con Nginx (SPA)

```nginx
server {
    listen 80;
    server_name dashboard.tudominio.com;
    root /var/www/frontend-dashboard/dist;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy al backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /webhook/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    # Cache de assets con hash
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Docker

`Dockerfile` multi-stage (Node 24 alpine para build + nginx alpine para servir):

```dockerfile
FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Config nginx inline (ver Dockerfile del repo)
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

El frontend se integra con el resto de la stack en el `docker-compose.yml` de la raíz del repo, que levanta en paralelo:

| Servicio | Puerto host | Notas |
|----------|------------|-------|
| `frontend` | 5050 | nginx sirviendo el dist |
| `backend` | 8000 | FastAPI + uvicorn |
| `redis` | 6379 | broker de Celery + cache |
| `celery-worker` | — | tareas async |
| `n8n` | 5678 | automatización |

### Variables de entorno

No hay variables de entorno runtime en el frontend — el target del proxy está hardcodeado en `vite.config.ts` apuntando a `http://localhost:8000`. Para apuntar a otro backend en producción, se modifica el bloque `server.proxy` o se sirve detrás de un reverse proxy que traduzca `/api` al host del backend.

### Preview local

```bash
npm run preview
# Sirve dist/ localmente para verificar el build antes de pushear
```

---

## 13. Documentación Adicional

### Documentos en este repositorio

| Documento | Ruta | Contenido |
|-----------|------|-----------|
| Arquitectura | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Estructura detallada, árbol de rutas, flujo de datos, stack por capa. |
| API Reference | [`docs/API.md`](docs/API.md) | Módulos de la API del frontend, modelos de datos, manejo de errores, políticas de React Query. |
| Componentes | [`docs/COMPONENTS.md`](docs/COMPONENTS.md) | Props y ejemplos de uso de los 8 componentes. |
| Testing | [`docs/TESTING.md`](docs/TESTING.md) | Configuración, comandos, cobertura actual y estrategia. |
| Deployment | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Build, nginx, Docker, preview. |
| Spec de páginas | [`specs/spec-frontend-pages.md`](specs/spec-frontend-pages.md) | Spec SDD de las páginas del frontend. |

### Documentos en la raíz del repo

| Documento | Ruta | Contenido |
|-----------|------|-----------|
| Guía de uso de la plataforma | [`../GUIA-APLICACION.md`](../GUIA-APLICACION.md) | Qué hace cada página, cómo acceder, flujo de aprobación, módulos del backend. |
| Master plan técnico | [`../GUIA-CONEXION-CLIENTES.md`](../GUIA-CONEXION-CLIENTES.md) | Decisiones cerradas, fases de implementación, checklist de calidad. |
| Specs SDD del backend | `../backend-core/specs/spec-*.md` | 13 specs (auth, conversations, email, landing, llm-langgraph, prospection, repositories, routers, templates, whatsapp, etc.). |

### Convenciones de calidad

Antes de cerrar una fase se debe correr:

```bash
# Frontend
cd frontend-dashboard
npm run lint && npx tsc -b && npm run build && npm test

# Backend
cd backend-core
ruff check . && mypy . && pytest -q
```

Todo verde antes de mergear.

---

## 14. Contribuciones y Licencia

### Reglas del repo

- **TDD**: tests antes de código.
- **Archivos < 500 líneas**, **funciones < 40 líneas**.
- **Tipado fuerte**, cero `any`.
- **Cero secretos** commiteados. `.env` está en `.gitignore` en todos los niveles.
- **Sin emojis en código** salvo que sean parte del UI funcional.
- Mensajes de commit en presente, en español, describiendo el "qué" y el "por qué".
- No agregar trailers `Co-Authored-By` salvo configuración explícita en `.claude/settings.json`.

### Cómo contribuir

1. Crear rama desde `main` con prefijo descriptivo (`feat/`, `fix/`, `chore/`, `docs/`).
2. PR con descripción del cambio, screenshots si afecta UI, referencia al spec de `backend-core/specs/` si aplica.
3. Verificar que el checklist de calidad pasa.
4. Asignar revisión (superadmin o desarrollador con ownership del módulo).

### Licencia

Privada / Propietaria. Todos los derechos reservados. Este proyecto no es open source y no se acepta contribución externa sin acuerdo previo con el operador de la plataforma.

---

> **Documento vivo**. Si encontrás secciones desactualizadas, abrí un PR contra `frontend-dashboard/README.md`.
