# API Documentation for Agencia IA Dashboard

## Overview

The API layer is responsible for communicating with the backend REST server at `http://localhost:8000`. All endpoints are under the `/api/v1/` prefix.

The API is built with a custom client wrapper (`api/config.ts`) that:
- Automatically injects the JWT token from `localStorage` as an `Authorization: Bearer <token>` header in every HTTP request
- Converts successful responses to typed data structures (`ClientData`, `AgentData`, etc.)
- Normalizes backend error responses (`{ detail?: string; error_type?: string }`) into `ApiError` objects with a `message` field
- Maintains a consistent error handling pattern throughout the entire application

All modules in `api/` export TypeScript functions that encapsulate specific endpoint calls, allowing pages and components to fetch/update data without having to handle URLs, headers, or raw JSON directly.

## API Modules

| Module | Functions | HTTP Methods | Endpoints | Cache Control |
|--------|----------|-------------|------------|---------------|
| `auth.ts` | `login`, `register`, `fetchMe` | POST (login/register), GET (fetchMe) | `/api/v1/auth/login`, `/api/v1/auth/register`, `/api/v1/auth/me` | No cache (sensitive data) |
| `client.ts` | `fetchClients`, `fetchClient`, `searchClientByWhatsapp`, `createClient`, `updateClient`, `deactivateClient` | GET (fetch), POST (create), PUT (update), DELETE (deactivate) | `/api/v1/clients`, `/api/v1/clients/:id`, `/api/v1/clients/search/whatsapp`, `/api/v1/clients`, `/api/v1/clients/:id`, `/api/v1/clients/:id` | React Query: `staleTime: 5min`, `retry: 1` |
| `agent.ts` | `fetchAgentsByClient`, `fetchAgent`, `createAgent`, `updateAgent`, `deactivateAgent`, `deleteAgent` | GET (fetch), POST (create), PUT (update), DELETE (deactivate), DELETE (delete) | `/api/v1/clients/:clientId/agents`, `/api/v1/agents/:id`, `/api/v1/agents`, `/api/v1/agents/:id`, `/api/v1/agents/:id`, `/api/v1/agents/:id` | Same base query config (`staleTime: 5min`, `retry: 1`) |
| `conversation.ts` | `fetchConversations`, `fetchConversationMessages`, `fetchConversationStats` | GET | `/api/v1/clients/:clientId/conversations`, `/api/v1/conversations/:id/messages`, `/api/v1/conversations/:id/stats` | Same base query config |
| `email.ts` | `sendEmail`, `fetchEmails`, `fetchEmailStats`, `fetchEmailTemplates` | POST (send), GET (list, stats, templates) | `/api/v1/emails`, `/api/v1/clients/:id/emails`, `/api/v1/emails/stats`, `/api/v1/emails/templates` | Same base query config |
| `feedback.ts` | `fetchFeedbackList`, `createFeedback`, `fetchFeedbackStats` | GET (list, stats), POST (create) | `/api/v1/feedback`, `/api/v1/feedback/stats` | Same base query config |
| `landing.ts` | `fetchLandingPublicConfig`, `submitLandingForm`, `fetchLandingConfig`, `updateLandingConfig` | GET (public, :id), POST (submit), PUT (update) | `/api/v1/landings/public/:slug`, `/api/v1/landings`, `/api/v1/landings/:id`, `/api/v1/landings/:id` | Same base query config |
| `lead.ts` | `fetchLeads`, `updateLead`, `fetchLeadStats`, `sendProactiveMessage`, `createLead` | GET (list, stats), POST (create), PUT (update), POST (send) | `/api/v1/leads`, `/api/v1/leads/:id`, `/api/v1/leads/stats`, `/api/v1/leads/:id/send-proactive-message`, `/api/v1/leads` | Same base query config |
| `template.ts` | `fetchTemplates`, `applyTemplate` | GET (list), POST (apply) | `/api/v1/templates`, `/api/v1/templates/:slug/apply` | Same base query config |

## API Error Structure

### Base Object

```typescript
interface ApiError {
  message: string;
  error_type?: string;
}
```

The backend error response format expected by the client:
```json
[
  { "detail": "Error description" },
  { "error_type": "validation_error", "field": "email" }
]
```

This is normalized into an `ApiError` object with a `message` field.

### Usage Examples

```typescript
import { apiFetch } from '@/api/config';
import { ApiError } from '@/api/types';

// Example: Component error handling
function SomeComponent() {
  const { toast } = useToast();

  const handleError = (err: unknown) => {
    if (err instanceof ApiError) {
      toast('error', err.message);
    } else {
      toast('error', 'An unexpected error occurred');
    }
  };

  // Or within useMutation
  const mutation = useMutation({
    mutationFn: () => apiFetch<SomeResponse>('POST', '/api/endpoint', payload),
    onError: (err) => {
      if (err instanceof ApiError) {
        setApiError(err.message);
      }
    }
  });
}
```

### Error Flow Paths

1. **Validation Errors (400, 422)**
   - `ApiError.message` typically comes from `detail` returned by the backend
   - The client attempts to parse and provide user-friendly error messages

2. **Authentication/Authorization Errors (401, 403)**
   - Backend usually returns `detail: "Token invalid or expired"`
   - Client normalizes this for UI display (toast, banner, dialog)

3. **Network/Server Errors (500, timeout, 502)**
   - Network failure or server crashed
   - `ApiError.message` might be `Error on network or server`

## React Query State Management and Caching

### Standard Query Policies

All queries use `/api/v1/` endpoints from `config.ts`:

```typescript
// api/config.ts (exported in most API modules)
export { apiFetch } from './config';

// In your page/component:
const query = useQuery({
  queryKey: ['clients', page],
  queryFn: () => fetchClients(PAGE_SIZE, (page - 1) * PAGE_SIZE),
  staleTime: 1000 * 60 * 5,  // 5 mins
  retry: 1,
});
```

### Transition Behavior

- **Initial Load**: Shows skeleton loading
- **Success**: Renders data
- **Error**: Shows error banner with retry button
- **Background Update**: UI remains unchanged (React Query handles updates silently)

### Query Invalidation

When creating/updating clients or agents, related queries are invalidated:

```typescript
// Mutation API in ClientForm.tsx
const mutation = useMutation({
  mutationFn: () => createClient(payload),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['clients'] });
    // Redirect or close modal
  }
});
```

### Automatic Stale-Time

If a query hasn't been accessed for 30s, React Query will pause it (customizable in the base client config).

## API Data Models

### auth.ts

```typescript
interface LoginInput {
  email: string;
  password: string;
}

interface RegisterInput {
  email: string;
  password: string;
  business_name: string;
  whatsapp_number: string;
}
```

### client.ts

```typescript
interface ClientData {
  id: string;
  email: string;
  name: string;
  business_name: string;
  business_type: string;
  whatsapp_number: string;
  is_active: boolean;
  subscription_status: 'active' | 'inactive';
  agent_count: number;
}

interface CreateClientInput {
  email: string;
  password: string;
  business_name: string;
  whatsapp_number: string;
  business_type: string;
}

interface UpdateClientInput {
  name?: string;
  business_name?: string;
  whatsapp_number?: string;
  business_type?: string;
  is_active?: boolean;
}
```

### agent.ts

```typescript
interface AgentData {
  id: string;
  client_id: string;
  name: string;
  personality: string;
  is_active: boolean;
  tools: AgentToolData[];
  knowledge_base_refs: string[];
  settings?: object;
}

interface AgentToolData {
  name: string;
  description: string;
  endpoint?: string;
}

interface CreateAgentInput {
  client_id: string;
  name: string;
  personality: string;
  tools?: AgentToolData[];
  knowledge_base_refs?: string[];
}

interface UpdateAgentInput {
  name?: string;
  personality?: string;
  tools?: AgentToolData[];
  knowledge_base_refs?: string[];
  is_active?: boolean;
}
```

### conversation.ts

```typescript
interface Conversation {
  id: string;
  client_id: string;
  agent_id: string;
  customer_number: string;
  started_at?: string;
  ended_at?: string;
  status: 'active' | 'archived';
  message_count?: number;
}
```

### email.ts

```typescript
interface EmailData {
  id: string;
  client_id: string;
  to: string;
  subject: string;
  body: string;
  sequence?: number;
  sent_at?: string;
}

interface SendEmailInput {
  to: string;
  subject: string;
  body: string;
  sequence?: number;
  rubro?: string;
}
```

### feedback.ts

```typescript
interface FeedbackData {
  id: string;
  client_id: string;
  agent_id?: string;
  rating: number;
  comment?: string;
  created_at: string;
}

interface CreateFeedbackInput {
  rating: number;
  comment?: string;
  agent_id?: string;
}
```

### landing.ts

```typescript
interface LandingConfig {
  landing_slug: string;
  landing_title: string;
  landing_description: string;
  landing_active: boolean;
  landing_auto_reply: string;
  landing_primary_color: string;
  client_id: string;
}
```

### lead.ts

```typescript
interface LeadData {
  id: string;
  client_id: string;
  source: string;
  source_detail?: string;
  status: 'new' | 'contacted' | 'converted';
  contacted_at?: string;
  notes?: string;
}

interface UpdateLeadInput {
  status?: 'new' | 'contacted' | 'converted';
  contacted_at?: string;
  notes?: string;
}
```

### template.ts

```typescript
interface TemplateData {
  slug: string;
  name: string;
  description: string;
  agent_config: {
    personality: string;
    tools: AgentToolData[];
    knowledge_base_refs: string[];
    initial_settings?: object;
  };
  tools_count: number;
  is_public: boolean;
  created_at?: string;
  updated_at?: string;
}
```