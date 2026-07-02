"""Punto de entrada FastAPI para la agencia de IA multi-tenant."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.infrastructure.config.settings import get_settings
from app.infrastructure.http.agent_router import router as agent_router
from app.infrastructure.http.auth_router import router as auth_router
from app.infrastructure.http.client_router import router as client_router
from app.infrastructure.http.conversation_router import router as conversation_router
from app.infrastructure.http.email_router import router as email_router
from app.infrastructure.http.error_handlers import register_error_handlers
from app.infrastructure.http.feedback_router import router as feedback_router
from app.infrastructure.http.landing_router import admin_router as landing_admin_router
from app.infrastructure.http.landing_router import public_router as landing_public_router
from app.infrastructure.http.lead_router import router as lead_router
from app.infrastructure.templates.router import router as template_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa y limpia recursos de la aplicación."""
    # TODO: Inicializar pool de conexiones Supabase, Redis, etc.
    yield
    # TODO: Cerrar conexiones


app = FastAPI(
    title="Agencia IA - Multi-Tenant Platform",
    description="Plataforma de agentes IA para negocios locales vía WhatsApp",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Endpoint de health check para monitoreo."""
    return {"status": "ok", "version": "0.1.0"}


# Register domain error → HTTP exception handlers
register_error_handlers(app)

# Register routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(client_router, prefix="/api/v1/clients", tags=["Clients"])
app.include_router(agent_router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(conversation_router, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(lead_router, prefix="/api/v1/leads", tags=["Leads"])
app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(template_router, prefix="/api/v1/templates", tags=["Templates"])
app.include_router(landing_public_router, prefix="/api/v1/landing", tags=["Landing Pages"])
app.include_router(landing_admin_router, prefix="/api/v1/clients", tags=["Landing Admin"])
app.include_router(email_router, prefix="/api/v1/emails", tags=["Email Marketing"])

# Register WhatsApp webhook
from app.infrastructure.whatsapp.webhook import router as whatsapp_router
app.include_router(whatsapp_router, tags=["WhatsApp"])
