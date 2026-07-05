# Guía de Despliegue: Agencias IA en Dokploy

> **Última actualización**: 4 Julio 2026
> **Stack**: Docker Compose (8 servicios) + Traefik + GitHub auto-deploy
> **Tiempo de deploy**: ~5-8 min (build) + 30s (cold start)
> **Estado**: ✅ Desplegado en `proyecto: agencias-ia` → `compose: agencias-ia-stack`

---

## Tabla de Contenidos

1. [Arquitectura](#arquitectura)
2. [Prerequisitos](#prerequisitos)
3. [Estructura del Repositorio](#estructura-del-repositorio)
4. [Setup Inicial en Dokploy](#setup-inicial-en-dokploy)
5. [Variables de Entorno](#variables-de-entorno)
6. [Configuración de Dominios y SSL](#configuración-de-dominios-y-ssl)
7. [Despliegue](#despliegue)
8. [Verificación Post-Deploy](#verificación-post-deploy)
9. [Operación del Día a Día](#operación-del-día-a-día)
10. [Troubleshooting](#troubleshooting)
11. [Rollback](#rollback)
12. [Seguridad](#seguridad)
13. [Costos y Recursos](#costos-y-recursos)

---

## Arquitectura

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          DOKPLOY (Servidor)                                 │
│                                                                            │
│  ┌──────────┐    ┌─────────────────────────────────────────────────┐      │
│  │ GitHub   │───▶│ Compose: agencias-ia-stack (docker-compose)      │      │
│  │ App      │    │                                                  │      │
│  │(webhook) │    │  ┌─────────┐  ┌──────────┐  ┌──────────────┐    │      │
│  └──────────┘    │  │frontend │  │ backend │  │celery-worker │    │      │
│       │           │  │  :80    │  │  :8000  │  │   (celery)   │    │      │
│       │           │  └────┬────┘  └─────┬────┘  └──────┬───────┘    │      │
│       │           │       │             │              │            │      │
│       │           │       └─────────────┼──────────────┘            │      │
│       │           │                     │                            │      │
│       │           │       ┌─────────────▼──────────────┐             │      │
│       │           │       │  postgrest-proxy (nginx)  │             │      │
│       │           │       │          :3000             │             │      │
│       │           │       └─────────────┬──────────────┘             │      │
│       │           │                     │                            │      │
│       │           │       ┌─────────────▼──────────────┐             │      │
│       │           │       │   postgrest + postgres    │             │      │
│       │           │       │   (pgvector extension)   │             │      │
│       │           │       └────────────────────────────┘             │      │
│       │           │                                                  │      │
│       │           │       ┌─────────┐  ┌──────────┐                 │      │
│       │           │       │  redis  │  │   n8n    │                 │      │
│       │           │       │  :6379  │  │  :5678   │                 │      │
│       │           │       └─────────┘  └──────────┘                 │      │
│       │           └─────────────────────────────────────────────────┘      │
│       │                              │                                     │
│       │                              ▼                                     │
│       │                    ┌──────────────────┐                            │
│       └───────────────────▶│     Traefik      │◀── HTTPS (Let's Encrypt)  │
│                            │  (auto SSL/TLS)  │                            │
│                            └─────────┬────────┘                            │
└──────────────────────────────────────┼─────────────────────────────────────┘
                                       │
                                       ▼
                          🌍 Internet (clientes)
```

### Servicios (8 total)

| # | Servicio | Puerto interno | Imagen | Función |
|---|----------|---------------|--------|---------|
| 1 | `frontend` | 80 | Build (Vite + nginx) | Panel de control React |
| 2 | `backend` | 8000 | Build (FastAPI) | API + LLM + WhatsApp |
| 3 | `celery-worker` | — | Build (mismo Dockerfile que backend) | Tareas async (PDF, mensajes) |
| 4 | `postgres` | 5432 | `pgvector/pgvector:pg16` | DB + embeddings |
| 5 | `postgrest` | 3000 | `postgrest/postgrest:latest` | API REST compatible Supabase |
| 6 | `postgrest-proxy` | 3000 | `nginx:alpine` | Re-enruta /rest/v1/* |
| 7 | `redis` | 6379 | `redis:7-alpine` | Caché + Celery broker |
| 8 | `n8n` | 5678 | `n8nio/n8n:latest` | Workflows automatizados |

---

## Prerequisitos

### En Dokploy

- ✅ Dokploy instalado y accesible
- ✅ GitHub App configurada (en este caso: `Dokploy-wrhorse`)
- ✅ Traefik activo y configurado para Let's Encrypt
- ✅ Al menos **2 GB de RAM** y **10 GB de disco** libres

### En GitHub

- ✅ Repositorio público o con GitHub App instalada: `walter10x/agencias-ia`
- ✅ Branch `main` con el código actualizado

### DNS

Para producción real (no incluido en este deploy de prueba):
- `agencias.dominio.com` → IP pública del servidor Dokploy
- `n8n.dominio.com` → IP pública del servidor Dokploy

### API Keys externas (rellenar antes de activar el bot)

- **LLM**: OpenAI API key, Anthropic, o un gateway local (Ollama, oinoco proxy, etc.)
- **WhatsApp Cloud API** (Meta): `WHATSAPP_PHONE_NUMBER_ID` + `WHATSAPP_ACCESS_TOKEN`
- Opcional: **Evolution API** si quieres usar un gateway WhatsApp self-hosted

---

## Estructura del Repositorio

```
agencias-ia/                      ← repo GitHub
├── .gitignore                    ← env, node_modules, .venv, stitch-output
├── README.md
├── docker-compose.yml            ← DESARROLLO LOCAL (usa .env file)
├── docker-compose.production.yml ← PRODUCCIÓN (usa ${VAR} refs, Traefik labels)
├── backend-core/                 ← FastAPI + LangGraph
│   ├── .env                      ← gitignored, solo dev local
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── application/
│       ├── domain/
│       └── infrastructure/
│           ├── ai/               ← OpenAI/anthropic/ollama/opencode adapters
│           ├── whatsapp/         ← webhook + message processor
│           ├── http/             ← FastAPI routers
│           ├── config/           ← settings + celery + tasks
│           └── persistence/
├── frontend-dashboard/           ← React + Vite + TypeScript
│   ├── Dockerfile
│   ├── package.json
│   └── src/
├── docker/
│   ├── nginx/
│   │   └── default.conf          ← config postgrest-proxy
│   └── postgres/
│       └── init.sql              ← schema + migraciones
├── GUIA.md
├── GUIA-INTEGRACION.md
└── GUIA-DESPLIEGUE-DOKPLOY.md    ← este archivo
```

### Diferencias clave entre `docker-compose.yml` y `docker-compose.production.yml`

| Aspecto | Local (`docker-compose.yml`) | Producción (`docker-compose.production.yml`) |
|---------|------------------------------|---------------------------------------------|
| Config | `env_file: ./backend-core/.env` | `environment: ${VAR}` (Dokploy inyecta) |
| Puertos host | `5051:80`, `8000:8000`, etc. | Sin puertos host (Traefik enruta) |
| Routing | Localhost | Traefik labels + dominios |
| Volúmenes | Bind mounts (código en vivo) | Solo data persistente (postgres, n8n) |
| Build args | Sin args | `VITE_API_URL` para el frontend |

---

## Setup Inicial en Dokploy

### Paso 1: Crear el proyecto

```bash
# Vía MCP Dokploy o UI:
dokploy_project_create(
  name="agencias-ia",
  description="Plataforma SaaS multi-tenant de agencias de IA",
  env="..."  # variables globales (opcional)
)
```

**Resultado**: `projectId: fg7t_auA0vd-AQ4Gcy6dj` (production environment `j6fMoQR7nYMX1w2-CXbuQ`)

### Paso 2: Verificar GitHub Provider

```bash
dokploy_github_githubProviders()
# Debe listar: Dokploy-wrhorse (githubId: MIKORVsBDVaTbtW6gl3hy)
```

Si no está, instalarla desde Dokploy UI: **Settings → Git Providers → Add GitHub App**.

### Paso 3: Crear Compose Service

```bash
dokploy_compose_create(
  name="agencias-ia-stack",
  environmentId="<env_id>",
  composeType="docker-compose",
  composeFile="docker-compose.production.yml"
)
```

### Paso 4: Vincular repo de GitHub

```bash
dokploy_compose_update(
  composeId="<compose_id>",
  sourceType="github",
  repository="agencias-ia",
  owner="walter10x",
  branch="main",
  githubId="<github_provider_id>",
  composePath="./docker-compose.production.yml",
  autoDeploy=true,           # redespliega en cada push
  triggerType="push"
)
```

> **Importante**: el `composePath` debe apuntar a `docker-compose.production.yml`, no al `docker-compose.yml` original.

---

## Variables de Entorno

Todas las variables se configuran con `dokploy_compose_saveEnvironment`. El archivo está dividido en secciones:

### 1. Dominios (Traefik routing)

```bash
APP_DOMAIN=agencias.tu-dominio.com
N8N_DOMAIN=n8n.tu-dominio.com
N8N_HOST=${N8N_DOMAIN}
```

### 2. Base de datos (OBLIGATORIO cambiar)

```bash
POSTGRES_DB=agencias_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<CAMBIAR-PASSWORD-FUERTE>   # ← CHANGE_ME
POSTGREST_PASSWORD=<CAMBIAR-PASSWORD-FUERTE> # ← mismo que postgres
```

Generar password fuerte:
```bash
openssl rand -hex 32
```

### 3. Backend / PostgREST

```bash
SUPABASE_URL=http://postgrest-proxy:3000
SUPABASE_SERVICE_KEY=local-no-auth-needed
```

### 4. LLM Provider (al menos uno)

```bash
# OpenAI
LLM_PROVIDER=openai
LLM_API_KEY=sk-proj-xxxxxxxxxxxx
LLM_MODEL=gpt-4o-mini

# O Anthropic
# LLM_PROVIDER=anthropic
# LLM_API_KEY=sk-ant-xxxxxxxxxxxx
# LLM_MODEL=claude-3-5-sonnet-20240620

# O Ollama local (en el mismo host)
# LLM_PROVIDER=ollama
# LLM_API_KEY=not-needed
# LLM_BASE_URL=http://host.docker.internal:11434/v1
# LLM_MODEL=llama3.2

# O gateway corporativo OpenAI-compatible
# LLM_PROVIDER=opencode
# LLM_BASE_URL=https://mi-gateway.com/v1
# LLM_API_KEY=<key>
# LLM_MODEL=<modelo>
```

> **Nota**: `LLM_BASE_URL` vacío = usa la API oficial del provider.

### 5. WhatsApp Cloud API (Meta)

```bash
WHATSAPP_PHONE_NUMBER_ID=<phone-number-id-de-ejemplo>
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxx...
WHATSAPP_VERIFY_TOKEN=my-verify-token
WHATSAPP_API_VERSION=v22.0
```

El `VERIFY_TOKEN` debe coincidir con el configurado en Meta Developers → Webhook.

### 6. n8n

```bash
N8N_URL=http://n8n:5678
N8N_API_KEY=<opcional, se llena después>
N8N_WEBHOOK_URL=https://${N8N_DOMAIN}/
GENERIC_TIMEZONE=America/Bogota
```

### 7. Seguridad (CRÍTICO)

```bash
JWT_SECRET=<64-CHAR-RANDOM-HEX>   # ← CAMBIAR (openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

> ⚠️ **NUNCA** dejar `JWT_SECRET` con un valor de ejemplo. Compromete la auth de toda la plataforma.

### 8. App

```bash
DEBUG=false                     # nunca true en producción
CORS_ORIGINS=["https://${APP_DOMAIN}"]
VITE_API_URL=https://${APP_DOMAIN}    # build-time del frontend
```

---

## Configuración de Dominios y SSL

### Opción A: Dominio real (recomendado para producción)

1. **DNS**: Apuntar `agencias.tu-dominio.com` y `n8n.tu-dominio.com` a la IP del servidor Dokploy
2. **Esperar propagación DNS** (5-30 min)
3. **Dokploy configura SSL automático** vía Let's Encrypt cuando el contenedor arranca (label `traefik.http.routers.X.tls.certresolver=letsencrypt`)

### Opción B: Subdominio .dokploy.me (testing rápido)

Dokploy puede asignar subdominios gratis `.dokploy.me`:

```bash
dokploy_domain_create(
  host="agencias-test.dokploy.me",
  https=true,
  certificateType="letsencrypt",
  composeId="<compose_id>",
  serviceName="frontend",
  path="/",
  stripPath=false
)
```

Repetir para `backend` y `n8n` con `serviceName` diferente.

### Opción C: IP directa (sin SSL)

Solo para dev/testing interno. Dokploy puede generar el dominio:

```bash
dokploy_domain_generateDomain(
  appName="<appName>",
  serverId="<server_id>"
)
```

---

## Despliegue

### Primer Deploy

```bash
# Disparar el deploy
dokploy_compose_deploy(
  composeId="<compose_id>",
  title="Initial production deploy",
  description="..."
)

# Monitorear progreso
dokploy_deployment_allByCompose(composeId="<compose_id>")
# status: idle → running → done | error
```

### Auto-deploy en cada push

Una vez configurado `autoDeploy=true`, cada `git push origin main` dispara:
1. Webhook de GitHub → Dokploy
2. Dokploy clona el repo
3. Ejecuta `docker compose build` (usa `build:` contexts)
4. Ejecuta `docker compose up -d`
5. Verifica healthchecks

---

## Verificación Post-Deploy

### 1. Status de los servicios

```bash
dokploy_docker_getContainersByAppLabel(
  appName="<appName_del_compose>",  # ej: compose-connect-neural-hard-drive-5rn4wr
  type="standalone"
)
```

Debe mostrar 8 containers con `Status: Up`.

### 2. Health check del backend

```bash
curl https://agencias.tu-dominio.com/health
# Esperado: {"status":"ok","version":"0.1.0"}
```

### 3. Webhook de WhatsApp (verificación Meta)

```bash
curl "https://agencias.tu-dominio.com/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=my-verify-token&hub.challenge=test"
# Esperado: test
```

### 4. Frontend carga

Abrir en navegador: `https://agencias.tu-dominio.com` — debe cargar el panel React.

### 5. n8n

Abrir: `https://n8n.tu-dominio.com` — debe mostrar pantalla de setup de admin.

### 6. Base de datos

```bash
dokploy_docker_getContainersByAppLabel(
  appName="<appName>", type="standalone"
)
# Buscar agencia-postgres, hacer exec:
dokploy_docker_getConfig(containerId="<postgres_container_id>")
# Inspeccionar variables de entorno
```

### 7. Logs

```bash
dokploy_compose_readLogs(
  composeId="<compose_id>",
  containerId="<container_name>",  # ej: agencia-backend
  tail=200
)
```

---

## Operación del Día a Día

### Redesplegar (código nuevo)

```bash
# Local
git add -A
git commit -m "feat: ..."
git push origin main
# Dokploy redespliega automáticamente (autoDeploy=true)
```

### Redesplegar manual (sin push)

```bash
dokploy_compose_redeploy(
  composeId="<compose_id>",
  title="Manual redeploy",
  description="..."
)
```

### Cambiar variables de entorno

```bash
# 1. Editar env
dokploy_compose_saveEnvironment(
  composeId="<compose_id>",
  env="<nuevo contenido>"
)

# 2. Forzar redeploy para que tome los nuevos valores
dokploy_compose_redeploy(composeId="<compose_id>", title="env update")
```

### Ver logs en vivo

UI Dokploy → proyecto `agencias-ia` → compose `agencias-ia-stack` → tab "Logs" → seleccionar container.

### Escalar servicios

Para escalar celery workers (si hay mucha carga):

```yaml
# En docker-compose.production.yml:
celery-worker:
  ...
  deploy:
    replicas: 3
```

Después:
```bash
dokploy_compose_redeploy(composeId="<compose_id>", title="scale celery")
```

### Backup de la base de datos

```bash
# Configurar backup automático en Dokploy:
dokploy_backup_create(
  schedule="0 3 * * *",  # diario a las 3am
  destinationId="<id del destination S3/local>",
  database="agencias_db",
  databaseType="postgres",
  postgresId="<postgres_id>"
)
```

---

## Troubleshooting

### Backend no arranca

```bash
# Ver logs
dokploy_compose_readLogs(composeId="<id>", containerId="agencia-backend", tail=100)

# Causas comunes:
# 1. JWT_SECRET no está configurado (compose usa :? syntax)
# 2. POSTGRES_PASSWORD muy corto o con caracteres especiales no escapados
# 3. LLM_API_KEY inválido (pero no debería impedir el startup)
```

### Webhook no responde

```bash
# 1. Verificar que el contenedor backend está up
dokploy_docker_getContainersByAppLabel(...)

# 2. Probar el endpoint internamente
dokploy_docker_getConfig(containerId="<agencia-backend_id>")
# Buscar la network y hacer exec
# O usar la UI de Dokploy → Exec

# 3. Verificar DNS y Traefik
curl -I https://agencias.tu-dominio.com/webhook/whatsapp
# Debe devolver 405 (GET no permitido) o 200 (si el verify pasa)
```

### Frontend no carga / muestra pantalla blanca

```bash
# 1. Verificar que VITE_API_URL se inyectó en el build
dokploy_compose_readLogs(composeId="<id>", containerId="agencia-frontend", tail=50)
# Buscar errores de nginx (404 en archivos JS)

# 2. Causa común: APP_DOMAIN no estaba seteado cuando se hizo el primer build
# Solución: cambiar APP_DOMAIN y redeploy (rebuild del frontend)
```

### n8n pide login pero no hay credenciales

n8n con `N8N_BASIC_AUTH_ACTIVE=false` permite crear la primera cuenta de owner al primer acceso. Ir a `https://n8n.tu-dominio.com/setup` y crear admin.

### Disco lleno

```bash
# Limpiar imágenes dangling
dokploy_settings_cleanDockerPrune(serverId="<server_id>")

# O desde dentro del servidor:
docker system prune -a
```

---

## Rollback

### Rollback del último deploy

```bash
dokploy_rollback_list()  # listar rollbacks disponibles
# O vía UI: Deployments → click en uno anterior → "Rollback to this"
```

### Rollback completo del env

Si cambiaste variables de entorno y rompiste algo:

```bash
# 1. Restaurar el env desde git
cd /path/agencias-ia
git log --oneline -10  # encontrar el último commit bueno del env

# 2. Reconstruir el archivo de env
# (copiar el bloque correcto de variables)

# 3. Aplicar
dokploy_compose_saveEnvironment(composeId="<id>", env="<env restaurado>")
dokploy_compose_redeploy(composeId="<id>", title="env rollback")
```

### Rollback del compose file

```bash
# Revertir cambios en el repo
git revert HEAD~3..HEAD
git push origin main
# Dokploy redespliega con el compose antiguo
```

---

## Seguridad

### Secretos que NUNCA deben commitearse

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `LLM_API_KEY` (OpenAI, Anthropic, etc.)
- `WHATSAPP_ACCESS_TOKEN`
- `N8N_API_KEY` (cuando se cree)
- Cualquier `*.pem` o `*.key`

El `.gitignore` del repo ya excluye `.env`, `*.pem`, `*.key`. Pero **siempre** verifica antes de hacer `git add`:

```bash
git diff --staged
```

### Checklist pre-producción

- [ ] `JWT_SECRET` es un string random de al menos 32 bytes
- [ ] `POSTGRES_PASSWORD` es fuerte y único
- [ ] `DEBUG=false`
- [ ] `CORS_ORIGINS` solo incluye el dominio real
- [ ] `LLM_PROVIDER` y `LLM_API_KEY` apuntan al servicio correcto
- [ ] `WHATSAPP_VERIFY_TOKEN` coincide con el de Meta Developers
- [ ] SSL de Let's Encrypt activo en todos los dominios
- [ ] Backups de postgres configurados
- [ ] Monitoreo de contenedores (Dokploy tiene notificaciones Telegram/Discord/email)

### Rotación de secretos

Rotar cada 90 días:
- `JWT_SECRET` (invalida todos los tokens de usuario, hay que re-loguear)
- `POSTGRES_PASSWORD` (requiere reconfigurar `postgrest` también)
- API keys (OpenAI, etc.) — desde el panel del provider

---

## Costos y Recursos

### Recursos del servidor Dokploy (mínimos)

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disco | 20 GB | 50 GB SSD |
| Ancho de banda | 100 GB/mes | Ilimitado |

### Costos externos (depende del provider)

| Servicio | Costo aproximado |
|----------|------------------|
| **OpenAI GPT-4o-mini** | ~$0.15 / 1M tokens (~$15/mes para 100 clientes activos) |
| **Anthropic Claude Haiku** | ~$0.25 / 1M tokens |
| **Meta WhatsApp Cloud** | Gratis los primeros 1000 mensajes/mes, luego ~$0.005 c/u |
| **Dominio** | ~$10-15/año |
| **VPS Dokploy** | $20-50/mes (Hetzner, DigitalOcean, etc.) |

### Optimizaciones para reducir costos

1. **Cachear respuestas frecuentes** con Redis (ya configurado)
2. **Rate limiting** (ya configurado: 10 msg/60s por número)
3. **Modelos más baratos** para casos simples (clasificación, FAQ) y más caros solo para conversación
4. **Embeddings locales** con Ollama en vez de OpenAI

---

## Próximos Pasos

Después del primer deploy exitoso:

1. [ ] Configurar backups automáticos de Postgres (Dokploy → Backups)
2. [ ] Configurar notificaciones (Dokploy → Settings → Notifications): Telegram/Discord/email
3. [ ] Crear el primer superadmin vía `/admin` (o `scripts/seed_superadmin.py` con `SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD` propios — sin defaults hardcodeados)
4. [ ] Configurar el webhook de Meta con la URL real: `https://agencias.tu-dominio.com/webhook/whatsapp`
5. [ ] Configurar el LLM con la API key real
6. [ ] Crear el primer cliente y agente de prueba
7. [ ] Enviar un WhatsApp de prueba y verificar respuesta
8. [ ] Configurar workflows en n8n para automatizaciones
9. [ ] Documentar en `GUIA-CONEXION-CLIENTES.md` cómo cada cliente nuevo se conecta

---

## Referencias

- **Dokploy docs**: https://docs.dokploy.com
- **Docker Compose reference**: https://docs.docker.com/compose/compose-file/
- **Traefik labels**: https://doc.traefik.io/traefik/routing/routers/#rule
- **Meta WhatsApp Cloud API**: https://developers.facebook.com/docs/whatsapp/cloud-api
- **PostgREST**: https://postgrest.org/en/stable/
- **pgvector**: https://github.com/pgvector/pgvector
- **LangGraph + FastAPI**: ver `backend-core/specs/spec-llm-langgraph.md`

---

**Mantenedor**: Equipo Agencias IA
**Último deploy**: ver `git log` del proyecto
**Status dashboard**: <URL de Dokploy>
