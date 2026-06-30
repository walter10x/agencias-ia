---
name: code-review
description: >
  Revisor de código experto. Analiza cada PR o cambio antes de mergear.
  Verifica SOLID, Clean Code, tests, cobertura, performance, naming,
  y delega hallazgos de seguridad al agente cybersecurity.
  Aplicar SIEMPRE antes de cerrar un feature o hacer commit final.
  Triggers: "revisar código", "code review", "PR review", "revisión",
  "review", "auditar código", "antes de merge", "pre-commit".
risk: safe
source: "Agencia IA — Custom Skill"
date_added: "2026-06-07"
---

# Code Review — Always-On Gatekeeper Skill

Este skill define el checklist de revisión de código que se aplica
en CADA feature completada antes de mergear. Es la última línea de defensa
de calidad.

## 🔍 Regla de Oro

**Si no pasa los tests, no se revisa. Si no es legible para un junior, no se mergea.**

---

## 1. Architecture & Design (SOLID)

### S — Single Responsibility
- [ ] Cada clase/módulo tiene UNA sola razón para cambiar
- [ ] Funciones ≤ 20 líneas (ideal ≤ 10)
- [ ] No hay "god classes" ni "utility folders" sin cohesión

### O — Open/Closed
- [ ] Nuevas funcionalidades se añaden extendiendo, no modificando
- [ ] Uso de interfaces/ABC en lugar de if/else gigantes por tipo

### L — Liskov Substitution
- [ ] Las subclases no rompen contratos de la clase base
- [ ] No hay `isinstance` checks que traicionen el polimorfismo

### I — Interface Segregation
- [ ] Las interfaces son pequeñas y específicas (no "fat interfaces")
- [ ] Los clientes no dependen de métodos que no usan

### D — Dependency Inversion
- [ ] Módulos de alto nivel no dependen de detalles de bajo nivel
- [ ] Domain no importa nada de infrastructure ✅

---

## 2. Clean Code Principles

### Naming
- [ ] Nombres revelan intención (`processMessage` no `procMsg`)
- [ ] Sin abreviaturas crípticas (`usr`, `ctx`, `repo` sólo si es estándar del proyecto)
- [ ] Variables booleanas con prefijo `is_`, `has_`, `should_`
- [ ] Constantes en UPPER_SNAKE_CASE

### Functions
- [ ] Una función = una cosa
- [ ] ≤ 3 argumentos (más = considerar objeto de configuración)
- [ ] Sin efectos secundarios ocultos
- [ ] Early returns en lugar de nesting profundo

### Comments
- [ ] Cero comentarios redundantes (`# incrementa i` sobre `i += 1`)
- [ ] Cero código comentado (eso es lo que git es para)
- [ ] Si hay un TODO, tiene issue number (`# TODO(PROJ-123): ...`)

---

## 3. Test Coverage & Quality

- [ ] Todos los tests pasan (30/30 ✅)
- [ ] Nuevos tests para nueva funcionalidad (TDD: Red → Green → Refactor)
- [ ] Tests unitarios cubren:
  - Happy path
  - Edge cases (valores límite, nulos, vacíos)
  - Error paths (excepciones, timeouts)
- [ ] Nombres de tests descriptivos: `test_raises_on_empty_name` no `test_error_1`
- [ ] Sin dependencias externas en tests unitarios (mocks para DB, API, etc.)

### Coverage targets:
| Capa | Objetivo |
|------|----------|
| Domain entities | 100% |
| Value objects | 100% |
| Use cases | 90%+ |
| Repositories | 80%+ (con test de integración) |
| API endpoints | 85%+ |

---

## 4. Error Handling

- [ ] Excepciones específicas, no genéricas (`except Exception:` ❌)
- [ ] Mensajes de error útiles para debugging
- [ ] Errores de dominio separados de errores de infraestructura
- [ ] Sin `pass` en bloques `except`
- [ ] Operaciones async tienen timeout
- [ ] Circuit breaker para llamadas externas (LLM, WhatsApp, DB)

---

## 5. Performance

- [ ] Operaciones I/O son async (FastAPI: `async def`)
- [ ] No hay N+1 queries
- [ ] Consultas DB usan índices existentes
- [ ] Respuestas grandes usan paginación
- [ ] LLM calls usan streaming cuando es posible
- [ ] Caché donde aplique (Redis para config, respuestas frecuentes)

---

## 6. Code Smells — Radar

| Smell | Detección |
|-------|-----------|
| 🔴 Código duplicado | Misma lógica en 2+ lugares |
| 🔴 Números mágicos | `if status == 3` → `if status == Status.ACTIVE` |
| 🟠 Método largo | > 30 líneas |
| 🟠 Clase grande | > 200 líneas (sin contar tests) |
| 🟡 Feature envy | Método que usa más datos de otra clase que de la propia |
| 🟡 Switch statements | `if type == "a" elif type == "b"` → usar polimorfismo |
| 🟢 Long parameter list | > 4 parámetros |

---

## 7. Dependencies & Imports

- [ ] Imports organizados: stdlib → third-party → proyecto
- [ ] Sin imports circulares
- [ ] Sin imports no usados
- [ ] Dependencias en `requirements.txt` o `package.json` con versión exacta (`==` no `>=`)
- [ ] Sin dependencias deprecated/abandonadas

---

## 8. Configuration & Environment

- [ ] Configuración centralizada (settings.py / .env)
- [ ] Valores por defecto sensibles
- [ ] Sin hardcoding de URLs, puertos, credenciales
- [ ] `.env.example` actualizado con nuevas variables

---

## 9. Security — Delegar a Cybersecurity Agent

Si se detecta CUALQUIERA de estos, **delegar inmediatamente al skill `cybersecurity`:**
- Secrets en código
- Input sin validar
- Auth débil
- Datos sensibles en logs
- Dependencias con CVEs

---

## 📋 Reporte de Code Review

Al finalizar la revisión, generar reporte con:

```markdown
## 📝 Code Review Report

### Branch/Feature: [nombre]
### Archivos revisados: X
### Score: X/100

### ✅ Lo que está bien
- [Fortaleza 1]
- [Fortaleza 2]

### ⚠️ Mejoras necesarias
| ID | Gravedad | Archivo | Descripción | Sugerencia |
|----|----------|---------|-------------|------------|
| CR01 | ALTA | agent.py:44 | Validación en __post_init__ no cubre X | Añadir check |

### 🔜 Sugerencias opcionales
- [Sugerencia 1]
- [Sugerencia 2]

### 🛡️ Hallazgos de seguridad delegados a cybersecurity
- [Hallazgo 1] → cybersecurity agent
```

---

## 🚦 Gate Criteria (Condiciones para merge)

| Criterio | ¿Bloquea merge? |
|----------|:---:|
| Tests no pasan | 🔴 SÍ |
| Nuevo código sin tests | 🔴 SÍ |
| Vulnerabilidad crítica de seguridad | 🔴 SÍ |
| Error handling ausente en I/O | 🟠 SÍ |
| Código duplicado significativo | 🟠 SÍ |
| Naming confuso/engañoso | 🟡 NO (Warning) |
| Falta documentación de API pública | 🟡 NO (Warning) |
| Performance sub-óptima (no regresión) | 🟢 NO (Sugerencia) |

---

## Limitations
- Este skill hace análisis estático. No ejecuta tests (eso es CI).
- No reemplaza la revisión humana de arquitectura.
- Para hallazgos de seguridad, DELEGAR al skill `cybersecurity`.
- Si hay duda entre clean code y pragmatismo, preguntar al Arquitecto (Human).
