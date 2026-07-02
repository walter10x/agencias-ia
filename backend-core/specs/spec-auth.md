# Spec: Auth Multi-Tenant (Fase 1)

**Status**: Implementación completa — pasos 1–13 terminados
**Última actualización**: 2026-07-01
**Versión**: 1.3
**Sigue el patrón de**: `specs/spec-use-cases.md`, `specs/spec-whatsapp-meta.md`

---

## 1. Objetivo

Habilitar autenticación multi-tenant en agencias-ia: registro público de clientes, aprobación manual por el superadmin (Walter), login JWT con `client_id` en claims, y filtro por tenant en todos los routers existentes.

## 2. Decisiones cerradas

- JWT HS256 vía `python-jose`; bcrypt vía `passlib`.
- Roles: `superadmin` / `client_admin` / `client_user` (previsto).
- Status: `pending` → `approved` → `active`; además `inactive` para rechazados/suspendidos.
- Registro público: 4 campos (email, password, business_name, whatsapp_number).
- Aprobación manual para TODOS por Walter.
- Sin email transaccional en Fase 1.
- Meta Cloud API + WABA central (ya cubierto por `spec-whatsapp-meta.md`).
- Solo superadmin aprueba/rechaza/desconecta WhatsApp.

## 3. Migración 002

Archivo: `backend-core/migrations/002_auth_multi_tenant.sql`

```sql
ALTER TABLE clients
    ADD COLUMN email             TEXT NOT NULL DEFAULT '',
    ADD COLUMN password_hash     TEXT NOT NULL DEFAULT '',
    ADD COLUMN role              TEXT NOT NULL DEFAULT 'client_admin'
        CHECK (role IN ('superadmin', 'client_admin', 'client_user')),
    ADD COLUMN status            TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'active', 'inactive')),
    ADD COLUMN phone_number_id   TEXT NOT NULL DEFAULT '',
    ADD COLUMN whatsapp_connected BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN plan              TEXT NOT NULL DEFAULT 'free'
        CHECK (plan IN ('free', 'starter', 'pro', 'enterprise'));

CREATE UNIQUE INDEX idx_clients_email_unique
    ON clients (email) WHERE email <> '';

CREATE INDEX idx_clients_status ON clients(status);
CREATE INDEX idx_clients_role   ON clients(role);
```

**Pre-migración**: si hay filas existentes sin email, ejecutar antes del `UNIQUE INDEX`:
`UPDATE clients SET email = 'pre_' || id::text || '@migrate.local' WHERE email = '';`

## 4. Value Objects nuevos (`app/domain/shared/value_objects.py`)

- `Email(value: str)` — frozen dataclass; regex `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`; normaliza a lower.
- `PasswordHash(value: str)` — frozen; debe comenzar con `$2a$|b$|y$` y len 60. No contiene plain password.

Reutiliza: `ClientId`, `WhatsAppNumber`, `BusinessType` ya existentes.

## 5. Enums (`app/domain/client/enums.py` — nuevo)

```python
class ClientRole(str, Enum):
    SUPERADMIN = "superadmin"
    CLIENT_ADMIN = "client_admin"
    CLIENT_USER = "client_user"

class ClientStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    INACTIVE = "inactive"
```

## 6. Entidad `Client` (extender `app/domain/client/entity.py`)

Campos nuevos: `email: Email`, `password_hash: PasswordHash`, `role: ClientRole`, `status: ClientStatus`, `phone_number_id: str = ""`, `whatsapp_connected: bool = False`, `plan: str = "free"`.

Métodos de dominio (todos hacen `self.touch()`):
- `approve()` — desde `PENDING` → `APPROVED`; lanza `InvalidClientError` si ya está.
- `reject()` — `PENDING` → `INACTIVE`; lanza `InvalidClientError` si no está `PENDING`.
- `connect_whatsapp(phone_number_id)` — solo si `status in (APPROVED, ACTIVE)`.
- `disconnect_whatsapp()` — solo si `APPROVED|ACTIVE`; limpia `phone_number_id=""`.
- `can_login() -> bool` — `status in (APPROVED, ACTIVE)`.

## 7. Ports (`app/application/ports/`)

```python
class PasswordHasherPort(Protocol):
    def hash_password(self, plain: str) -> PasswordHash: ...
    def verify(self, plain: str, hashed: PasswordHash) -> bool: ...

class JwtPort(Protocol):
    def sign(self, sub: str, role: str, client_id: str | None) -> str: ...
    def decode(self, token: str) -> dict[str, str]: ...
```

Extender `ClientRepository` con:
- `async def find_by_email(email: Email) -> Optional[Client]`
- `async def list_pending(limit, offset) -> list[Client]`
- `async def update(client: Client) -> None` (alias semántico de `save`)

## 8. Excepciones (`app/domain/shared/errors.py`)

```python
class AuthError(DomainError): ...
class InvalidCredentialsError(AuthError): ...
class EmailAlreadyRegisteredError(AuthError): ...
class ClientNotApprovedError(AuthError): ...
class WeakPasswordError(DomainError): ...
class UnauthorizedError(AuthError): ...
class ForbiddenError(AuthError): ...
```

## 9. Casos de uso (`app/application/auth/`)

- `RegisterClientUseCase(repo, hasher).execute(RegisterClientInput) -> RegisterClientOutput` — valida email, pass len≥8 (si no `WeakPasswordError`), WhatsApp; pre-check `find_by_email`; persiste con `status=PENDING`.
- `LoginClientUseCase(repo, hasher, jwt).execute(LoginClientInput) -> LoginClientOutput` — busca por email (404 → `InvalidCredentialsError` sin filtrar existencia); `verify` False → `InvalidCredentialsError`; `status=PENDING` → `ClientNotApprovedError`; firma JWT.
- `GetCurrentClientUseCase(repo).execute(client_id) -> CurrentClientOutput`.

## 10. Adaptadores (`app/infrastructure/security/`)

- `BcryptPasswordHasher` — `CryptContext(schemes=["bcrypt"], deprecated="auto")`; `verify` retorna bool.
- `JoseJwtHandler(settings)` — HS256; `exp = now + timedelta(minutes=settings.jwt_expire_minutes)`; `JWTError` se reenvuelve como `UnauthorizedError`.

## 11. Endpoints HTTP

- `POST /api/v1/auth/register` → `RegisterResponse` (201; 409 dup email; 400 pass débil; 422 escema)
- `POST /api/v1/auth/login` → `LoginResponse` (200; 401 creds malas; 403 pending)
- `GET  /api/v1/auth/me` → `MeResponse` (200; 401 sin token)

Admin (solo `require_superadmin`):
- `POST /api/v1/clients/{id}/approve` → `ClientResponse` (200; 403 si no superadmin)
- `POST /api/v1/clients/{id}/reject` → `ClientResponse` (200; 403)
- `POST /api/v1/clients/{id}/disconnect-whatsapp` → `ClientResponse` (200; 403)

## 12. Dependencies (`app/infrastructure/http/dependencies.py`)

- `get_password_hasher()` → `BcryptPasswordHasher()` (cached)
- `get_jwt_handler()` → `JoseJwtHandler(get_settings())` (cached)
- `get_current_client(authorization, jwt_handler, client_repo)` → valida Bearer, decodifica JWT, busca `Client`, comprueba `can_login()`; lanza `UnauthorizedError`/`ForbiddenError` (mapeados a 401/403 por `auth_error_handler`).
- `require_superadmin(current)` — 403 si `role != superadmin`.

## 13. Filtro tenant en routers existentes

A cada endpoint tenant-scoped de `lead_router`, `conversation_router`, `agent_router`, `email_router`, `feedback_router` añadir `current_client: CurrentClientOutput = Depends(get_current_client)` y forzar `client_id = current_client.client_id` en el DTO (ignorando cualquier `client_id` del body/query). En `agent_router` además validar que `agent.client_id == current_client.client_id` para `GET/PATCH/DELETE/{id}`.

`landing_public_router` NO lleva auth. `client_router` GET/PATCH por `{id}` requiere auth y mismo `client_id` o superadmin.

## 14. Tests TDD (paso actual: 31 tests implementados de ~38 previstos)

| Archivo | Tests | Estado |
|---|---|---|
| `tests/unit/test_password_hasher.py` | hash_and_verify_roundtrip · hash_does_not_leak_plain | ✅ 4 tests |
| `tests/unit/test_jwt_handler.py` | sign_and_decode_roundtrip · decode_expired_token_raises · decode_invalid_token_raises · extra tests | ✅ 5 tests |
| `tests/unit/test_value_objects.py` (extender) | email_invalid_format · password_hash_invalid | ✅ 10 tests |
| `tests/unit/test_register_client_use_case.py` | returns_pending_status · duplicate_email_raises_409 · weak_password_raises_400 | ✅ |
| `tests/unit/test_login_client_use_case.py` | success_returns_jwt · pending_raises_forbidden · wrong_password_raises_401 | ✅ |
| `tests/unit/test_get_current_client_use_case.py` | success_returns_client · not_found_raises_401 | ✅ |
| `tests/unit/test_auth_router.py` | register(201/409/422/400) · login(200/401/403/422) · me(200/401) | ✅ 10 tests |
| `tests/unit/test_admin_use_cases.py` | approve(3) · reject(2) · disconnect-whatsapp(4) | ✅ 9 tests |
| `tests/unit/test_admin_router.py` | approve(200/403) · reject(200) · disconnect-whatsapp(200) | ✅ 4 tests |
| `tests/unit/test_tenant_isolation.py` (nuevo) | 11 tests: lead_create/lead_list override · conversation_list filtro · email_send/email_list override · feedback_create/list override · agent_get/update/deactivate/delete cross-tenant 403 | ✅ |

## 15. Orden de implementación

1. ✅ Migración 002.
2. ✅ VOs `Email`, `PasswordHash` (+ 10 tests).
3. ✅ Enums `ClientRole`, `ClientStatus` (+ tests).
4. ✅ Entidad `Client` extendida (+ 12 tests en `test_client.py`).
5. ✅ `BcryptPasswordHasher` (+ 4 tests).
6. ✅ `JoseJwtHandler` (+ 5 tests).
7. ✅ Ports + DTOs + excepciones.
8. ✅ Casos de uso auth (+ 12 tests, RED→GREEN).
9. ✅ `auth_router.py` (+ 10 tests) + `auth_error_handler`.
10. ✅ `dependencies.py` completo + `main.py` mount.
11. ✅ `client_router` admin endpoints (+ 3 use cases + 13 tests: 9 + 4 router).
12. ✅ Filtro tenant en routers de lead/conversation/agent/email/feedback + validación cross-tenant en agent use cases (ForbiddenError 403).
13. ✅ `scripts/seed_superadmin.py` idempotente (`SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD` env vars).

**Ciclo TDD por cada paso con "+ tests":** RED → GREEN → REFACTOR.

## 16. Riesgos

- Bcrypt síncrono bloquea event loop: envolver en `asyncio.to_thread` dentro del hasher.
- Rotación `jwt_secret` invalida todos los tokens sin blacklist; aceptable Fase 1.
- `reject` marca `status=inactive` + `is_active=False`; el email queda bloqueado para re-registro (traza).
- Detección unique-violation email vs whatsapp: pre-check `find_by_email` antes de `save`.
- `client_user` (empleado) solo previsto — sin endpoints en Fase 1.

## 17. Open questions

- ¿Superadmin tiene fila en `clients` o tabla `users` separada? → Fase 1: fila en `clients` con `role=superadmin, status=active, business_type=otro, whatsapp_number="0000000000"`. Reconsiderar antes de Fase 3 si加入 real `client_user`.
- ¿Activar Supabase RLS como defensa en profundidad? → diferido a Fase 2.
- Email del superadmin inicial: pendiente de Walter (lo pide `seed_superadmin.py`).