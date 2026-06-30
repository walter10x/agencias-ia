---
name: cybersecurity
description: >
  Auditor de ciberseguridad proactivo. Revisa cada cambio de código en busca de
  vulnerabilidades OWASP Top 10, secretos expuestos, dependencias inseguras,
  y malas prácticas de seguridad. Aplicar SIEMPRE antes de hacer commit o entregar.
  Triggers: "seguridad", "vulnerabilidad", "revisar seguridad", "security audit",
  "OWASP", "secrets", "pentest", "hack", "auditar".
risk: safe
source: "Agencia IA — Custom Skill"
date_added: "2026-06-07"
---

# Cybersecurity — Always-On Audit Skill

Este skill define las reglas de seguridad que se auditan en CADA cambio de código.
No es opcional. Todo commit debe pasar este filtro.

## 🛡️ Regla de Oro

**Si expone datos, autentica. Si recibe input, valida. Si usa dependencias, escanea. Si toca secrets, encripta.**

---

## 1. Secrets & Credentials (CRÍTICO)

| Qué buscar | Dónde | Acción |
|-----------|-------|--------|
| API Keys hardcodeadas | `.py`, `.ts`, `.tsx`, `.js`, `.env.example` | ❌ BLOQUEAR |
| Tokens JWT con valores reales | Código fuente, tests | ❌ BLOQUEAR |
| URLs con credenciales | `supabase_url`, `redis_url` | ❌ BLOQUEAR |
| Private keys / certificados | Cualquier archivo | ❌ BLOQUEAR |
| `.env` sin `.gitignore` | Raíz del proyecto | ⚠️ ADVERTIR |

### Checklist de Secrets:
- [ ] `.env` está en `.gitignore`
- [ ] `.env.example` no contiene valores reales
- [ ] Ningún archivo fuente contiene strings tipo `sk-...`, `eyJ...`, `-----BEGIN`
- [ ] Las URLs de conexión usan variables de entorno, no strings literales

---

## 2. Input Validation (OWASP #1 — Injection)

- **SQL Injection**: TODAS las queries usan parámetros bind (nunca string interpolation)
  ```python
  # ❌ PELIGRO
  query = f"SELECT * FROM clients WHERE id = '{client_id}'"

  # ✅ CORRECTO
  query = "SELECT * FROM clients WHERE id = :client_id"
  ```
- **Command Injection**: Nunca `os.system()` o `subprocess` con input de usuario
- **LLM Prompt Injection**: Sanitizar mensajes de usuario antes de inyectarlos en prompts
- **WhatsApp payload**: Validar estructura del webhook antes de procesar

### Checklist de Input:
- [ ] Todos los endpoints validan input con Pydantic/Zod
- [ ] Strings de usuario se escapan antes de insertar en HTML/JSON/SQL
- [ ] Límites de longitud en todos los campos de texto
- [ ] Validación de tipos estricta (no coercion automática)

---

## 3. Authentication & Authorization (OWASP #2, #5)

- **JWT**: 
  - Secret mínimo 256 bits (32 caracteres aleatorios)
  - Expiración configurada (máximo 60 minutos)
  - Algoritmo: HS256 mínimo, preferible RS256
  - Refresh tokens con rotación
- **API Keys**:
  - Evolution API: key única por instancia, mínimo 32 caracteres
  - n8n: autenticación básica o API key
- **Row Level Security**: Supabase RLS activado en TODAS las tablas
- **CORS**: Orígenes explícitos, nunca `allow_origins=["*"]` en producción

### Checklist de Auth:
- [ ] Endpoints sensibles requieren autenticación
- [ ] Validación de tenant (client_id) en cada request multi-tenant
- [ ] Rate limiting en endpoints de login (5 intentos/min)
- [ ] Las contraseñas/google nunca se loguean

---

## 4. Data Exposure (OWASP #3, #4)

- **Logging**: NUNCA loguear contraseñas, tokens, números de teléfono completos, mensajes de usuarios
- **Error responses**: No exponer stack traces en producción
  ```python
  # ❌ PELIGRO
  return {"error": str(e), "traceback": traceback.format_exc()}

  # ✅ CORRECTO
  return {"error": "Internal server error", "code": "INTERNAL_ERROR"}
  ```
- **Rate Limiting**: Endpoints públicos limitados (webhook WhatsApp: 50 req/s, API: 100 req/min)
- **Headers de seguridad**:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy` configurado

### Checklist de Datos:
- [ ] IDs de usuario enmascarados en logs
- [ ] Error responses genéricos en producción
- [ ] HTTPS forzado en producción
- [ ] CSP headers configurados

---

## 5. Dependencies Security (OWASP #6)

- **Python**: Revisar `requirements.txt` contra CVEs conocidos
  - Ejecutar: `pip-audit` o `safety check`
- **Node.js**: Revisar `package.json` contra CVEs
  - Ejecutar: `npm audit`
- **Imágenes Docker**: Usar versiones específicas, no `:latest`
- **Actualizaciones**: Dependencias con vulnerabilidades críticas = BLOQUEAR merge

### Checklist de Dependencias:
- [ ] No hay dependencias con CVEs críticos (CVSS >= 9.0)
- [ ] Docker images tienen tag específico (no `latest`)
- [ ] Base images son oficiales y actualizadas
- [ ] `.dockerignore` excluye `.env`, `.git`, `node_modules`

---

## 6. WhatsApp-Specific Security

- **Webhook verification**: Validar `hub.verify_token` en webhook de Evolution API
- **Message validation**: Verificar que el número de WhatsApp es válido antes de procesar
- **Rate limiting por número**: Máximo 10 mensajes/minuto por número
- **No almacenar mensajes en texto plano**: Considerar encriptación para conversaciones sensibles

---

## 7. CI/CD & Git Security

- **Pre-commit hooks**: Escanear secrets antes de commit (git-secrets, gitleaks)
- **.gitignore debe incluir**:
  ```
  .env
  *.pem
  *.key
  credentials.json
  service-account.json
  ```
- **Branches protegidos**: `main` requiere PR + review + tests pasando

---

## 🚨 Severidad de Hallazgos

| Nivel | Acción |
|-------|--------|
| 🔴 CRÍTICO | Bloquear merge inmediatamente. Requiere fix. |
| 🟠 ALTO | Bloquear merge. Fix requerido antes de deploy. |
| 🟡 MEDIO | Crear issue. No bloquea merge pero debe resolverse. |
| 🟢 BAJO | Advertencia. Mejora sugerida. |

---

## 📋 Reporte de Auditoría

Al finalizar el análisis, generar reporte con:

```markdown
## 🔐 Security Audit Report

### Resumen
- Archivos revisados: X
- Hallazgos críticos: X
- Hallazgos altos: X
- Score de seguridad: X/100

### Hallazgos
| ID | Severidad | Archivo | Línea | Descripción | Fix sugerido |
|----|-----------|---------|-------|-------------|--------------|
| S01 | CRÍTICO | main.py | 42 | API key hardcodeada | Usar env var |

### Recomendaciones
- [Prioridad 1] ...
- [Prioridad 2] ...
```

---

## Limitations
- Este skill no ejecuta pentesting activo. Solo análisis estático.
- No reemplaza una auditoría de seguridad profesional.
- Stop y pregunta si encuentras algo que requiera criterio humano (ej: arquitectura de auth).
