"""Configuración de la aplicación usando Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global cargada desde .env y variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Agencia IA"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # LLM Provider (agnostic)
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gpt-4o-mini"

    # Conversaciones (memoria del agente)
    conversation_history_limit: int = 10

    # WhatsApp Cloud API (Meta)
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = "my-verify-token"
    whatsapp_api_version: str = "v22.0"

    # n8n
    n8n_url: str = ""
    n8n_api_key: str = ""

    # Resend (Email)
    resend_api_key: str = ""
    email_from: str = "Agencia IA <noreply@agencia-ia.com>"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"

    # Security
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Cifrado de credenciales por tenant (Fase 3 — Fernet).
    # Vacío por defecto: FernetCredentialsCipher degrada a un fallback
    # base64 SOLO-DEV (ver app/infrastructure/security/credentials_cipher.py).
    # Generar con: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    credentials_encryption_key: str = ""

    # Recordatorios de cita (Fase 4). Frecuencia del job periódico de
    # Celery beat que busca y envía recordatorios — ver
    # app/infrastructure/config/celery_app.py (beat_schedule) y
    # app/infrastructure/celery/reminders.py (send_appointment_reminders).
    # Debe coincidir con el intervalo real del beat: la tarea usa este
    # mismo valor como ancho de la ventana de selección de citas, para
    # cubrir el tiempo entre ejecuciones sin huecos ni duplicados.
    reminder_beat_interval_minutes: int = 10


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuración. Se cachea para no leer .env cada vez."""
    return Settings()
