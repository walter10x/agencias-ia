# Guía de Conexión con Clientes — Plataforma Agencias-IA

> **Objetivo**: Convertir este monorepo en una plataforma SaaS multi-tenant donde tus clientes se registran, tú les configuras agentes IA, y ellos gestionan su negocio desde un dashboard propio.

---

## 1. Visión General

**Qué es**: Una plataforma web tipo "Meta Business para Agentes IA".  
**Para quién**:
- **Walter (tú)**: Superadmin. Creas clientes, configuras agentes IA, ves todo.
- **Clientes (dueños de negocio)**: Se registran, conectan su WhatsApp, su agente IA atiende automático a SUS clientes finales.
- **Clientes finales**: Gente que manda WhatsApp al negocio y el agente IA les responde.

**Stack tecnológico**:
```
Frontend → React 19 + Vite + Tailwind v4 + TanStack Query
Backend  → FastAPI + LangGraph + Celery + Redis
DB       → Supabase (PostgreSQL)
WhatsApp → Evolution API (self-hosted)
Auth     → JWT (ya configurado en backend)
Deploy   → Docker Compose (todo en una VPS)
```

---

## 2. Lo Que Ya Está Codeado

| Componente | Archivos clave | Funcionalidad |
|---|---|---|
| **Backend API** | `backend-core/app/main.py` | FastAPI corriendo en `:8000` |
| **CRUD Clientes** | `backend-core/app/application/client/` | Crear, listar, editar, desactivar clientes |
| **CRUD Agentes IA** | `backend-core/app/application/agent/` | Crear, configurar, asignar agentes con prompt |
| **Leads** | `backend-core/app/application/lead/` | Capturar, listar, enviar mensajes a leads |
| **Conversaciones** | `backend-core/app/application/conversation/` | Historial de chats WhatsApp |
| **Landing Pública** | `backend-core/app/application/landing/` | Página pública captura leads (submit_lead) |
| **Templates** | `backend-core/app/application/templates/` | Plantillas de mensajes predefinidas |
| **Email Marketing** | `backend-core/app/application/email/` | Envío de campañas de email |
| **Feedback** | `backend-core/app/application/feedback/` | Sistema de feedback/NPS |
| **WhatsApp Webhook** | `backend-core/app/infrastructure/whatsapp/` | Recibe mensajes, procesa con LangGraph |
| **LangGraph Agent** | `backend-core/app/infrastructure/ai/agent_graph.py` | Motor de IA conversacional |
| **Supabase Repos** | `backend-core/app/infrastructure/persistence/` | Capa de datos (PostgreSQL) |
| **Dashboard Frontend** | `frontend-dashboard/src/pages/` | Panel React con todas las pantallas |
| **Docker Compose** | `docker-compose.yml` | Orquestación: frontend, backend, redis, celery, n8n |

---

## 3. Lo Que Falta Construir (Roadmap)

### 🔴 FASE 1 — Autenticación Multi-Tenant (CRÍTICO - empezar aquí)

**Problema actual**: Cualquiera con acceso a la API ve TODOS los datos. No hay login de clientes, no hay separación por tenant.

**Qué hay que hacer**:

| Tarea | Detalle |
|---|---|
| **Registro de clientes** | Endpoint `POST /auth/register` — un cliente se registra con email + contraseña + datos del negocio |
| **Login de clientes** | Endpoint `POST /auth/login` — devuelve JWT con `client_id` en el payload |
| **Roles** | Tres niveles: `superadmin` (tú), `client_admin` (dueño del negocio), `client_user` (empleados del negocio) |
| **Middleware de tenant** | Cada request autenticado inyecta `client_id` del JWT. Todas las queries filtran por ese `client_id` |
| **Ruta protegida frontend** | React Router guard que redirige a `/login` si no hay token |
| **Pantalla de Login** | Ya existe `LoginPage.tsx` — conectarla al backend real |
| **Pantalla de Registro** | Nueva: formulario de registro con datos del negocio |

**Archivos a tocar**:
```
NUEVO: backend-core/app/infrastructure/http/auth_router.py
NUEVO: backend-core/app/application/auth/register_client.py
NUEVO: backend-core/app/application/auth/login_client.py
EDITAR: backend-core/app/infrastructure/http/dependencies.py (agregar get_current_client)
EDITAR: TODOS los routers (filtrar por client_id del token)
EDITAR: frontend-dashboard/src/pages/LoginPage.tsx
NUEVO: frontend-dashboard/src/pages/RegisterPage.tsx
NUEVO: frontend-dashboard/src/context/AuthContext.tsx
```

---

### 🟠 FASE 2 — Panel de Admin (para ti, Walter)

**Problema actual**: No hay distinción entre lo que ves tú y lo que ve un cliente.

**Qué hay que hacer**:

| Tarea | Detalle |
|---|---|
| **Vista global de clientes** | Tabla con todos los clientes registrados, estado, plan, fecha de registro |
| **Activar/desactivar cliente** | Tú controlas quién tiene acceso |
| **Configurar agente por cliente** | Desde tu panel, seleccionas un cliente y le creas/editas su agente IA |
| **Métricas globales** | Total clientes, total mensajes procesados, agentes activos, ingresos |
| **Sidebar admin** | Menú diferente al del cliente (más opciones) |

**Archivos a tocar**:
```
EDITAR: frontend-dashboard/src/components/Sidebar.tsx (menú condicional por rol)
EDITAR: frontend-dashboard/src/pages/DashboardPage.tsx (métricas según rol)
NUEVO: frontend-dashboard/src/pages/AdminClientsPage.tsx
EDITAR: backend-core/app/infrastructure/http/client_router.py (endpoints admin)
```

---

### 🟡 FASE 3 — Dashboard del Cliente

**Problema actual**: Las páginas del dashboard existen pero no filtran por `client_id`.

**Qué hay que hacer**:

| Tarea | Detalle |
|---|---|
| **Dashboard del cliente** | Al loguearse, el cliente ve SOLO sus métricas: leads, conversaciones, mensajes |
| **Lista de leads** | Solo los leads de SU negocio |
| **Conversaciones** | Solo los chats de SU WhatsApp |
| **Configuración de agente** | El cliente puede ver (no editar) la configuración de su agente IA |
| **Perfil** | El cliente puede editar datos de su negocio (nombre, rubro, horarios) |

**Archivos a tocar**:
```
EDITAR: TODAS las queries en backend-core/app/infrastructure/persistence/
        Agregar WHERE client_id = current_client_id
EDITAR: frontend-dashboard/src/api/*.ts (pasar token JWT en headers)
EDITAR: frontend-dashboard/src/pages/*.tsx (solo muestran datos del cliente autenticado)
```

---

### 🟢 FASE 4 — Onboarding Wizard

**Problema actual**: El cliente se registra y no sabe qué hacer.

**Qué hay que hacer**:

| Tarea | Detalle |
|---|---|
| **Paso 1: Datos del negocio** | Nombre, rubro, descripción, horarios |
| **Paso 2: Conectar WhatsApp** | Instrucciones para conectar su número a Evolution API (o escanear QR) |
| **Paso 3: Configurar agente** | El cliente elige tono, idioma, servicios que ofrece. Tú validas. |
| **Paso 4: Activar** | Tú activas el agente desde tu panel admin |

---

### 🔵 FASE 5 — Facturación y Planes

**Problema actual**: No hay forma de cobrar.

**Qué hay que hacer**:

| Tarea | Detalle |
|---|---|
| **Planes** | Free (100 msgs/mes), Pro (1000 msgs/mes), Enterprise (ilimitado) |
| **Pasarela de pago** | Stripe o MercadoPago |
| **Límites** | Middleware que cuenta mensajes por cliente y bloquea si excede |
| **Facturas** | Generación automática de factura/recibo |

---

## 4. Flujo del Cliente (Paso a Paso)

```
CLIENTE (dueño de negocio)              WALTER (tú)                    SISTEMA
─────────────────────────────           ──────────────                 ──────────
                                       
1. Entra a tudominio.com               
2. Ve landing "Potencia tu             
   negocio con IA"                     
3. Click en "Comenzar"                 
4. Se registra (email + pass           
   + datos negocio)                    
                                                                   5. JWT generado
                                                                      Redirige a /dashboard
                                                                      
6. Ve wizard onboarding:                                            7. Muestra pasos:
   - Completa perfil                                                  1. Perfil
   - Elige rubro/templates                                            2. Templates
   - Conecta WhatsApp                                                 3. WhatsApp
                                                                    
                                       8. Recibes notificación       
                                       9. Revisas datos cliente      
                                       10. Creas agente IA           
                                           con prompt personalizado  
                                       11. Activas agente            
                                                                     12. Agente IA online
                                                                         WhatsApp conectado
                                                                         
13. Cliente ve dashboard:                                           14. Dashboard muestra:
    - Leads capturados                                                  leads, conversaciones
    - Conversaciones                                                    métricas en tiempo real
    - Estadísticas                                                  
```

---

## 5. Arquitectura Multi-Tenant

```
┌──────────────────────────────────────────────────────────────┐
│                    SUPABASE (PostgreSQL)                     │
│                                                              │
│  Tabla: clients          Tabla: agents        Tabla: leads   │
│  ┌─────────────────┐    ┌────────────────┐   ┌────────────┐ │
│  │ id (PK)         │    │ id (PK)        │   │ id (PK)    │ │
│  │ name            │◄───│ client_id (FK) │◄──│ client_id  │ │
│  │ email           │    │ name           │   │ name       │ │
│  │ password_hash   │    │ prompt         │   │ phone      │ │
│  │ plan            │    │ model          │   │ status     │ │
│  │ is_active       │    │ is_active      │   │ ...        │ │
│  │ created_at      │    │ ...            │   └────────────┘ │
│  └─────────────────┘    └────────────────┘                  │
│                                                              │
│  REGLA DE ORO: TODA query incluye WHERE client_id = $1      │
│  $1 = client_id extraído del JWT del usuario autenticado     │
└──────────────────────────────────────────────────────────────┘

JWT Payload:
{
  "sub": "client_uuid",
  "client_id": "uuid-del-cliente",
  "role": "client_admin",
  "exp": 1234567890
}
```

---

## 6. Orden de Implementación (Qué Hacer Primero)

| Orden | Fase | Tiempo estimado | Depende de |
|---|---|---|---|
| **1** | Auth multi-tenant (registro + login + JWT) | 2-3 días | Nada |
| **2** | Middleware tenant (filtrar queries por client_id) | 1-2 días | Fase 1 |
| **3** | Frontend auth (AuthContext + rutas protegidas) | 1 día | Fase 1 |
| **4** | Panel Admin (métricas globales, gestión clientes) | 2 días | Fase 2 |
| **5** | Dashboard cliente (filtrar datos por tenant) | 2 días | Fase 2 y 3 |
| **6** | Onboarding wizard | 2 días | Fase 3 |
| **7** | Facturación (Stripe/MercadoPago) | 3-4 días | Fase 3 |
| **8** | Deploy producción (VPS + dominio + HTTPS) | 1 día | Fase 5 |

**Total estimado**: ~15 días de trabajo para tener la plataforma completa.

---

## 7. Checklist Técnico Detallado

### Backend — Nuevos Archivos

```
backend-core/app/application/auth/
├── __init__.py
├── register_client.py       # Caso de uso: registrar nuevo cliente
├── login_client.py           # Caso de uso: login y generar JWT
└── get_current_client.py     # Caso de uso: obtener perfil del cliente autenticado

backend-core/app/infrastructure/http/
├── auth_router.py            # POST /auth/register, POST /auth/login, GET /auth/me
└── admin_router.py           # Endpoints solo para superadmin
```

### Backend — Archivos a Editar

```
backend-core/app/infrastructure/http/dependencies.py
  → Agregar get_current_client() que extrae client_id del JWT
  → Agregar require_superadmin() para rutas admin

backend-core/app/infrastructure/persistence/lead_repository.py
backend-core/app/infrastructure/persistence/conversation_repository.py
backend-core/app/infrastructure/persistence/agent_repository.py
backend-core/app/infrastructure/persistence/email_repository.py
backend-core/app/infrastructure/persistence/feedback_repository.py
  → TODOS: agregar filtro WHERE client_id = $1

backend-core/app/infrastructure/config/settings.py
  → Agregar JWT_SECRET, JWT_EXPIRE_MINUTES (ya existen en .env.example)
  → Agregar SUPERADMIN_EMAILS (lista de emails con rol superadmin)

backend-core/migrations/
  → 002_add_auth_fields.sql: agregar password_hash, role a tabla clients
```

### Frontend — Nuevos Archivos

```
frontend-dashboard/src/
├── context/
│   └── AuthContext.tsx        # Proveedor de autenticación (token, rol, client_id)
├── hooks/
│   └── useAuth.ts            # Hook para acceder al contexto de auth
├── pages/
│   ├── RegisterPage.tsx       # Formulario de registro
│   └── AdminClientsPage.tsx   # Panel admin: lista de clientes
└── components/
    ├── ProtectedRoute.tsx     # Guard que redirige a /login si no hay token
    └── AdminRoute.tsx         # Guard que redirige si no es superadmin
```

### Frontend — Archivos a Editar

```
frontend-dashboard/src/
├── App.tsx                    # Agregar rutas: /login, /register, /admin/*
├── main.tsx                   # Envolver app en AuthProvider
├── api/config.ts              # Agregar interceptor JWT en headers
├── components/Sidebar.tsx     # Menú condicional según rol
└── pages/LoginPage.tsx        # Conectar con endpoint real
```

---

## 8. Notas Importantes

- **El `.env` NUNCA se commitea**. Usa `.env.example` como template. El `.gitignore` ya está configurado.
- **Branch principal**: `main` (no `master`).
- **Docker Compose** levanta todo junto. En producción, separa frontend (nginx) y backend (uvicorn) con redes internas.
- **Supabase Row Level Security (RLS)**: Opcionalmente puedes usar RLS de Supabase para reforzar multi-tenancy a nivel base de datos, además del filtro en código.
- **Dominio**: Compra un dominio tipo `agenciasia.com`. Configura DNS apuntando a tu VPS.
- **HTTPS**: Usa Traefik o Caddy como reverse proxy con Let's Encrypt automático.

---

## 9. Glosario

| Término | Significado |
|---|---|
| **Multi-tenant** | Múltiples clientes comparten la misma app pero solo ven sus datos |
| **JWT** | Token que identifica al usuario sin sesiones en servidor |
| **LangGraph** | Framework de LangChain para agentes IA conversacionales |
| **Evolution API** | Servidor WhatsApp auto-hosteado (alternativa a Meta Cloud API) |
| **Supabase** | PostgreSQL como servicio con API REST automática |
| **Celery** | Sistema de tareas en segundo plano (ej: procesar mensajes, enviar emails) |
| **n8n** | Automatizador visual de flujos (opcional, para flujos secundarios) |

---

> **Próximo paso**: Empezar con Fase 1 — Autenticación Multi-Tenant.  
> Cuando estés listo, dime: *"Walter, arrancamos con el registro y login"* y lo codeamos.
