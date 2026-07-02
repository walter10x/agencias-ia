# Guía de Conexión con Clientes — Plataforma Agencias-IA

> **Documento ÚNICO y DECISIVO** del proyecto.
> Cualquier otro `.md` de planificación que no sea este está obsoleto.
> **Reglas**: arquitectura hexagonal · TDD · archivos <500 líneas · funciones pequeñas · cero `Any`.

---

## 1. Visión General

**Qué es**: Una plataforma SaaS multi-tenant tipo "Meta Business para Agentes IA".
**Para quién**:
- **Walter (tú)**: Superadmin. Ves todos los clientes, configuras agentes, apruebas registros.
- **Clientes (dueños de negocio)**: Llegan a la página pública, ven los servicios, se registran, conectan WhatsApp, y su agente IA atiende a SUS clientes finales.
- **Clientes finales**: Gente que manda WhatsApp al negocio y el agente IA les responde.

**Stack**:
```
Frontend → React 19 + Vite + Tailwind v4 + TanStack Query
Backend  → FastAPI + LangGraph + Celery + Redis (arquitectura hexagonal)
DB       → Supabase (PostgreSQL)
WhatsApp → Meta Cloud API (WABA central de Walter)
Auth     → JWT (bcrypt + python-jose)
Deploy   → Docker Compose
```

**3 roles**: `superadmin` (Walter) · `client_admin` (dueño negocio) · `client_user` (empleado, previsto)

---

## 2. Estado Actual vs Meta Final

| # | Módulo | Estado | Prioridad |
|---|--------|:------:|:---------:|
| 1 | **Chatbots Multicanal** (WhatsApp ✅, Telegram/Webchat ❌) | ⚠️ | 🔴 |
| 2 | **Backend Auth Multi-Tenant** (registro, login, JWT, middleware, tenant filter) | ✅ Completo | 🟢 |
| 3 | **CRUD Clientes + Agentes IA + Leads + Conversaciones** | ✅ Completo | 🟢 |
| 4 | **Landing Pages Públicas** (para captar leads de los clientes) | ✅ Completo | 🟢 |
| 5 | **Email Marketing** (30 templates HTML, API lista, 0 tests, sin scheduler) | ⚠️ Parcial | 🟡 |
| 6 | **Frontend Auth** (página pública plataforma, registro, login real, rutas protegidas) | 🔴 **AHORA** | 🔴 |
| 7 | **Panel Admin** (mejoras: badge pendientes, aprobar/rechazar desde UI) | ⏳ Existe, mejorar | 🟡 |
| 8 | **Dashboard Cliente** (páginas existen, falta filtrar por rol JWT) | ⏳ Existe, mejorar | 🟡 |
| 9 | **Onboarding Wizard** (perfil → rubro/templates → WhatsApp → activar) | ❌ No empezado | 🟢 |
| 10 | **Facturación** (MercadoPago/Stripe, planes, límites) | ❌ No empezado | 🔵 |
| 11 | **Deploy Producción** (VPS + dominio + HTTPS) | ❌ No empezado | ⚫ |

---

## 3. Fases de Implementación

### ✅ FASE 1 — Backend Auth Multi-Tenant (COMPLETADA)

**Qué se hizo**:
- `PasswordHasher` bcrypt + tests (5 tests)
- `JwtHandler` HS256 + tests (5 tests)
- `RegisterClientUseCase` (hash + status=pending) + tests (12 tests)
- `LoginClientUseCase` (valida pass + status gate) + tests
- `GetCurrentClientUseCase` + tests
- `auth_router.py` (`POST /auth/register`, `POST /auth/login`, `GET /auth/me`)
- `dependencies.py`: `get_current_client`, `require_superadmin`
- `client_router.py`: approve / reject / disconnect-whatsapp (solo superadmin)
- Migración `002_auth_multi_tenant.sql` (password_hash, role, status, plan)
- Filtro tenant en 5 routers (lead, conversation, agent, email, feedback)
- Validación cross-tenant en agentes (403 si no coincide client_id)
- 38 tests de auth + 11 tests de tenant isolation
- `spec-auth.md` v1.3 completa
- `ForbiddenError` → HTTP 403 handler

**Total**: 631 tests passing, 19 pre-existing failing (17 whatsapp_webhook + 2 repo)

---

### 🔴 FASE 2 — Página Pública de la Plataforma + Frontend Auth (AHORA)

**Objetivo**: Crear el punto de entrada donde los dueños de negocio descubren la plataforma, se registran e inician sesión.

**Qué construir**:

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `pages/HomePage.tsx` | Nuevo | Marketing page: hero, servicios, cómo funciona, CTA "Comenzar" |
| `pages/RegisterPage.tsx` | Nuevo | Formulario: email + contraseña + nombre negocio + WhatsApp |
| `context/AuthContext.tsx` | Nuevo | Estado global de auth (token, rol, client_id, login/logout) |
| `hooks/useAuth.ts` | Nuevo | Hook para acceder al contexto |
| `components/ProtectedRoute.tsx` | Nuevo | Guard → redirige a /login si no hay token |
| `components/AdminRoute.tsx` | Nuevo | Guard → redirige si no es superadmin |
| `components/ClientRoute.tsx` | Nuevo | Guard → redirige si no es client_admin |
| `components/ClientLayout.tsx` | Nuevo | Layout del panel cliente (sidebar distinto) |
| `pages/client/ClientDashboardPage.tsx` | Nuevo | Métricas del cliente |
| `pages/client/ClientLeadsPage.tsx` | Nuevo | Leads del cliente |
| `pages/client/ClientConversationsPage.tsx` | Nuevo | Conversaciones del cliente |
| `pages/client/ProfilePage.tsx` | Nuevo | Editar datos del negocio |
| `pages/client/ConnectWhatsAppPage.tsx` | Nuevo | Estado WhatsApp (no QR — Meta) |
| `pages/client/AgentViewPage.tsx` | Nuevo | Agente solo lectura |
| `api/auth.ts` | Nuevo | Funciones register, login, me |

**Archivos a editar**:

| Archivo | Cambio |
|---------|--------|
| `App.tsx` | Rutas `/` → HomePage, añadir `/register`, mover admin a `/app/*` |
| `main.tsx` | Envolver en `AuthProvider` |
| `api/config.ts` | Interceptor JWT en headers |
| `components/Sidebar.tsx` | Menú condicional por rol (superadmin vs client_admin) |
| `pages/LoginPage.tsx` | Conectar al backend real (`POST /auth/login`) |

**API endpoints que consume**:
- `POST /api/v1/auth/register` → `{ email, password, business_name, whatsapp_number }` → `{ client_id, email, status, message }`
- `POST /api/v1/auth/login` → `{ email, password }` → `{ access_token, token_type, client_id, role, status }`
- `GET /api/v1/auth/me` → Bearer → `{ client_id, email, name, role, status, whatsapp_number, whatsapp_connected, plan, is_active }`

**Reglas**:
- TDD: tests primero (vitest/react-testing-library)
- Sin archivos > 500 líneas
- Sin funciones > 40 líneas
- Tipado fuerte, cero `Any`
- Misma paleta visual: black bg, amber accents, zinc grays

---

### 🟠 FASE 3 — Panel Admin (mejoras)

- ClientsPage: badge "Pendientes: N", botones aprobar/rechazar
- ClientDetailPage: estado WhatsApp + botón desconectar (solo superadmin)
- DashboardPage: métricas globales (clientes, aprobados, pendientes, WhatsApp conectados, mensajes hoy)

### 🟡 FASE 4 — Dashboard Cliente

- ClientLayout sidebar distinto (solo leads, conversaciones, perfil, agente read-only, billing)
- Filtrar APIs por client_id del JWT
- ProfilePage con onboarding wizard

### 🟢 FASE 5 — Onboarding Wizard

- Paso 1: perfil (rubro, descripción, horarios, dirección, logo)
- Paso 2: confirmar WhatsApp conectado
- Paso 3: elegir tono/idioma del agente
- Paso 4: Walter activa

### 🔵 FASE 6 — Facturación

- MercadoPago o Stripe
- Planes (Free/Pro/Enterprise)
- Middleware de límites
- BillingPage integrada

### ⚫ FASE 7 — Deploy Producción

- VPS + dominio + HTTPS (Traefik/Caddy + Let's Encrypt)
- Separar contenedores con redes internas

---

## 4. Decisiónes Cerradas

| # | Decisión | Valor |
|---|----------|-------|
| 1 | Auth | JWT + bcrypt (`passlib[bcrypt]`, `python-jose[cryptography]`) |
| 2 | Roles | `superadmin` (Walter), `client_admin` (dueño), `client_user` (empleado, previsto) |
| 3 | Registro público | 4 campos: email + contraseña + nombre negocio + WhatsApp |
| 4 | Aprobación | Manual por Walter. `status`: `pending` → `approved` → `active` |
| 5 | WhatsApp | Meta Cloud API (Graph v22.0). WABA central de Walter |
| 6 | Prompt del agente | Lo configura Walter. El cliente ve (no edita) |
| 7 | Supabase RLS | Deseable pero no bloquea avance |
| 8 | Facturación | MercadoPago o Stripe (decidir en Fase 6) |

---

## 5. Flujo del Usuario

```
CLIENTE (dueño negocio)         WALTER (tú)                    SISTEMA
─────────────────────────────   ──────────────                 ──────────

1. Entra a tudominio.com
2. Ve HomePage: "Potencia tu
   negocio con IA"
3. Click "Comenzar"
4. Se registra (email + pass
   + nombre negocio + WhatsApp)
                                                               JWT generado
                                                               status = pending

                                5. ClientsPage badge "Pendientes: 1"
                                6. Revisa datos
                                7. Aprueba → status = approved

8. Recibe notificación
9. Login → ve su dashboard    10. Configura agente IA
                                   desde panel admin
                                11. Activa agente → status = active

12. Dashboard cliente: leads,
    conversaciones, métricas
```

---

## 6. Arquitectura

```
Página pública nuestra     →  /register  →  Auth API → Supabase
(dueños descubren + se        POST /auth/register     clients table
 registran)

Login                       →  /login     →  Auth API → JWT
                               POST /auth/login

Panel admin (Walter)        →  /app/*      →  API scoped → filtrado
Panel cliente (dueño)       →  /app/*      →  API scoped por client_id

Landing pública del cliente →  /landing/:slug → API pública → leads
(para captar clientes finales)

WhatsApp                    →  Webhook    →  LangGraph → agente → respuesta
```

---

## 7. Checklist de Calidad

```bash
# Backend
cd backend-core
ruff check . && mypy . && pytest -q

# Frontend
cd frontend-dashboard
npm run lint && npm run typecheck && npm run build
```

Todo verde antes de marcar una fase como completa.

---

> **Documento ÚNICO**. No hay otro plan. Si ves un `.md` de planificación que no es este, está obsoleto.
> Próxima fase: **FASE 2 — Página pública de la plataforma + Frontend Auth**.
