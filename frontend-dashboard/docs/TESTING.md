# Testing

## Stack

| Herramienta | Versión | Uso |
|-------------|---------|-----|
| Vitest | 4.x | Test runner |
| @testing-library/react | 16.x | Render y queries |
| @testing-library/jest-dom | 6.x | Matchers DOM (`toBeInTheDocument`, etc.) |
| @testing-library/user-event | 14.x | Simulación de eventos reales |
| jsdom | 29.x | Entorno DOM virtual |

## Configuración

`vite.config.ts`:
```ts
test: {
  globals: true,
  environment: "jsdom",
  setupFiles: ["./src/test/setup.ts"],
  css: false,
}
```

`src/test/setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```

## Ejecutar

```bash
npm test          # una vez
npm run test:watch  # modo watch
```

## Estructura

```
src/
├── api/__tests__/         # 2 tests (auth, config)
│   ├── auth.test.ts       # login, register, fetchMe
│   └── config.test.ts     # apiFetch, auth headers, errores
├── components/__tests__/  # 3 tests
│   ├── AdminRoute.test.tsx
│   ├── ClientRoute.test.tsx
│   └── ProtectedRoute.test.tsx
├── pages/__tests__/       # 3 tests
│   ├── HomePage.test.tsx
│   ├── LoginPage.test.tsx
│   └── RegisterPage.test.tsx
├── context/__tests__/     # contexto auth
└── test/
    └── setup.ts
```

## Convenciones

1. **Mockear API calls** con `vi.mock("@/api/<modulo>")`
2. **Buscar elementos** por rol (`getByRole`) o test-id
3. **Simular eventos** con `userEvent` (no `fireEvent`)
4. **Limpiar** automático (jsdom + afterEach implícito)
5. **Probar**: happy path + error path + casos borde
6. **Archivos**: `<Nombre>.test.tsx` al lado del componente o en `__tests__/`

## Cobertura Actual

### ✅ Probado (40 tests, 8 archivos)

| Archivo | Tests | Cubre |
|---------|-------|-------|
| `api/__tests__/auth.test.ts` | 4 | login, register, fetchMe, errores |
| `api/__tests__/config.test.ts` | 4 | apiFetch, headers auth, errores HTTP |
| `components/__tests__/ProtectedRoute.test.tsx` | 2 | autenticado → outlet, no auth → redirect |
| `components/__tests__/AdminRoute.test.tsx` | 2 | superadmin → outlet, client → redirect |
| `components/__tests__/ClientRoute.test.tsx` | 2 | client → outlet, superadmin → redirect |
| `pages/__tests__/HomePage.test.tsx` | 2 | render básico |
| `pages/__tests__/LoginPage.test.tsx` | 2 | render, submit |
| `pages/__tests__/RegisterPage.test.tsx` | 2 | render, submit |

### ❌ No Probado (pendiente)

| Componente/Página | Prioridad |
|-------------------|-----------|
| `DashboardPage.tsx` | Alta |
| `ClientsPage.tsx` | Alta |
| `ClientDetailPage.tsx` | Alta |
| `ClientForm.tsx` | Alta |
| `AgentForm.tsx` | Alta |
| `AgentsPage.tsx` | Media |
| `ConversationsPage.tsx` | Media |
| `Sidebar.tsx` | Media |
| `Toast.tsx` | Baja |
| `Pagination.tsx` | Baja |

## Estrategia

1. **Unit tests** — componentes aislados con mocks de API y contexto
2. **Integration tests** — páginas completas con `AuthProvider` mockeado
3. **No E2E** por ahora (sin Cypress/Playwright configurado)
