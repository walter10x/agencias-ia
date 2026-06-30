# Spec: Frontend Pages — Agencia IA Dashboard

**SDD Phase:** Spec
**Date:** 2026-06-08
**Status:** Pending Approval
**Scope:** Frontend pages, API integration layer, navigation, UI components

---

## 1. Objective

Construir 4 páginas nuevas + integrar API real en Dashboard + capa `api/` con React Query. Todo sobre tema oscuro actual (black bg, zinc-900 cards, amber-500 accent). Sin librerías UI externas.

---

## 2. Architecture Overview

```
Browser (React 19 + Vite)
  │
  ├─ App.tsx (react-router-dom BrowserRouter)
  │   ├─ /login     → LoginPage (pública)
  │   ├─ /          → DashboardPage (AdminLayout)
  │   ├─ /clients   → ClientsPage (AdminLayout)
  │   ├─ /clients/:id → ClientDetailPage (AdminLayout)
  │   ├─ /agents    → AgentsPage (AdminLayout)
  │   └─ /agents/:id  → AgentDetailPage (AdminLayout)
  │
  ├─ Sidebar (colapsable, links existentes OK)
  │
  ├─ api/
  │   ├── config.ts    → BASE_URL, fetch wrapper, error handling
  │   ├── client.ts    → client CRUD functions
  │   └── agent.ts     → agent CRUD functions
  │
  └─ components/
      ├── ClientForm.tsx   → modal crear/editar cliente
      ├── AgentForm.tsx    → modal crear/editar agente
      └── Pagination.tsx   → controles página
```

**Data flow:**
```
Page → useQuery/useMutation → api/function → fetch(BASE_URL + path) → Backend REST
                                                                         │
                                                          http://localhost:8000/api/v1/*
                                                          Vite proxy: /api → :8000
```

---

## 3. API Integration Layer

### 3.1 `src/api/config.ts` — Base Configuration

```typescript
const BASE_URL = "/api/v1";

interface ApiError {
  detail: string;
  error_type: string;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err: ApiError = await res.json().catch(() => ({ detail: res.statusText, error_type: "unknown" }));
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
```

**States:** `fetch` normal → resuelve `T`. Error → lanza `ApiError {detail, error_type}`. 204 → `undefined`.

### 3.2 `src/api/client.ts` — Client API Functions

| Function | Method | Path | Body | Response |
|---|---|---|---|---|
| `listClients(limit, offset)` | GET | `/clients?limit=&offset=` | — | `ClientListResponse` |
| `getClient(id)` | GET | `/clients/{id}` | — | `ClientResponse` |
| `searchClientByWhatsapp(wa)` | GET | `/clients?whatsapp=` | — | `ClientResponse` |
| `createClient(data)` | POST | `/clients` | `ClientCreateRequest` | `ClientResponse` |
| `updateClient(id, data)` | PATCH | `/clients/{id}` | `ClientUpdateRequest` | `ClientResponse` |
| `deactivateClient(id)` | DELETE | `/clients/{id}` | — | `ClientResponse` |

**TypeScript types (inline, no Zod — KISS):**

```typescript
interface ClientData {
  id: string;
  name: string;
  business_type: string;
  whatsapp_number: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ClientListData {
  items: ClientData[];
  count: number;
}

interface ClientCreateInput {
  name: string;
  business_type: string;
  whatsapp_number: string;
}

interface ClientUpdateInput {
  name?: string;
  whatsapp_number?: string;
}
```

### 3.3 `src/api/agent.ts` — Agent API Functions

| Function | Method | Path | Body | Response |
|---|---|---|---|---|
| `listAgentsByClient(clientId)` | GET | `/clients/{clientId}/agents` | — | `AgentListResponse` |
| `getAgent(id)` | GET | `/agents/{id}` | — | `AgentResponse` |
| `createAgent(clientId, data)` | POST | `/clients/{clientId}/agents` | `AgentCreateRequest` | `AgentResponse` |
| `updateAgent(id, data)` | PATCH | `/agents/{id}` | `AgentUpdateRequest` | `AgentResponse` |
| `deactivateAgent(id)` | DELETE | `/agents/{id}` | — | `AgentResponse` |
| `deleteAgentPermanent(id)` | DELETE | `/agents/{id}/permanent` | — | `void (204)` |

**TypeScript types:**

```typescript
interface AgentToolData {
  name: string;
  description: string;
  endpoint: string;
}

interface AgentData {
  id: string;
  client_id: string;
  name: string;
  personality: string;
  tools: AgentToolData[];
  knowledge_base_refs: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface AgentListData {
  items: AgentData[];
  count: number;
}

interface AgentCreateInput {
  name: string;
  personality: string;       // min 10 chars
  tools: AgentToolData[];
  knowledge_base_refs: string[];
}

interface AgentUpdateInput {
  name?: string;
  personality?: string;      // min 10 chars if provided
  tools?: AgentToolData[];
  knowledge_base_refs?: string[];
}
```

---

## 4. Pages Specification

### 4.1 DashboardPage (UPDATE existing)

**Ubicación:** `src/pages/DashboardPage.tsx`

**Cambios:**
- Sustituir datos hardcodeados por `useQuery` fetching stats.
- Backend NO tiene endpoint `/stats`. Solución: fetching paralelo con `useQuery`:
  - `listClients(1, 0)` → count de clientes activos
  - `listAgentsByClient` no sirve sin clientId. Solución simple: usar 2-3 queries para obtener conteos.
  - **KISS approach:** fetch `listClients(limit=200)` para contar. Fetch agentes desde el primer cliente o usar un approach simplificado.
  - **Decisión:** El dashboard muestra stats reales vía 2 queries: `listClients(limit=200, offset=0)` + para cada cliente, sus agentes. O mejor: `listClients` da el count. Para agentes, iteramos todos los clientes. Simplificamos: 2 queries paralelas con `useQuery`.
  - **Final:** `useQuery` para `listClients(200,0)` → count = total. `useQuery` para agentes: dado que no hay endpoint global, hacemos: si clientes existe, tomamos los primeros 3 y listamos sus agentes. Sumamos. **KISS:** el Dashboard muestra "X clientes activos" y "Y agentes activos" aproximados con lo disponible.

**Stats cards actualizadas:**
| Card | Label | Fuente |
|---|---|---|
| Clientes activos | Count de `listClients` (solo `is_active:true`) | `listClients` |
| Agentes IA | Suma de counts de `listAgentsByClient` de cada cliente | loop sobre clientes |
| Mensajes hoy | "—" (no hay endpoint aún) | Hardcodeado |
| Tasa respuesta | "—" (no hay endpoint aún) | Hardcodeado |

**Estados:**
- `loading`: skeleton cards (4 rectángulos grises animados)
- `error`: toast o banner "Error al cargar estadísticas" con botón retry
- `empty`: si 0 clientes, mostrar el empty state actual ("Aún no hay agentes configurados")

**Componentes visuales:** mantener estructura actual (4 stat cards + placeholder), solo cambiar fuente datos.

---

### 4.2 ClientsPage (NEW)

**Ubicación:** `src/pages/ClientsPage.tsx`
**Ruta:** `/clients`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  Clientes                        [+ Nuevo Cliente] │
│  ────────────────────────────────────────────── │
│  [🔍 Buscar por WhatsApp...        ] [Buscar]   │
│                                                 │
│  ┌─────────────────────────────────────────────┐│
│  │ Nombre       │ WhatsApp      │ Tipo    │ Activo ││
│  │ Peluquería X │ 573001234567  │ peluq.  │ ✅    ││
│  │ Bar La Esq.  │ 573009876543  │ bar     │ ✅    ││
│  └─────────────────────────────────────────────┘│
│                                                 │
│  ← Anterior   Página 1 de 3   Siguiente →      │
└────────────────────────────────────────────────┘
```

**Estados:**

| Estado | UI |
|---|---|
| `loading` | Skeleton table (5 filas grises) |
| `empty` (0 clientes) | Ilustración + "No hay clientes aún" + botón "Crear primer cliente" |
| `error` | Banner rojo "Error al cargar clientes" + botón "Reintentar" |
| `loaded` | Tabla con filas clickeables → navega a `/clients/:id` |
| `search-loading` | Spinner pequeño junto al input de búsqueda |
| `search-empty` | "No se encontró ningún cliente con ese WhatsApp" |

**Funcionalidades:**

1. **Listado paginado:** `useQuery({ queryKey: ['clients', page], queryFn: () => listClients(10, (page-1)*10) })`. Page size = 10.
2. **Búsqueda por WhatsApp:** input controlado + botón. `useQuery` condicional (`enabled: !!whatsapp`). Si hay resultado, mostrar tarjeta individual. Si no, mensaje "no encontrado".
3. **Navegación:** click en fila → `navigate(/clients/${id})`.
4. **Botón "Nuevo Cliente":** abre modal `ClientForm`.
5. **Paginación:** componente `<Pagination>` abajo. Props: `currentPage`, `totalPages`, `onPageChange`.
6. **Feedback tras crear:** toast verde "Cliente creado" + invalidar query `['clients']`.

**API calls:**
- Carga inicial: `listClients(10, 0)`
- Paginación: `listClients(10, (page-1)*10)`
- Búsqueda: `searchClientByWhatsapp(whatsapp)`
- Crear: `createClient(data)` → onSuccess invalidate + close modal

**Nota sobre `count`:** El backend retorna `count: items.length`. Para paginación real necesitamos saber el total. Solución KISS: fetch con `limit=200` una vez para saber el total aproximado, o confiar en que `count` refleja la página actual. **Decisión:** la paginación usa `count` de la respuesta actual. Si `count < limit`, es última página. Simple, sin endpoint extra.

---

### 4.3 ClientDetailPage (NEW)

**Ubicación:** `src/pages/ClientDetailPage.tsx`
**Ruta:** `/clients/:id`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  ← Volver    Peluquería El Corte                │
│              WhatsApp: 573001234567             │
│              Tipo: peluqueria | Activo: ✅       │
│              [✏️ Editar] [🗑️ Desactivar]        │
│  ────────────────────────────────────────────── │
│                                                 │
│  Agentes IA (3)                  [+ Nuevo Agente]│
│  ┌─────────────────────────────────────────────┐│
│  │ Bot Ventas   │ asistente de ventas... │ ✅   ││
│  │ Bot Soporte  │ asistente técnico...   │ ✅   ││
│  │ Bot Inactivo │ ...                   │ ❌   ││
│  └─────────────────────────────────────────────┘│
└────────────────────────────────────────────────┘
```

**Estados:**

| Estado | UI |
|---|---|
| `loading` (cliente) | Skeleton card grande |
| `error` (cliente 404) | "Cliente no encontrado" + botón "Volver a clientes" |
| `loaded` | Datos cliente + tabla agentes |
| `agents-loading` | Skeleton table agentes (3 filas) |
| `agents-empty` | "Este cliente no tiene agentes" + botón "Crear agente" |
| `agents-error` | Banner "Error al cargar agentes" |
| `deactivating` | Botón desactivar deshabilitado + spinner |
| `after-deactivate` | Toast "Cliente desactivado" + navigate a `/clients` |

**Funcionalidades:**

1. **Fetch cliente:** `useQuery({ queryKey: ['client', id], queryFn: () => getClient(id) })`.
2. **Fetch agentes:** `useQuery({ queryKey: ['agents', id], queryFn: () => listAgentsByClient(id) })`.
3. **Editar cliente:** botón abre modal `ClientForm` en modo edición (pre-relleno con datos actuales). `onSuccess` → invalidate `['client', id]`.
4. **Desactivar cliente:** `useMutation` → `deactivateClient(id)`. Al confirmar (modal confirmación), ejecuta. `onSuccess` → invalidate + navigate a `/clients`.
5. **Nuevo agente:** botón "Nuevo Agente" abre modal `AgentForm` con `clientId` pre-seteado.
6. **Click en agente:** navega a `/agents/:agentId`.

---

### 4.4 AgentsPage (NEW)

**Ubicación:** `src/pages/AgentsPage.tsx`
**Ruta:** `/agents`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  Agentes IA                                     │
│  ────────────────────────────────────────────── │
│  ⚠ No se puede listar todos los agentes sin     │
│    un endpoint global.                           │
│                                                 │
│  Solución: mostrar buscador de agentes por ID   │
│  O: listar clientes primero → seleccionar uno   │
│    para ver sus agentes.                         │
└────────────────────────────────────────────────┘
```

**Problema detectado:** No existe endpoint `GET /api/v1/agents?limit=&offset=` (listado global de agentes). Los agentes solo se listan por cliente (`GET /api/v1/clients/{id}/agents`).

**Solución KISS — dos opciones:**

**Opción A (elegida):** AgentsPage actúa como "selector de cliente → agentes":
1. Fetch `listClients(200, 0)` → dropdown/selector de cliente.
2. Al seleccionar, fetch `listAgentsByClient(clientId)` → tabla.
3. Si 0 clientes, mostrar estado empty.

**Opción B (alternativa si se añade endpoint):** Listado global con paginación + búsqueda.

**Estados:**

| Estado | UI |
|---|---|
| `loading clients` | Skeleton dropdown |
| `no clients` | "Crea un cliente primero para poder crear agentes" + link a `/clients` |
| `client selected, agents loading` | Skeleton tabla |
| `client selected, agents empty` | "Este cliente no tiene agentes" + botón "Crear agente" |
| `loaded` | Tabla agentes del cliente seleccionado |

**Funcionalidades:**
1. Selector cliente (dropdown con nombre + negocio).
2. Tabla agentes: nombre, personalidad (truncada 80 chars), tools count, activo.
3. Click fila → `/agents/:id`.
4. Botón "Nuevo Agente" → abre `AgentForm`.

---

### 4.5 AgentDetailPage (NEW)

**Ubicación:** `src/pages/AgentDetailPage.tsx`
**Ruta:** `/agents/:id`

**Layout:**

```
┌────────────────────────────────────────────────┐
│  ← Volver     Bot Ventas                        │
│               Cliente: Peluquería El Corte       │
│               Estado: Activo ✅                  │
│               [✏️ Editar] [🗑️ Desactivar]       │
│                                                  │
│  Personalidad                                    │
│  ┌──────────────────────────────────────────────┐│
│  │ Eres un asistente de ventas amable y...       ││
│  │ (texto completo del system prompt)            ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│  Tools (2)                                       │
│  ┌──────────────────────────────────────────────┐│
│  │ 📋 book_appointment                          ││
│  │    Reservar cita                             ││
│  │    POST https://n8n.example.com/book         ││
│  │ ─────────────────────────────────────────    ││
│  │ 📋 send_catalog                              ││
│  │    Enviar catálogo de productos               ││
│  │    POST https://n8n.example.com/catalog      ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│  Knowledge Base                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ kb-precios-2026, kb-faq-general              ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│  Zona peligrosa                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ ⚠️ Eliminar permanentemente                   ││
│  │    [🗑️ Eliminar agente]                      ││
│  └──────────────────────────────────────────────┘│
└────────────────────────────────────────────────┘
```

**Estados:**

| Estado | UI |
|---|---|
| `loading` | Skeleton: card con 3 bloques grises |
| `error 404` | "Agente no encontrado" + botón volver |
| `error generic` | Banner error + retry |
| `loaded` | Datos completos del agente |
| `deactivating` | Botón desactivar con spinner |
| `deleting` | Botón eliminar con spinner |
| `after-delete` | Toast "Agente eliminado" + navigate a `/clients/:clientId` o `/agents` |

**Funcionalidades:**

1. **Fetch agente:** `useQuery({ queryKey: ['agent', id], queryFn: () => getAgent(id) })`.
2. **Fetch nombre cliente:** usando `getClient(agent.client_id)` para mostrar breadcrumb. O `useQuery` extra.
3. **Editar:** botón → modal `AgentForm` en modo edición.
4. **Desactivar:** `useMutation` → `deactivateAgent(id)`. Confirmación previa.
5. **Eliminar permanente:** `useMutation` → `deleteAgentPermanent(id)`. Confirmación doble ("¿Estás seguro? Esta acción no se puede deshacer"). `onSuccess` → navigate back.
6. **Volver:** `navigate(-1)` o `navigate(/agents)`.

**Visualización de tools:** Cada tool como card con:
- Nombre (bold) + descripción
- Endpoint mostrado en mono gris (si existe)
- Ícono `Wrench` de lucide-react

---

## 5. Components Specification

### 5.1 ClientForm (NEW)

**Ubicación:** `src/components/ClientForm.tsx`
**Tipo:** Modal (dialog con overlay oscuro + blur)

**Props:**
```typescript
interface ClientFormProps {
  isOpen: boolean;
  onClose: () => void;
  client?: ClientData;        // undefined = crear, definido = editar
  onSuccess?: () => void;
}
```

**Campos:**
| Campo | Tipo | Validación |
|---|---|---|
| Nombre | text input | requerido, max 200 chars |
| Tipo de negocio | `<select>` | requerido. Opciones: peluqueria, bar, restaurante, contador, fonatero, tienda, gimnasio, clinica, otro |
| WhatsApp | text input | requerido, solo dígitos, min 10 chars |

**Estados:**
| Estado | UI |
|---|---|
| `idle` | Form vacío (crear) o pre-relleno (editar) |
| `submitting` | Botón guardar con spinner, campos disabled |
| `error` (validación) | Mensajes rojos bajo cada campo |
| `error` (API, p.ej WhatsApp duplicado) | Banner rojo dentro del modal con `detail` del error |
| `success` | Modal se cierra, `onSuccess` disparado |

**Flujo:**
1. Click "Nuevo Cliente" → abre modal.
2. Llenar campos → Submit.
3. `useMutation` llama a `createClient` o `updateClient`.
4. `onError` → mostrar mensaje API.
5. `onSuccess` → invalidar queries + cerrar modal + toast.

**Validación frontend (KISS, sin Zod):**
- Nombre: `value.trim().length === 0` → "El nombre es obligatorio".
- WhatsApp: `/^\d{10,}$/` → "Mínimo 10 dígitos, solo números".
- Tipo negocio: `value === ""` → "Selecciona un tipo".

### 5.2 AgentForm (NEW)

**Ubicación:** `src/components/AgentForm.tsx`
**Tipo:** Modal

**Props:**
```typescript
interface AgentFormProps {
  isOpen: boolean;
  onClose: () => void;
  clientId: string;           // siempre requerido (crear o editar)
  agent?: AgentData;          // undefined = crear, definido = editar
  onSuccess?: () => void;
}
```

**Campos:**
| Campo | Tipo | Validación |
|---|---|---|
| Nombre | text input | requerido, max 200 chars |
| Personalidad | `<textarea>` | requerido, min 10 chars, max 5000 |
| Tools | lista dinámica (add/remove) | Cada tool: name, description, endpoint (opcional) |
| Knowledge Base Refs | tags input o textarea (comas) | opcional |

**Tool sub-form:** cada tool tiene 3 campos:
- `name`: text (requerido)
- `description`: text (requerido)
- `endpoint`: text (opcional, placeholder "https://...")

Botón "+ Añadir tool" agrega fila. Botón 🗑️ elimina tool.

**Estados:**
| Estado | UI |
|---|---|
| `idle` | Form vacío o pre-relleno |
| `submitting` | Botón con spinner |
| `error validación` | Campos marcados en rojo |
| `error API` | Banner dentro del modal |

**Validación:**
- Nombre: no vacío.
- Personalidad: `value.trim().length < 10` → "Mínimo 10 caracteres".
- Tools: cada tool debe tener name + description no vacíos.

### 5.3 Pagination (NEW)

**Ubicación:** `src/components/Pagination.tsx`

**Props:**
```typescript
interface PaginationProps {
  currentPage: number;        // 1-based
  totalPages: number;
  onPageChange: (page: number) => void;
}
```

**Layout:** `← Anterior   Página 3 de 10   Siguiente →`

- Botones deshabilitados si `currentPage === 1` (anterior) o `currentPage === totalPages` (siguiente).
- Si `totalPages <= 1`, no renderiza nada.
- Estilo: fondo `zinc-900`, texto `zinc-400`, hover `zinc-700`, activo `amber-500`.

---

## 6. Routing (App.tsx Changes)

**Rutas actuales:**
```tsx
<Route path="/login" element={<LoginPage />} />
<Route element={<AdminLayout />}>
  <Route path="/" element={<DashboardPage />} />
</Route>
```

**Rutas nuevas:**
```tsx
<Route path="/login" element={<LoginPage />} />
<Route element={<AdminLayout />}>
  <Route path="/" element={<DashboardPage />} />
  <Route path="/clients" element={<ClientsPage />} />
  <Route path="/clients/:id" element={<ClientDetailPage />} />
  <Route path="/agents" element={<AgentsPage />} />
  <Route path="/agents/:id" element={<AgentDetailPage />} />
</Route>
```

**Lazy loading:** todas las páginas nuevas usan `lazy(() => import(...))` como las existentes.

---

## 7. Sidebar Verification

Sidebar ya tiene links correctos:
- `/` → Dashboard ✅
- `/clients` → Clientes ✅
- `/agents` → Agentes IA ✅
- `/conversations` → Conversaciones (placeholder, no implementado aún) ⚠️

No se requiere modificar Sidebar. Si `/conversations` no existe, se puede ocultar o redirigir a "próximamente".

---

## 8. Theme & Visual Consistency

**Paleta (Tailwind v4):**
| Uso | Clase |
|---|---|
| Fondo página | `bg-black` |
| Cards/paneles | `bg-zinc-900 border border-zinc-800 rounded-xl` |
| Inputs | `bg-zinc-950 border-zinc-800 rounded-lg` |
| Botón primario | `bg-amber-500 text-black font-semibold rounded-lg hover:bg-amber-400` |
| Botón secundario | `bg-zinc-800 text-zinc-300 hover:bg-zinc-700 border-zinc-700` |
| Botón peligro | `bg-red-500/10 text-red-400 hover:bg-red-500/20 border-red-500/20` |
| Texto principal | `text-white` |
| Texto secundario | `text-zinc-400` / `text-zinc-500` |
| Texto terciario | `text-zinc-600` |
| Badge activo | `bg-emerald-500/10 text-emerald-400` |
| Badge inactivo | `bg-zinc-800 text-zinc-500` |
| Skeleton | `bg-zinc-800 animate-pulse rounded` |

**Tipografía:** sistema (sin fuente externa). Tailwind default.

**Iconos:** `lucide-react` (ya instalado). Usar `stroke-[1.5]` consistente con Sidebar.

**Modales:** overlay `bg-black/80 backdrop-blur-sm`. Contenido `bg-zinc-900 border-zinc-800 rounded-2xl`. Animación fade-in.

**Toasts:** posición bottom-right. Color verde éxito, rojo error. Auto-dismiss 4s. Implementación simple: estado React + portal, sin librería.

---

## 9. User Flows

### Flow 1: Crear cliente y agente

```
Dashboard (0 clientes)
  → Click "Crear Cliente" en empty state
  → ClientForm modal: llenar datos → Submit
  → Toast "Cliente creado" → redirige a /clients/:newId
  → ClientDetailPage: click "Nuevo Agente"
  → AgentForm modal: llenar datos + tools → Submit
  → Toast "Agente creado" → aparece en tabla
```

### Flow 2: Buscar cliente por WhatsApp

```
ClientsPage → escribir WhatsApp en buscador → click Buscar
  → Si encontrado: mostrar tarjeta con datos → click → ClientDetailPage
  → Si no encontrado: mensaje "No encontrado"
```

### Flow 3: Editar agente

```
AgentDetailPage → click "Editar"
  → AgentForm modal pre-relleno → modificar personalidad → Submit
  → Toast "Agente actualizado" → datos refrescados en página
```

### Flow 4: Eliminar agente permanentemente

```
AgentDetailPage → scroll a "Zona peligrosa" → click "Eliminar agente"
  → Modal confirmación: "¿Estás seguro? Esta acción no se puede deshacer"
  → Click "Eliminar" → spinner → toast "Agente eliminado" → navigate a /agents
```

### Flow 5: Desactivar cliente

```
ClientDetailPage → click "Desactivar"
  → Modal confirmación: "¿Desactivar cliente? Sus agentes también se desactivarán"
  → Click "Desactivar" → toast "Cliente desactivado" → navigate a /clients
```

---

## 10. Error Handling Strategy

| Capa | Estrategia |
|---|---|
| `api/` functions | Lanzan `ApiError {detail, error_type}`. `apiFetch` maneja !res.ok. |
| `useQuery` | `onError` → mostrar banner/toast en página. Retry 1 vez (config global QueryClient). |
| `useMutation` | `onError` → mostrar error API en modal o toast. |
| 404 específico | `error.error_type === 'client_not_found'` o `'agent_not_found'` → UI específica. |
| 400 validación | `error.error_type === 'invalid_client'` o `'invalid_agent'` → mostrar mensaje en formulario. |
| Red/500 | Mostrar "Error del servidor. Intenta de nuevo." + botón retry. |

**Error boundary (opcional, futuro):** componente wrapper que captura crashes y muestra pantalla "Algo salió mal".

---

## 11. States Summary Matrix

| Página | Loading | Empty | Error | Edge Cases |
|---|---|---|---|---|
| Dashboard | 4 skeleton cards | Empty state con CTAs | Banner + retry | API lenta (>3s) |
| ClientsPage | Skeleton table 5 rows | "No hay clientes" + CTA | Banner + retry | WhatsApp search not found |
| ClientDetailPage | 2 skeletons (cliente + agentes) | Agentes: "Sin agentes" | 404 page, banner | Cliente desactivado (mostrar badge) |
| AgentsPage | Skeleton dropdown + tabla | Selector cliente vacío o cliente sin agentes | Banner + retry | — |
| AgentDetailPage | 3 bloques skeleton | N/A (siempre hay datos si existe) | 404 page, banner | Agente desactivado |
| ClientForm modal | Botón con spinner | N/A | Campos rojos, banner API | WhatsApp duplicado |
| AgentForm modal | Botón con spinner | N/A | Campos rojos, banner API | Tools vacíos permitidos |

---

## 12. Files Structure (Final)

```
frontend-dashboard/src/
├── api/
│   ├── config.ts          ← NEW
│   ├── client.ts          ← NEW
│   └── agent.ts           ← NEW
├── pages/
│   ├── LoginPage.tsx      (sin cambios)
│   ├── DashboardPage.tsx  (MODIFICAR: integrar API)
│   ├── ClientsPage.tsx    ← NEW
│   ├── ClientDetailPage.tsx ← NEW
│   ├── AgentsPage.tsx     ← NEW
│   └── AgentDetailPage.tsx ← NEW
├── components/
│   ├── Sidebar.tsx        (sin cambios)
│   ├── ClientForm.tsx     ← NEW
│   ├── AgentForm.tsx      ← NEW
│   ├── Pagination.tsx     ← NEW
│   └── Toast.tsx          ← NEW (sistema simple de toasts)
├── App.tsx                (MODIFICAR: agregar rutas)
├── main.tsx               (sin cambios)
└── index.css              (sin cambios)
```

**Total archivos nuevos:** 10
**Total archivos modificados:** 2 (DashboardPage.tsx, App.tsx)

---

## 13. What This Spec Does NOT Cover

- Sistema de autenticación (login real con JWT)
- Página de Conversaciones (requiere endpoints de mensajes)
- Tests (se especificarán en spec separada de tests con TDD)
- Analytics / gráficos avanzados en Dashboard
- Responsive design detallado (usa Tailwind responsive utilities, mobile-first donde aplique)
- Internacionalización (i18n)
- PWA / Service Workers

---

## 14. Approval Checklist

- [ ] API contracts alineados con backend (spec-http-routers.md)
- [ ] Todas las páginas con estados loading/empty/error
- [ ] Tema visual consistente con Login + Sidebar existentes
- [ ] Componentes reutilizables (ClientForm, AgentForm, Pagination)
- [ ] Sin dependencias nuevas (solo lo ya instalado)
- [ ] Rutas definidas en App.tsx
- [ ] Flujos de usuario documentados
