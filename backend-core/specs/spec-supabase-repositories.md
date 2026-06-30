# Spec: Repositorios Supabase — Client & Agent

**SDD Phase:** Spec (Spec-Driven Development)
**Date:** 2026-06-07
**Status:** Approved
**Scope:** Infraestructura de persistencia (adaptadores secundarios)

---

## 1. Objetivo

Implementar los adaptadores Supabase para los puertos `ClientRepository` y `AgentRepository`.
El dominio ya define los contratos (ABC); esta especificación describe su implementación
concreta usando `supabase-py` contra una instancia real de Supabase, con soporte de
testing aislado vía mocking.

---

## 2. Requisitos funcionales

### RF-01: SupabaseClientRepository.save(client)
- Si el cliente NO existe en DB (no hay fila con ese `id`): ejecutar `INSERT`.
- Si el cliente YA existe: ejecutar `UPDATE` (UPSERT semántico).
- Mapear `Client` → `dict` con columnas: `id`, `name`, `business_type` (str), `whatsapp_number` (str), `is_active`, `created_at`, `updated_at`.
- `created_at` y `updated_at` se persisten como ISO 8601 UTC (`datetime.isoformat()`).
- `business_type` se persiste como string (`.value`).
- `whatsapp_number` se persiste como string (`.value`).
- Si Supabase lanza error de unicidad (`whatsapp_number` duplicado), lanzar `InvalidClientError`.
- Si cualquier otro error de DB, lanzar `DomainError` con mensaje descriptivo.

### RF-02: SupabaseClientRepository.find_by_id(client_id)
- Recibe `ClientId`.
- Ejecuta `SELECT * FROM clients WHERE id = :id LIMIT 1`.
- Si no hay resultado: retornar `None`.
- Si hay resultado: mapear `dict` → `Client` y retornar.
- Si `client_id` no es un UUID válido: lanzar `InvalidClientError`.

### RF-03: SupabaseClientRepository.find_by_whatsapp(number)
- Recibe `str` (número crudo, ej. `"573001234567"`).
- Ejecuta `SELECT * FROM clients WHERE whatsapp_number = :number LIMIT 1`.
- Si no hay resultado: retornar `None`.
- Si hay resultado: mapear `dict` → `Client` y retornar.
- Si el número tiene formato inválido: lanzar `InvalidClientError`.

### RF-04: SupabaseClientRepository.list_active(limit, offset)
- Ejecuta `SELECT * FROM clients WHERE is_active = true ORDER BY created_at DESC LIMIT :limit OFFSET :offset`.
- Valida `limit >= 1`, `offset >= 0`; si no: lanzar `InvalidClientError`.
- Retorna `list[Client]` (vacía si no hay resultados).

### RF-05: SupabaseAgentRepository.save(agent)
- Mismo patrón UPSERT que Client.
- `tools` (list[AgentTool]) se serializa como JSONB: `[{"name": "...", "description": "...", "endpoint": "..."}]`.
- `knowledge_base_refs` (list[str]) se persiste como `TEXT[]`.
- `client_id` se persiste como UUID string.
- Si `client_id` no existe en `clients`: supabase-py lanza error de FK → mapear a `InvalidAgentError`.
- Cualquier otro error de DB → `DomainError`.

### RF-06: SupabaseAgentRepository.find_by_id(agent_id)
- Recibe `AgentId`.
- `SELECT * FROM agents WHERE id = :id LIMIT 1`.
- Mapea JSONB `tools` → `list[AgentTool]`.
- Retorna `None` si no existe.

### RF-07: SupabaseAgentRepository.find_active_by_client(client_id)
- Recibe `ClientId`.
- `SELECT * FROM agents WHERE client_id = :cid AND is_active = true ORDER BY created_at ASC`.
- Retorna `list[Agent]` (vacía si no hay agentes activos).

### RF-08: SupabaseAgentRepository.delete(agent_id)
- Recibe `AgentId`.
- Ejecuta `DELETE FROM agents WHERE id = :id`.
- Si no se eliminó ninguna fila (affected rows = 0): lanzar `AgentNotFoundError`.
- Si error de DB: lanzar `DomainError`.

---

## 3. Requisitos no funcionales

### NFR-01: Async-first
Todos los métodos son `async def`. Se usa `AsyncClient` de `supabase` (o cliente sync envuelto en `asyncio.to_thread` si supabase-py no expone API async directa).

### NFR-02: Tipado estricto
- `mypy --strict` pasa sin errores en los archivos de repositorio.
- Sin `Any` ni `type: ignore` salvo para librerías externas sin stubs.

### NFR-03: Sin acoplamiento al ORM
- No se usa SQLAlchemy ni ORM.
- Queries raw vía supabase-py `table().select().eq().execute()`.
- El mapeo `dict ↔ Entity` es explícito en funciones privadas `_row_to_client()`, `_client_to_row()`.

### NFR-04: Tests aislan Supabase
- Tests de integración corren contra Supabase real (requieren `.env` con credenciales, marcados con `@pytest.mark.integration`).
- Alternativa: tests con mock de `supabase.Client` para CI sin dependencia externa.
- Cobertura > 90% en los repositorios.

### NFR-05: Configuración centralizada
- El `Supabase Client` se inyecta vía constructor (`__init__(self, client: supabase.Client)`) o se obtiene de un factory/provider.
- Las credenciales vienen de `get_settings()` (settings.py), nunca hardcodeadas.

### NFR-06: Manejo de timeouts
- Timeout de 10 segundos para queries a Supabase.
- Si timeout → `DomainError("Database timeout")`.

---

## 4. Edge cases

| # | Escenario | Comportamiento esperado |
|---|-----------|------------------------|
| EC-01 | `save()` con WhatsApp duplicado (ya existe otro cliente con ese número) | `InvalidClientError("WhatsApp number already registered")` |
| EC-02 | `find_by_id()` con UUID malformado | `InvalidClientError` / `InvalidAgentError` |
| EC-03 | `find_by_id()` con UUID válido pero inexistente | `None` |
| EC-04 | `list_active()` con `limit=0` o negativo | `InvalidClientError` |
| EC-05 | `list_active()` sin clientes activos | `[]` (lista vacía) |
| EC-06 | `save()` de Agent con `client_id` que no existe en DB | `InvalidAgentError` (FK violation) |
| EC-07 | `delete()` de Agent que no existe | `AgentNotFoundError` |
| EC-08 | `delete()` de Agent exitoso → `find_by_id()` retorna `None` | Consistencia post-delete |
| EC-09 | `tools` vacío (`[]`) se persiste y recupera como `[]` | Sin errores de serialización |
| EC-10 | `knowledge_base_refs` con strings que contienen comillas o caracteres especiales | PostgreSQL TEXT[] maneja correctamente |
| EC-11 | Supabase desconectado o caído | `DomainError("Database connection failed")` |
| EC-12 | `save()` con `is_active=False` | Se persiste correctamente, `find_by_id()` retorna entidad con `is_active=False` |
| EC-13 | Agent `personality` con emojis y caracteres Unicode | Se persiste y recupera sin corrupción |
| EC-14 | Concurrencia: dos `save()` simultáneos sobre el mismo cliente | Último write gana (no hay optimistic locking en v1) |
| EC-15 | `upsert` sin `created_at` en update | Usar `ON CONFLICT (id) DO UPDATE` preservando `created_at` original |

---

## 5. Criterios de aceptación

### CA-01: SupabaseClientRepository pasa todos los tests de integración
- `test_save_new_client` → INSERT exitoso
- `test_save_existing_client` → UPDATE exitoso (mismo id, datos nuevos)
- `test_find_by_id_returns_client` → entidad mapeada correctamente
- `test_find_by_id_returns_none_for_missing` → `None`
- `test_find_by_whatsapp_found` → entidad
- `test_find_by_whatsapp_not_found` → `None`
- `test_find_by_whatsapp_invalid_number` → `InvalidClientError`
- `test_list_active_returns_only_active` → filtra `is_active=false`
- `test_list_active_pagination` → offset/limit funciona
- `test_list_active_empty` → `[]`
- `test_save_duplicate_whatsapp` → `InvalidClientError`

### CA-02: SupabaseAgentRepository pasa todos los tests de integración
- `test_save_new_agent` → INSERT con tools JSONB
- `test_save_existing_agent` → UPDATE
- `test_find_by_id_returns_agent_with_tools` → deserialización correcta
- `test_find_by_id_none` → `None`
- `test_find_active_by_client` → filtra `is_active=false`
- `test_find_active_by_client_no_agents` → `[]`
- `test_delete_existing_agent` → `DELETE` exitoso
- `test_delete_nonexistent_agent` → `AgentNotFoundError`
- `test_save_agent_with_invalid_client_id` → `InvalidAgentError`

### CA-03: Mapeo de errores
- Errores de FK → `InvalidAgentError` / `InvalidClientError`
- Errores de unicidad → `InvalidClientError`
- Errores de conexión → `DomainError`
- Errores de timeout → `DomainError`

### CA-04: Linting y tipos
- `ruff check` sin errores en archivos de repositorio
- `mypy` sin errores en archivos de repositorio

---

## 6. Estructura de archivos propuesta

```
backend-core/
├── app/
│   └── infrastructure/
│       └── persistence/
│           ├── __init__.py                    (ya existe)
│           ├── client_repository.py           ← NUEVO: SupabaseClientRepository
│           └── agent_repository.py            ← NUEVO: SupabaseAgentRepository
└── tests/
    └── integration/
        ├── __init__.py                        (ya existe, vacío)
        ├── conftest.py                        ← NUEVO: fixtures Supabase
        ├── test_client_repository.py          ← NUEVO: 11 tests integración
        └── test_agent_repository.py           ← NUEVO: 9 tests integración
```

### `conftest.py` (fixtures compartidas)
- `supabase_client` — instancia real de `supabase.Client` (lee `.env`)
- `clean_db` — fixture autouse que limpia `agents` y `clients` antes/después de cada test
- `sample_client` — `Client` preconstruido con datos válidos
- `sample_agent` — `Agent` preconstruido con tools

### `test_client_repository.py` (11 tests)
### `test_agent_repository.py` (9 tests)

---

## 7. Dependencias

| Dependencia | Versión | Uso |
|-------------|---------|-----|
| `supabase` | `>=2.15.0` | Cliente Supabase (ya en requirements.txt) |
| `pytest` | `>=8.3.4` | Test runner (ya en requirements.txt) |
| `pytest-asyncio` | `>=0.24.0` | Soporte async tests (ya en requirements.txt) |
| `pytest-mock` | `>=3.14.0` | Mocking para tests aislados (ya en requirements.txt) |
| `python-dotenv` | `>=1.0.1` | Carga `.env` en tests (ya en requirements.txt) |

**Nuevas dependencias (no requeridas):** Ninguna. Todo se implementa con lo ya instalado.

---

## 8. Diagrama de flujo (TDD)

El ciclo TDD para cada repositorio sigue este orden:

1. **Red**: Escribir el test de integración mínimo que falle.
2. **Green**: Implementar el método mínimo para que pase.
3. **Refactor**: Extraer helpers de mapeo, mejorar manejo de errores.

### Orden de implementación (KISS)

```
1. SupabaseClientRepository.save()     → test_save_new_client
2. SupabaseClientRepository.find_by_id() → test_find_by_id_returns_client
3. SupabaseClientRepository.find_by_whatsapp() → test_find_by_whatsapp_found
4. SupabaseClientRepository.list_active() → test_list_active_returns_only_active
5. SupabaseAgentRepository.save()      → test_save_new_agent
6. SupabaseAgentRepository.find_by_id() → test_find_by_id_returns_agent_with_tools
7. SupabaseAgentRepository.find_active_by_client() → test_find_active_by_client
8. SupabaseAgentRepository.delete()    → test_delete_existing_agent
```

### Diagrama de secuencia (save)

```
Test/UseCase  →  SupabaseClientRepository.save(client)
                     │
                     ▼
              _client_to_row(client) → dict
                     │
                     ▼
         supabase.table("clients").upsert(row).execute()
                     │
                     ▼
              ¿error_postgrest?
                ├─ uniqueness → InvalidClientError
                ├─ fk         → InvalidClientError
                ├─ connection → DomainError
                └─ ok         → None
```

### Diagrama de secuencia (find_by_id)

```
Test/UseCase  →  SupabaseClientRepository.find_by_id(client_id)
                     │
                     ▼
         supabase.table("clients").select("*").eq("id", str(cid)).execute()
                     │
                     ▼
              ¿data?
                ├─ vacío → None
                └─ datos → _row_to_client(row) → Client
```

---

## 9. Mapping functions (contrato interno)

### `_client_to_row(client: Client) -> dict`
```python
{
    "id": str(client.id),
    "name": client.name,
    "business_type": str(client.business_type),
    "whatsapp_number": str(client.whatsapp_number),
    "is_active": client.is_active,
    "created_at": client.created_at.isoformat(),
    "updated_at": client.updated_at.isoformat(),
}
```

### `_row_to_client(row: dict) -> Client`
```python
Client(
    id=UUID(row["id"]),
    name=row["name"],
    business_type=BusinessType(row["business_type"]),
    whatsapp_number=WhatsAppNumber(row["whatsapp_number"]),
    is_active=row["is_active"],
)
# Timestamps se asignan desde row["created_at"], row["updated_at"]
```

### `_agent_to_row(agent: Agent) -> dict`
```python
{
    "id": str(agent.id),
    "client_id": str(agent.client_id),
    "name": agent.name,
    "personality": agent.personality,
    "tools": [{"name": t.name, "description": t.description, "endpoint": t.endpoint} for t in agent.tools],
    "knowledge_base_refs": agent.knowledge_base_refs,
    "is_active": agent.is_active,
    "created_at": agent.created_at.isoformat(),
    "updated_at": agent.updated_at.isoformat(),
}
```

### `_row_to_agent(row: dict) -> Agent`
```python
Agent(
    id=UUID(row["id"]),
    client_id=ClientId(UUID(row["client_id"])),
    name=row["name"],
    personality=row["personality"],
    tools=[AgentTool(**t) for t in row["tools"]],  # JSONB → list[dict] → list[AgentTool]
    knowledge_base_refs=row.get("knowledge_base_refs", []),
    is_active=row["is_active"],
)
```

---

## 10. Notas

- **Sin optimistic locking en v1**: El UPSERT no verifica `updated_at` previo. Dos saves concurrentes pueden causar lost update. Se documenta como limitación conocida.
- **RLS ya configurada**: La política `Service role full access` permite al backend operar sin restricciones (usando `service_role key`).
- **Triggers `updated_at`**: La DB ya actualiza `updated_at` automáticamente. El repositorio aún envía el valor de la entidad; la DB lo sobrescribe con `now()`.
- **pgvector no se usa aún**: La extensión `vector` está instalada pero `ClientRepository` y `AgentRepository` no la usan. Se usará en `KnowledgeBaseRepository` (futuro).
