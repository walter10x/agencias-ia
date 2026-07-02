# Arquitectura del Proyecto

## Descripción General

Agencia IA es una dashboard multi-tenant SaaS para gestionar agentes de inteligencia artificial en WhatsApp. La plataforma permite a negocios conectar agentes IA con sus clientes de WhatsApp para automatizar conversaciones, generar clientes potenciales y crecer sus negocios.

## Ubicación Física y Arquitectura

```
frontend-dashboard/
├── src/
│   ├── api/                          # 10 módulos de API con ~30 funciones
│   │   ├── auth.ts                   # Autenticación, inicio de sesión, registro
│   │   ├── client.ts                 # CRUD de clientes (4 funciones)
│   │   ├── agent.ts                  # CRUD de agentes (6 funciones)
│   │   ├── conversation.ts           # Gestión de conversaciones (3 funciones)
│   │   ├── email.ts                  # Integración de emails (4 funciones)
│   │   ├── feedback.ts               # Sistema de feedback (3 funciones)
│   │   ├── landing.ts                # Configuración de landing pages (4 funciones)
│   │   ├── lead.ts                   # Gestión de clientes potenciales (5 funciones)
│   │   ├── template.ts               # Biblioteca de plantillas de agentes (2 funciones)
│   │   └── config.ts                 # Configuración del cliente y manejo de errores
│   ├── components/                   # 8 componentes reutilizables
│   │   ├── ClientForm.tsx            # Modal para crear/editar clientes
│   │   ├── AgentForm.tsx             # Constructor de agentes con herramientas
│   │   ├── Sidebar.tsx              # Navegación colapsable con menú
│   │   ├── Toast.tsx                # Sistema de notificaciones toast
│   │   ├── ProtectedRoute.tsx       # Componente guard de rutas protegidas
│   │   ├── AdminRoute.tsx           # Acceso solo para administradores
│   │   └── ClientRoute.tsx          # Acceso solo para clientes
│   ├── context/                      # Contexto de React
│   │   └── AuthContext.tsx          # Estado de autenticación, login/logout
│   ├── hooks/                        # Hooks personalizados
│   │   └── useAuth.ts               # Utilidades de autenticación
│   ├── pages/                        # 15 páginas principales
│   │   ├── HomePage.tsx              # Página de inicio (pública)
│   │   ├── LoginPage.tsx             # Login (pública)
│   │   ├── RegisterPage.tsx          # Registro (pública)
│   │   ├── DashboardPage.tsx         # Dashboard principal
│   │   ├── ClientsPage.tsx           # Lista de clientes
│   │   ├── ClientDetailPage.tsx      # Detalles de cliente con agentes
│   │   ├── AgentsPage.tsx            # Lista de agentes IA
│   │   ├── AgentDetailPage.tsx       # Detalles del agente
│   │   ├── ConversationsPage.tsx     # Historial de conversaciones
│   │   ├── LeadsPage.tsx              # Gestión de clientes potenciales
│   │   ├── ProfilePage.tsx           # Perfil de usuario
│   │   └── ... (mas páginas) ...
│   └── assets/                       # Imágenes, iconos, etc.
│   └── styles/                        # Archivo CSS global (si tiene)
└── public/                             # Archivos estáticos
    └── index.html
```

## Estructura de Rutas (Frontend)

### Rutas Públicas (sin autenticación)
```
/
├── /login                    # Inicio de sesión
├── /register                 # Registro de usuario
└── /landing/:slug            # Página de aterrizaje pública
```

### Rutas Protegidas (requieren autenticación)
```
/app                           # Dashboard principal
a|
├── /app/clients               # Gestión de clientes (sólo superadmin)
├── /app/clients/:id            # Detalles del cliente (sólo superadmin)
├── /app/agents                # Gestión de agentes IA (sólo superadmin)
├── /app/agents/:id            # Detalles del agente (sólo superadmin)
├── /app/templates             # Biblioteca de plantillas (sólo superadmin)
├── /app/conversations          # Historial de conversaciones (sólo superadmin y cliente)
├── /app/leads                 # Gestión de clientes potenciales (sólo superadmin y cliente)
├── /app/profile               # Perfil de usuario (sólo cliente)
```

### Modelo de Autorización por Roles

**1. Superadmin**
- Paquetes: Todos los paquetes disponibles
- Acciones: Gestionar clientes, agentes, plantillas, agentes, conversaciones, clientes potenciales
- Directorios: Todas las páginas (`/app/*`)

**2. Cliente (Dueño de negocio)**
- Paquetes: Los paquetes asignados a su negocio
- Acciones: Gestionar conversaciones, clientes potenciales, perfil
- Directorios: `/app/conversations`, `/app/leads`, `/app/profile`

**3. Usuario de Negocio (Empleado/Colaborador)**
- Paquetes: Los paquetes asignados a su negocio (sin acceso a configuración)
- Acciones: Ver conversaciones, clientes potenciales
- Directorios: `/app/conversations`, `/app/leads`

**4. Invitado (Sin acceso)**
- No se permiten accesos

## Flujo de Datos

### Autenticación
```
LoginPage.tsx → api/auth.ts:login() (POST /api/v1/auth/login)
                     ↓ (JWT en cookie)
                AuthContext.setToken()
                     ↓
                api/config.ts intercepta Authorization header
                     ↓
                /api/me → api/auth.ts:fetchMe() (GET /api/v1/auth/me)
                     ↓
                AuthContext.setUser(), Sidebar.show navigation
```

### Dashboard y Gestión de Clientes
```
DashboardPage.tsx → useQuery → api/client.ts:fetchClients(PAGE_SIZE, offset)
                     ↓
                api/client.ts:fetchClients() (GET /api/v1/clients?limit=X&offset=Y)
                     ↓
                respuesta.json() → items, count | isLoading, isError
                     ↓
                Stats grid + tabla de clientes mostrados en UI
```

### Constructor de Agentes
```
AgentsPage.tsx → Nuevo Agente button abre AgentForm.tsx
                     ↓
                AgentForm.tsx → mutation → api/agent.ts:createAgent(clientId, payload)
                     ↓
                api/agent.ts:createAgent() (POST /api/v1/agents)
                     ↓
                mutation.onSuccess → toast, invalidates ["agents"], onClose
```

## Tecnologías y Stack de Desarrollo

### Frontend
- **Framework**: React 19
- **Enrutador**: React Router v7
- **Cliente de API**: Custom wrapper con interceptores de auth
- **Gestión de estado**: TanStack Query (React Query) v5
- **CSS**: Tailwind CSS v4 ( Diseñado con acetado, tema oscuro completo )
- **Componentes**: Componente-based sin librerías UI externas
- **Testing**: Vitest con @testing-library/react
- **Linting**: Prettier + ESLint (si está configurado)
- **Build**: Vite ( Hasta 11 chunks, prefetching )

### Backend (Servidor API)
- **Servidor**: Desconocido (Se requiere en `http://localhost:8000`)
- **Documentación de API**: Swagger/Redoc (si está disponible)

### Proxy de Desarrollo
```
vite.config.ts

proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    secure: false
  },
  '/webhook': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    secure: false
  }
}
```

## Experiencia de Usuario y Proceso de Trabajo

### Flujo de Autenticación
1. **Login** - Página pública de inicio de sesión
2. **Dashboard principal** - Redirección con verificación de autorización basada en rol
3. **Navegación por sidebar** - Colapsable, con íconos, grupo de enlaces basadas en roles
4. **Gestión de modales** - Formularios (Cliente, Agente) en modales encima del contenido
5. **Pagación** - Cliente con botones para siguiente/anterior página
6. **Búsqueda** - Cliente de WhatsApp + botón de búsqueda
7. **Notificaciones** - Sistema toast para feedback de mutaciones (crear, actualizar, eliminar)
8. **Flujos de edición** - Click en fila abre página de detalle o modal correspondiente

### Sistema de Componentes
- **ToastProvider** - Sistema de notificaciones toast centralizado (portal, contexto)
- **ProtectedRoute** - Envuelve las rutas protegidas, redirige a `/login` si no está autenticado
- **AdminRoute / ClientRoute** - Componentes guard que restringen según rol
- **Layout compose** - `ProtectedRoute → AppLayout` (Sidebar + Outlet)
- **Fondos Glass-morphic** - `bg-zinc-900 border border-zinc-800 rounded-xl p-4`
- **Fondos de gradiente animado** - Gradientes de oro/positivo determinantes

### Stack de Testing
- **Framework**: Vitest (basado en Node)
- **Testing Library**: @testing-library/react (queries), user-event (simulación de eventos)
- **Scope cubierto**: 9 archivos de prueba (6 de API, 3 de componentes)
- **Situaciones cubiertas**: Happy path, path de error, flujos no autorizados
- **Gap reporting**: Mapeo de casos de testing cubiertos vs no cubiertos para planificación de tareas