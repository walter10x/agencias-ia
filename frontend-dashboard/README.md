# Agencia IA Dashboard

A multi-tenant SaaS platform for deploying WhatsApp AI agents to automate customer service, generate qualified leads, and grow businesses.

## Overview

Agencia IA enables businesses to connect intelligent AI agents to WhatsApp, automating customer conversations, capturing leads, and providing 24/7 support. The platform provides a clean dashboard for managing agents, clients, conversations, and analytics.

## Key Features

- **WhatsApp Integration**: Connect AI agents to customer WhatsApp conversations
- **Multi-Tenant**: Manage multiple businesses from a single dashboard
- **Agent Builder**: Create and configure AI agents with custom personalities and tools
- **Template Library**: Apply pre-built agent templates to accelerate setup
- **Analytics Dashboard**: Track conversation metrics, lead generation, and engagement
- **Role-Based Access**: Admin, client manager, and user roles with proper permissions

## Tech Stack

- **Frontend**: React 19, Vite, TypeScript
- **Styling**: Tailwind CSS v4
- **State Management**: TanStack Query (React Query)
- **Routing**: React Router v7
- **Architecture**: Component-based with prop drilling + context APIs
- **API Client**: Custom wrapper with auth interception and error handling

## Quick Start

### Prerequisites

- Node.js 24+
- Backend service running at `http://localhost:8000` (API server)

### Installation

```bash
cd frontend-dashboard
npm install
```

### Development

```bash
npm run dev
```

The frontend will start at `http://localhost:5173`. Ensure your backend is running at `http://localhost:8000` since the Vite config proxies `/api` routes there.

### Build

```bash
npm run build
```

### Testing

```bash
npm test
```

### Running Tests

All tests use Vitest with @testing-library/react. Tests are organized by feature:

**Tested:**
- Authentication flows (login, register, protected routes)
- API error handling and auth headers
- Route guards (ProtectedRoute, AdminRoute, ClientRoute)

**Not Tested (future priority):**
- Pages (Dashboard, Clients, ClientDetail, Agents, etc.)
- Form components (ClientForm, AgentForm)
- Utility components (Sidebar, Toast, Pagination)

## Project Structure

```
src/
├── api/              # API layer (10 modules)
│   ├── agent.ts      # Agent CRUD + tools
│   ├── client.ts     # Client management
│   ├── conversation.ts # Conversation & messaging
│   ├── email.ts      # Email integration
│   ├── feedback.ts   # Feedback system
│   ├── landing.ts   # Landing pages/public forms
│   ├── lead.ts      # Lead management
│   ├── template.ts  # Agent templates
│   └── config.ts     # API client + error handling
├── components/       # Shared UI components
│   ├── ClientForm.tsx      # Client creation/edit
│   ├── AgentForm.tsx       # Agent builder with tools
│   ├── Sidebar.tsx        # Navigation sidebar
│   ├── Toast.tsx          # Toast notification system
│   ├── ProtectedRoute.tsx # Auth guard component
│   ├── AdminRoute.tsx     # Admin-only access
│   └── ClientRoute.tsx    # Client-only access
├── context/           # Application context
│   └── AuthContext.tsx   # User authentication
├── hooks/             # Custom hooks
│   └── useAuth.ts        # Auth utilities
├── pages/             # Application pages (15 total)
│   ├── HomePage.tsx           # Landing page
│   ├── LoginPage.tsx          # Login
│   ├── RegisterPage.tsx       # Registration
│   ├── DashboardPage.tsx      # Main dashboard
│   ├── ClientsPage.tsx        # Client list + management
│   ├── ClientDetailPage.tsx   # Client details with agents
│   ├── AgentsPage.tsx         # Agent list
│   ├── AgentDetailPage.tsx    # Agent details + tools
│   ├── ConversationsPage.tsx  # Chat history
│   ├── LeadsPage.tsx          # Lead management
│   ├── ... (more pages) ...
├── assets/            # Static assets
└── styles/            # Global CSS (if any)
```

## Authentication

### Login Flow

1. User logs in with email and password
2. JWT token stored in `localStorage` as `auth_token`
3. Token included in all subsequent API requests via `Authorization: Bearer <token>`
4. Protected routes redirect to `/login` if user not authenticated
5. Login redirect depends on user role:
   - **Superadmin**: Full access (clients, agents, templates, conversations)
   - **Client**: Access to conversations, leads, profile

### Auth Context

`AuthContext` provides:
- `user`: Current user object (id, email, name, role)
- `login(token)`: Authenticate user and set token
- `logout()`: Clear token and redirect to login

### Protected Routes

**Route Protection Hierarchy:**
1. `ProtectedRoute` → Requires authentication
2. `AppLayout` → Applied to all `/app/*` routes
3. Role-based routes (`/app/clients`, `/app/agents`) → Only for superadmins
4. Client routes (`/app/conversations`, `/app/leads`) → Client-specific access

**Route Layout:**
```
/app
├── dashboard         (superadmin & client)
├── clients          (superadmin only)
├── clients/:id      (superadmin only)
├── agents          (superadmin only)
├── agents/:id      (superadmin only)
├── templates       (superadmin only)
├── conversations   (superadmin & client)
├── leads          (superadmin & client)
├── profile        (client only)
```

## Data Flow

### Authentication Flow

1. `LoginPage.tsx` → `api/auth.ts:login()`
2. API returns JWT in `auth_token` cookie
3. `AuthContext` stores token and fetches `/auth/me`
4. User context flows down to `Sidebar` for navigation
5. Protected routes check `user` context for access

### Client Management Flow

1. `ClientsPage.tsx` → `api/client.ts:fetchClients()`
2. Paginated API response (`limit: 10`, `offset: 0`)
3. Results displayed in table with action buttons
4. `ClientDetailPage.tsx` → `api/client.ts:fetchClient(id)`
5. Agents tab uses `api/agent.ts:fetchAgentsByClient(id)`
6. Agent management handled by `AgentForm.tsx`

### Agent Builder Flow

1. `AgentsPage.tsx` → New agent button opens `AgentForm.tsx`
2. Form collects name, personality, tools, knowledge base
3. Submit → `api/agent.ts:createAgent()` or `api/agent.ts:updateAgent()`
4. Tools dynamically added/removed with key-based state management
5. Toast notifications for success/error feedback

## API Layer

### API Overview

10 API modules with ~30 total functions, all TypeScript strongly typed:

| Module | Key Functions | Use Case |
|--------|---------------|----------|
| `auth.ts` | `login`, `register`, `fetchMe` | Authentication |
| `client.ts` | `fetchClients`, `fetchClient`, `searchClientByWhatsapp`, `createClient`, `updateClient`, `deactivateClient` | Client Management |
| `agent.ts` | `fetchAgentsByClient`, `fetchAgent`, `createAgent`, `updateAgent`, `deactivateAgent`, `deleteAgent` | Agent Management |
| `template.ts` | `fetchTemplates`, `applyTemplate` | Templates |
| `landing.ts` | `fetchLandingPublicConfig`, `submitLandingForm`, `fetchLandingConfig`, `updateLandingConfig` | Landing Pages |
| `email.ts` | `sendEmail`, `fetchEmails`, `fetchEmailStats`, `fetchEmailTemplates` | Email Integration |
| `conversation.ts` | `fetchConversations`, `fetchConversationMessages`, `fetchConversationStats` | Conversation History |
| `lead.ts` | `fetchLeads`, `updateLead`, `fetchLeadStats`, `sendProactiveMessage`, `createLead` | Lead Management |
| `feedback.ts` | `fetchFeedbackList`, `createFeedback`, `fetchFeedbackStats` | Feedback System |

### API Endpoints

All endpoints proxied through `vite.config.ts`:
- **Frontend**: `http://localhost:5173`
- **Backend**: `http://localhost:8000`

Base path: `/api/v1/` for all API calls

### Error Handling

`ApiError` class with `detail` and `error_type` fields
- HTTP 4xx/5xx → `ApiError` wrapper
- Generic error messages shown to user
- Toast notifications for user feedback

## Deployment

### Docker

```bash
# Build and run with nginx
 docker-compose up --build
```

### Environment Variables

`VITE_API_BASE_URL=http://localhost:8000` (configured in `vite.config.ts`)

### Static File Serving

Nginx configured for:
- SPA fallback (`try_files $uri $uri/ /index.html;`)
- API proxy to backend
- Static asset serving

## Testing

### Testing Stack

- **Framework**: Vitest
- **DOM Testing**: @testing-library/react
- **Assertions**: Vitest DOM (TDD approach)

### Test Quality

**Current Coverage (40 passed tests, 8 files):**
- ✅ Authentication flows
- ✅ Route protection
- ✅ Basic API error handling
- ✅ Component rendering

**Missing Coverage (future work):**
- ❌ Component testing (forms, sidebar, pagination)
- ❌ Page integration (dashboard, clients, agents)
- ❌ API integration (all 10 modules)

### Test Conventions

- Queries by test-id when available
- Mock API responses (`vi.mock('@/api/...')`)
- User event simulation (`userEvent.click()`)
- Cleanup in `afterEach`

## Contributions

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/awesome-feature`)
3. Commit your changes (`git commit -am 'Add awesome feature'`)
4. Push your branch (`git push origin feature/awesome-feature`)
5. Create a Pull Request

This project follows conventional commit structure:
```
feat: add new authentication flow
fix: resolve navigation bug in dashboard
refactor: improve code organization
```

## License

MIT