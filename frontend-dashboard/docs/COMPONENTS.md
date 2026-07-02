# Componentes

## Toast — Sistema de Notificaciones

Sistema de notificaciones toast vía Context API. Provee `ToastProvider` y hook `useToast`.

```tsx
// App.tsx — envolver al inicio
<ToastProvider>
  <App />
</ToastProvider>
```

```tsx
// Cualquier componente
import { useToast } from "@/components/Toast";

function MiComponente() {
  const { toast } = useToast();
  toast("success", "Cliente creado correctamente");
  toast("error",   "Error al guardar");
}
```

### Props / API

| Prop | Tipo | Descripción |
|------|------|-------------|
| `toast(type, message)` | `(type: "success" \| "error", message: string) => void` | Muestra toast. Auto-dismiss a los 4s |
| `ToastProvider` | `{ children: ReactNode }` | Envuelve la app |

---

## ProtectedRoute — Guard de Autenticación

Protege rutas. Muestra spinner mientras carga, redirige a `/login` si no autenticado.

```tsx
<Routes>
  <Route element={<ProtectedRoute />}>
    <Route element={<AppLayout />}>
      <Route path="/app" element={<DashboardPage />} />
    </Route>
  </Route>
</Routes>
```

### Props

Ninguna. Renderiza `<Outlet />` si está autenticado.

---

## AdminRoute — Guard de Superadmin

Similar a `ProtectedRoute` pero además verifica `role === "superadmin"`.

```tsx
<Route element={<ProtectedRoute />}>
  <Route element={<AdminRoute />}>
    <Route path="/app/clients" element={<ClientsPage />} />
  </Route>
</Route>
```

---

## ClientRoute — Guard de Cliente

Verifica `role === "client_admin"`. Redirige a `/app` si no coincide.

```tsx
<Route element={<ProtectedRoute />}>
  <Route element={<ClientRoute />}>
    <Route path="/app/leads" element={<LeadsPage />} />
  </Route>
</Route>
```

---

## Sidebar — Navegación Principal

Sidebar colapsable con navegación por roles. Guarda estado en `localStorage`.

```tsx
<Sidebar className="hidden md:flex" onCloseMobile={() => setOpen(false)} />
```

### Props

| Prop | Tipo | Descripción |
|------|------|-------------|
| `className?` | `string` | Clases adicionales |
| `onCloseMobile?` | `() => void` | Callback al hacer click en nav (mobile) |

### Navegación por Rol

**Superadmin**: Dashboard, Clientes, Agentes IA, Plantillas, Conversaciones
**Client Admin**: Dashboard, Conversaciones, Leads, Perfil

---

## ClientForm — Modal Crear/Editar Cliente

Modal para crear o editar clientes. Validación client-side antes de enviar.

```tsx
<ClientForm
  isOpen={showForm}
  onClose={() => setShowForm(false)}
  client={selectedClient}   // opcional — modo edición
  onSuccess={() => refetch()}
/>
```

### Props

| Prop | Tipo | Descripción |
|------|------|-------------|
| `isOpen` | `boolean` | Controla visibilidad del modal |
| `onClose` | `() => void` | Cierra el modal |
| `client?` | `ClientData` | Si se pasa, entra en modo edición |
| `onSuccess?` | `() => void` | Callback tras crear/editar |

### Validación

| Campo | Regla |
|-------|-------|
| `name` | Requerido, máx 200 chars |
| `business_type` | Requerido, selección de lista |
| `whatsapp_number` | Mínimo 10 dígitos, solo números |

---

## AgentForm — Constructor de Agentes

Modal para crear/editar agentes con tools dinámicas y KB refs.

```tsx
<AgentForm
  isOpen={showForm}
  onClose={() => setShowForm(false)}
  clientId="abc-123"
  agent={selectedAgent}
  onSuccess={() => refetch()}
/>
```

### Props

| Prop | Tipo | Descripción |
|------|------|-------------|
| `isOpen` | `boolean` | Controla visibilidad |
| `onClose` | `() => void` | Cierra modal |
| `clientId` | `string` | ID del cliente propietario |
| `agent?` | `AgentData` | Modo edición |
| `onSuccess?` | `() => void` | Callback post-creación |

### Tools (dinámicas)

Cada tool tiene: `name`, `description`, `endpoint` (opcional). Se pueden añadir/eliminar.

### Validación

| Campo | Regla |
|-------|-------|
| `name` | Requerido |
| `personality` | Mínimo 10 caracteres |

---

## Pagination — Navegación de Páginas

Renderiza botones "Anterior / Siguiente" con indicador de página actual.

```tsx
<Pagination
  currentPage={page}
  totalPages={totalPages}
  onPageChange={setPage}
/>
```

### Props

| Prop | Tipo | Descripción |
|------|------|-------------|
| `currentPage` | `number` | Página actual |
| `totalPages` | `number` | Total de páginas |
| `onPageChange` | `(page: number) => void` | Callback al cambiar página |

No renderiza nada si `totalPages <= 1`.
