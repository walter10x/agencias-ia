# Test Plan: Landing Pages + Formularios de Captacion

**Module:** `backend-core/app/` — Landing Pages
**Phase:** RED (TDD) — Tests written before implementation exists
**Spec:** `specs/spec-landing-pages.md`
**Test file:** `tests/unit/test_landing.py`

---

## Critical (test first)

- [ ] [TC-001] Given slug="mi-negocio", when LandingSlug() is created, then value="mi-negocio" and str() returns same
- [ ] [TC-002] Given slug="", when LandingSlug() is constructed, then ValueError("cannot be empty")
- [ ] [TC-003] Given Lead(phone=..., source="landing"), when constructed, then source="landing" without error
- [ ] [TC-004] Given "landing" not in Lead.VALID_SOURCES, when importing Lead, then test fails (RED — spec requires adding "landing")
- [ ] [TC-005] Given valid SubmitLandingInput, when SubmitLandingLeadUseCase.execute(), then lead created with source="landing", lead_repo.save called once
- [ ] [TC-006] Given slug="no-existe", when SubmitLandingLeadUseCase.execute(), then LandingNotFoundError raised, save not called
- [ ] [TC-007] Given landing_active=False, when SubmitLandingLeadUseCase.execute(), then LandingInactiveError raised, save not called
- [ ] [TC-008] Given client.is_active=False, when SubmitLandingLeadUseCase.execute(), then LandingInactiveError raised, save not called
- [ ] [TC-009] Given whatsapp="12345", when SubmitLandingLeadUseCase.execute(), then InvalidLeadError raised (min 10 digits)

## Happy Path

### LandingSlug — Value Object

- [ ] [TC-010] LandingSlug accepts slug with numbers ("negocio-24-horas")
- [ ] [TC-011] LandingSlug strips and lowercases input ("  Mi-Negocio  " → "mi-negocio")
- [ ] [TC-012] LandingSlug accepts single-character slug ("a")
- [ ] [TC-013] LandingSlug accepts slug at exactly 100 characters
- [ ] [TC-014] LandingSlug.from_name("Peluqueria El Buen Corte") → "peluqueria-el-buen-corte"
- [ ] [TC-015] LandingSlug.from_name("Cafe & Bar") → "cafe-bar"
- [ ] [TC-016] LandingSlug.from_name("@#$%") → "cliente" (fallback)
- [ ] [TC-017] LandingSlug is frozen dataclass (cannot mutate after creation)

### slugify() — Pure Function

- [ ] [TC-018] slugify("Mi Negocio") → "mi-negocio"
- [ ] [TC-019] slugify("Peluuqeria") removes accents → "peluqueria"
- [ ] [TC-020] slugify("Dr. Juan's Clinica") → "dr-juans-clinica"
- [ ] [TC-021] slugify("Cafe & Bar") → "cafe-bar"
- [ ] [TC-022] slugify("Mi   Negocio") collapses multiple spaces → "mi-negocio"
- [ ] [TC-023] slugify("  -Mi Negocio-  ") strips leading/trailing hyphens
- [ ] [TC-024] slugify("") → "cliente" (fallback)
- [ ] [TC-025] slugify("   ") → "cliente"
- [ ] [TC-026] slugify("@#$%") → "cliente"
- [ ] [TC-027] slugify("Negocio 24 Horas") preserves numbers → "negocio-24-horas"
- [ ] [TC-028] slugify("mi-negocio") is idempotent → "mi-negocio"

### generate_unique_slug() — Dedup Helper

- [ ] [TC-029] Unique base slug → returns as-is
- [ ] [TC-030] Conflicting base slug → appends "-2" ("mi-negocio" → "mi-negocio-2")
- [ ] [TC-031] Multiple conflicts → increments ("mi-negocio-4" when 1-3 exist)
- [ ] [TC-032] Empty existing set → returns base slug unchanged
- [ ] [TC-033] Numbers in slug don't conflict with suffix numbering

### Lead Entity — source="landing"

- [ ] [TC-034] All existing sources still valid (whatsapp, webchat, telegram, manual, import)
- [ ] [TC-035] Invalid source "email" still raises ValueError (regression)

### LandingConfig — Dataclass

- [ ] [TC-036] LandingConfig created with all fields populated
- [ ] [TC-037] Default values match spec (title="Impulsa tu negocio con IA", color="#f59e0b")

### SubmitLandingLeadUseCase — Happy Path

- [ ] [TC-038] Valid submission: lead created with correct phone, name, source
- [ ] [TC-039] Output contains lead_id, message="¡Gracias! Te contactaremos pronto.", auto_reply with name
- [ ] [TC-040] {{name}} interpolated in auto_reply ("¡Hola Carlos! ...")
- [ ] [TC-041] Agent active → WhatsApp message sent with phone + interpolated auto_reply
- [ ] [TC-042] WhatsApp "+57 300-123-4567" cleaned to "573001234567"
- [ ] [TC-043] Empty interest field → valid, lead created successfully
- [ ] [TC-044] No agent active → lead created, WhatsApp NOT sent (graceful degradation)

### GetLandingConfigUseCase

- [ ] [TC-045] Returns LandingConfigOutput with all config fields + leads_count
- [ ] [TC-046] leads_count=0 when no landing leads exist
- [ ] [TC-047] get_landing_config and count_leads_by_landing called with correct client_id

### UpdateLandingConfigUseCase — Happy Path

- [ ] [TC-048] Update landing_title → returned config has new title
- [ ] [TC-049] Update multiple fields simultaneously (title, description, color, auto_reply)
- [ ] [TC-050] Activate landing without slug → auto-generates slug from client name
- [ ] [TC-051] Unique slug → used as provided without suffix
- [ ] [TC-052] Update primary_color → config reflects new color
- [ ] [TC-053] Update auto_reply → config reflects new template
- [ ] [TC-054] Deactivate landing → landing_active=False

### Landing DTOs

- [ ] [TC-055] SubmitLandingInput is frozen (immutable)
- [ ] [TC-056] UpdateLandingConfigInput with 1 field → valid
- [ ] [TC-057] LandingConfigOutput is frozen
- [ ] [TC-058] LandingPublicConfigOutput has no landing_slug or landing_auto_reply (public-safe)

## Edge Cases & Errors

### LandingSlug — Validation

- [ ] [TC-059] Whitespace-only ("   ") → ValueError
- [ ] [TC-060] Uppercase ("Mi-Negocio") → ValueError
- [ ] [TC-061] Internal spaces ("mi negocio") → ValueError
- [ ] [TC-062] Special characters ("mi@negocio") → ValueError
- [ ] [TC-063] Consecutive hyphens ("mi--negocio") → ValueError
- [ ] [TC-064] Leading hyphen ("-mi-negocio") → ValueError
- [ ] [TC-065] Trailing hyphen ("mi-negocio-") → ValueError
- [ ] [TC-066] Exceeds 100 characters → ValueError

### SubmitLandingLeadUseCase — Errors

- [ ] [TC-067] Slug not found → LandingNotFoundError (404)
- [ ] [TC-068] Landing inactive (landing_active=False) → LandingInactiveError (404)
- [ ] [TC-069] Client inactive (is_active=False) → LandingInactiveError (404)
- [ ] [TC-070] WhatsApp < 10 digits → InvalidLeadError
- [ ] [TC-071] WhatsApp only non-digits ("abc-+def") → InvalidLeadError
- [ ] [TC-072] Empty name → InvalidLeadError
- [ ] [TC-073] Whitespace-only name → InvalidLeadError
- [ ] [TC-074] Rate limit exceeded (5/min per IP) → LandingRateLimitError (429)
- [ ] [TC-075] Rate limit check receives correct client_ip parameter
- [ ] [TC-076] WhatsApp send failure → lead still created, no exception propagated (graceful degradation)

### GetLandingConfigUseCase — Errors

- [ ] [TC-077] Client not found → ClientNotFoundError

### UpdateLandingConfigUseCase — Errors

- [ ] [TC-078] All fields None → ValueError("at least one field") in DTO
- [ ] [TC-079] Duplicate slug → auto-generates numerical suffix (e.g., -2, -3)
- [ ] [TC-080] Slug uniqueness check excludes current client (can reuse own slug)

### Landing Domain Errors

- [ ] [TC-081] LandingNotFoundError extends DomainError
- [ ] [TC-082] LandingInactiveError extends DomainError
- [ ] [TC-083] LandingRateLimitError extends DomainError
- [ ] [TC-084] All errors store and display message correctly

### LandingRepository Interface

- [ ] [TC-085] All 8 abstract methods declared (find_client_by_slug, get_landing_config, update_landing_config, slug_exists, count_leads_by_landing, check_rate_limit, get_all_slugs, get_client)
- [ ] [TC-086] Cannot instantiate LandingRepository (abstract class)

---

## Non-Existent Imports (RED phase — will fail until implementation)

These modules/files do **not** exist yet. The test file `tests/unit/test_landing.py` imports them to define expected behavior:

```
app.domain.shared.value_objects.LandingSlug         → NEW (add to existing file)
app.domain.shared.slugify                           → NEW module
app.domain.landing.repository                        → NEW module
app.domain.shared.errors.LandingNotFoundError       → NEW (add to existing file)
app.domain.shared.errors.LandingInactiveError       → NEW (add to existing file)
app.domain.shared.errors.LandingRateLimitError      → NEW (add to existing file)
app.application.dtos.SubmitLandingInput              → NEW (add to existing file)
app.application.dtos.SubmitLandingOutput             → NEW
app.application.dtos.GetLandingConfigInput           → NEW
app.application.dtos.UpdateLandingConfigInput        → NEW
app.application.dtos.LandingConfigOutput             → NEW
app.application.dtos.LandingPublicConfigOutput       → NEW
app.application.landing.submit_lead                  → NEW module
app.application.landing.get_landing_config           → NEW module
app.application.landing.update_landing_config        → NEW module
app.domain.landing.repository.LandingConfig          → NEW dataclass
app.domain.landing.repository.LandingRepository      → NEW ABC
```

## Modified Files (already exist, need changes)

```
app.domain.lead.entity.Lead.VALID_SOURCES           → + "landing"
```

---

## Test File Summary

| File | Classes | Tests | Coverage |
|------|---------|-------|----------|
| `tests/unit/test_landing.py` | 12 classes | ~86 tests | LandingSlug, slugify, generate_unique_slug, Lead source="landing", domain errors, LandingConfig, SubmitLandingLeadUseCase (happy + errors), GetLandingConfigUseCase, UpdateLandingConfigUseCase, DTOs, LandingRepository interface |

## Implementation Order (from spec section 15)

```
FASE 1: Domain
  1. app/domain/lead/entity.py              — + "landing" to VALID_SOURCES
  2. app/domain/shared/slugify.py            — slugify + generate_unique_slug
  3. app/domain/shared/value_objects.py     — + LandingSlug
  4. app/domain/shared/errors.py            — + 3 landing errors
  5. app/domain/landing/__init__.py
  6. app/domain/landing/repository.py       — LandingRepository ABC + LandingConfig

FASE 2: Application DTOs
  7. app/application/dtos.py               — + 6 landing DTOs

FASE 3: Application Use Cases
  8. app/application/landing/__init__.py
  9. app/application/landing/submit_lead.py
  10. app/application/landing/get_landing_config.py
  11. app/application/landing/update_landing_config.py

FASE 4: Infrastructure
  12. app/infrastructure/persistence/landing_repository.py
  13. app/infrastructure/http/schemas.py          — + 5 landing schemas
  14. app/infrastructure/http/dependencies.py     — + get_landing_repo
  15. app/infrastructure/http/error_handlers.py   — + 3 handlers
  16. app/infrastructure/http/landing_router.py
  17. app/main.py                                  — register routers
```
