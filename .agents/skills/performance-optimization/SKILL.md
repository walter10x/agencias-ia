---
name: performance-optimization
description: >
  Optimización de rendimiento y latencia. Aplicar SIEMPRE en cada commit.
  Async-first, caché agresivo, pooling, índices, streaming, lazy loading.
  Triggers: "optimizar", "rendimiento", "lento", "rápido", "performance",
  "latencia", "cache", "speed", "optimize".
---

# Performance Optimization — Always-On Skill

Esta skill define los principios de rendimiento que se aplican en CADA decisión de código. No es opcional, es un estándar del proyecto.

## Regla de Oro

**Si tarda más de 200ms, ponle caché. Si tarda más de 1s, hazlo async.**

## Principios (aplicar siempre)

### 1. Async/Non-blocking (Backend)
- TODAS las operaciones I/O son async: DB queries, HTTP calls, file reads.
- FastAPI usa `async def` en todos los endpoints.
- LLM calls usan streaming (`StreamingResponse`).
- Conexiones DB usan pool, nunca una sola conexión.

### 2. Caché Agresivo
| Qué cachear | Dónde | TTL |
|-------------|-------|-----|
| FAQ respuestas | Redis | 1 hora |
| Config de agentes | Redis | 10 min |
| Sesiones de usuario | Redis | 30 min |
| Embeddings RAG | pgvector (indexado) | Permanente |
| Frontend assets | CDN (Cloudflare) | 1 año |
| API responses GET | Redis opcional | 5 min |

### 3. Base de Datos
- Índices para TODOS los campos de filtro frecuente (`client_id`, `agent_id`, `created_at`).
- pgvector usa índices IVFFlat o HNSW.
- Pool de conexiones: mínimo 5, máximo 20.
- Queries usan parámetros bind, nunca string interpolation.
- Paginación con cursores, nunca `OFFSET/LIMIT` en tablas grandes.

### 4. LLM / IA
- Streaming de tokens (el usuario ve respuesta mientras se genera).
- Caché de respuestas idénticas (mismo prompt + mismo contexto = misma respuesta).
- Timeout máximo de 15 segundos para llamadas LLM.
- Usar el modelo más pequeño que cumpla (GPT-4o-mini para FAQs, GPT-4o para ventas complejas).

### 5. Frontend
- Lazy loading de rutas (`React.lazy` + `Suspense`).
- Code splitting por página (Vite lo hace automático).
- Imágenes en WebP/AVIF con `loading="lazy"`.
- Tailwind purga CSS no usado.
- shadcn/ui importa solo componentes usados (tree-shakeable).
- React Flow: solo renderiza nodos visibles (viewport culling).

### 6. WhatsApp / Webhooks
- Evolution API webhook responde 200 OK inmediatamente.
- Procesamiento del mensaje en background (Celery o `asyncio.create_task`).
- No bloquear el webhook NUNCA.

### 7. Infraestructura
- Gzip/Brotli compression en FastAPI.
- HTTP/2 en producción.
- CDN para frontend estático (Cloudflare Pages, Vercel).
- Rate limiting por IP y por client_id.

## Anti-Patterns (NUNCA hacer)

| ❌ Anti-Pattern | ✅ Alternativa |
|-----------------|----------------|
| `time.sleep()` en endpoint | `asyncio.sleep()` |
| Query sin índice en WHERE | Migración con `CREATE INDEX` |
| Cargar TODOS los mensajes de una conversación | Paginación con cursor |
| `SELECT *` en producción | Solo columnas necesarias |
| LLM call síncrono | Streaming via `httpx` async |
| `OFFSET 1000 LIMIT 50` | Cursor-based pagination |
| Esperar LLM en webhook de WhatsApp | Responder 200, procesar en background |
| No tener timeout en llamadas externas | `httpx.Timeout(15.0)` |
| Caché sin TTL | Siempre con TTL explícito |

## Checklist por Feature

Antes de mergear cualquier feature:
- [ ] ¿Endpoints I/O son `async def`?
- [ ] ¿Hay caché para respuestas repetitivas?
- [ ] ¿Índices creados en campos de filtro?
- [ ] ¿LLM usa streaming?
- [ ] ¿Frontend usa lazy loading?
- [ ] ¿Webhooks responden antes de procesar?
- [ ] ¿Timeouts configurados en llamadas externas?

## Métricas Target

| Métrica | Objetivo MVP | Objetivo Producción |
|---------|-------------|-------------------|
| Respuesta webhook WhatsApp | < 500ms | < 200ms |
| Primera respuesta LLM (streaming) | < 1s | < 500ms |
| Dashboard carga inicial | < 2s | < 1s |
| API response (caché hit) | < 50ms | < 20ms |
| API response (caché miss) | < 200ms | < 100ms |
| RAG búsqueda pgvector | < 100ms | < 50ms |
