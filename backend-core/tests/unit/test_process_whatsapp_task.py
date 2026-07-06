"""Unit tests for process_whatsapp_message — Fase 1 persistencia.

Verifica que la tarea Celery:
1. Busca/crea la conversación por (client_id, phone) y guarda el entrante.
2. Inyecta los últimos N mensajes como historial de chat en run_agent.
3. Guarda la respuesta del agente con el estado REAL del envío
   (sent / failed / skipped — nunca "sent" ficticio).

Todo mockeado: sin llamadas reales a OpenAI, Meta ni Supabase.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.agent.entity import Agent
from app.domain.conversation.entity import Conversation, Message
from app.domain.conversation.repository import ConversationRepository
from app.domain.shared.errors import DomainError
from app.domain.shared.value_objects import ClientId
from app.infrastructure.config import tasks as tasks_module
from app.infrastructure.config.settings import get_settings

CLIENT_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AGENT_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")
CONV_UUID = uuid.UUID("33333333-3333-3333-3333-333333333333")
PHONE = "573001234567"
INCOMING = "Hola, quiero agendar una cita"
REPLY = "¡Claro! ¿Para qué día te gustaría la cita?"


def _make_agent() -> Agent:
    return Agent(
        id=AGENT_UUID,
        client_id=ClientId(CLIENT_UUID),
        name="Recepcionista",
        personality="Eres un asistente amable y profesional. Diez caracteres minimo.",
        tools=[],
        knowledge_base_refs=[],
        is_active=True,
    )


def _make_existing_conversation() -> Conversation:
    return Conversation(
        id=CONV_UUID,
        client_id=CLIENT_UUID,
        agent_id=AGENT_UUID,
        wa_phone_number=PHONE,
    )


@pytest.fixture
def conv_repo() -> AsyncMock:
    """Mock del puerto ConversationRepository (sin Supabase real)."""
    repo = AsyncMock(spec=ConversationRepository)
    repo.find_by_client_and_phone.return_value = None
    repo.get_recent_messages.return_value = []
    return repo


@pytest.fixture
def run_task(conv_repo: AsyncMock):
    """Ejecuta la tarea con todas las dependencias externas mockeadas.

    Devuelve (result, run_agent_mock, send_mock).
    """

    def _run(
        *,
        agent: Agent | None = None,
        send_status: str = "sent",
        reply: str = REPLY,
    ):
        if agent is None:
            agent = _make_agent()

        run_agent_mock = AsyncMock(return_value=reply)
        with (
            patch.object(tasks_module, "_load_agent_sync", return_value=agent),
            patch.object(tasks_module, "get_llm_adapter", return_value=MagicMock()),
            patch.object(tasks_module, "run_agent", run_agent_mock),
            patch.object(
                tasks_module, "_get_conversation_repo", return_value=conv_repo
            ),
            patch.object(
                tasks_module, "_send_whatsapp_message", return_value=send_status
            ) as send_mock,
        ):
            result = tasks_module.process_whatsapp_message(
                client_id=str(CLIENT_UUID),
                phone=PHONE,
                message=INCOMING,
                agent_id=str(AGENT_UUID),
                push_name="Juan",
            )
        return result, run_agent_mock, send_mock

    return _run


# ======================================================================
# 1. Buscar/crear conversación + guardar mensaje entrante
# ======================================================================


class TestIncomingPersistence:
    def test_creates_conversation_when_none_exists(
        self, run_task, conv_repo: AsyncMock
    ) -> None:
        conv_repo.find_by_client_and_phone.return_value = None

        result, _, _ = run_task()

        conv_repo.find_by_client_and_phone.assert_awaited_once_with(
            str(CLIENT_UUID), PHONE
        )
        conv_repo.save.assert_awaited_once()
        saved = conv_repo.save.await_args[0][0]
        assert isinstance(saved, Conversation)
        assert saved.client_id == CLIENT_UUID
        assert saved.agent_id == AGENT_UUID
        assert saved.wa_phone_number == PHONE
        assert result["conversation_id"] == str(saved.id)

    def test_reuses_existing_conversation(
        self, run_task, conv_repo: AsyncMock
    ) -> None:
        existing = _make_existing_conversation()
        conv_repo.find_by_client_and_phone.return_value = existing

        result, _, _ = run_task()

        # No crea una nueva: refresca la existente (updated_at bump)
        conv_repo.save.assert_awaited_once()
        saved = conv_repo.save.await_args[0][0]
        assert saved.id == CONV_UUID
        assert result["conversation_id"] == str(CONV_UUID)

    def test_saves_incoming_user_message(
        self, run_task, conv_repo: AsyncMock
    ) -> None:
        existing = _make_existing_conversation()
        conv_repo.find_by_client_and_phone.return_value = existing

        run_task()

        # Primer append: mensaje entrante del usuario
        first_msg = conv_repo.append_message.await_args_list[0][0][0]
        assert isinstance(first_msg, Message)
        assert first_msg.conversation_id == CONV_UUID
        assert first_msg.role == "user"
        assert first_msg.content == INCOMING
        assert first_msg.status == "received"


# ======================================================================
# 2. Historial inyectado como mensajes de chat
# ======================================================================


class TestHistoryInjection:
    def test_history_passed_as_chat_messages(
        self, run_task, conv_repo: AsyncMock
    ) -> None:
        existing = _make_existing_conversation()
        conv_repo.find_by_client_and_phone.return_value = existing
        conv_repo.get_recent_messages.return_value = [
            Message(conversation_id=CONV_UUID, role="user", content="Hola"),
            Message(
                conversation_id=CONV_UUID,
                role="assistant",
                content="¡Hola! ¿En qué te ayudo?",
                status="sent",
            ),
        ]

        _, run_agent_mock, _ = run_task()

        history = run_agent_mock.await_args.kwargs["history"]
        assert history == [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¡Hola! ¿En qué te ayudo?"},
        ]

    def test_history_uses_configured_limit(
        self, run_task, conv_repo: AsyncMock
    ) -> None:
        existing = _make_existing_conversation()
        conv_repo.find_by_client_and_phone.return_value = existing

        run_task()

        expected_limit = get_settings().conversation_history_limit
        conv_repo.get_recent_messages.assert_awaited_once_with(
            str(CONV_UUID), limit=expected_limit
        )

    def test_empty_history_for_new_conversation(
        self, run_task, conv_repo: AsyncMock
    ) -> None:
        conv_repo.find_by_client_and_phone.return_value = None
        conv_repo.get_recent_messages.return_value = []

        _, run_agent_mock, _ = run_task()

        assert run_agent_mock.await_args.kwargs["history"] == []


# ======================================================================
# 3. Respuesta del agente persistida con estado real
# ======================================================================


class TestReplyPersistence:
    @pytest.mark.parametrize("send_status", ["sent", "failed", "skipped"])
    def test_reply_saved_with_real_send_status(
        self, run_task, conv_repo: AsyncMock, send_status: str
    ) -> None:
        existing = _make_existing_conversation()
        conv_repo.find_by_client_and_phone.return_value = existing

        result, _, _ = run_task(send_status=send_status)

        assert result["status"] == send_status
        # Segundo append: respuesta del asistente con estado real
        assert conv_repo.append_message.await_count == 2
        reply_msg = conv_repo.append_message.await_args_list[1][0][0]
        assert reply_msg.role == "assistant"
        assert reply_msg.content == REPLY
        assert reply_msg.status == send_status
        assert reply_msg.conversation_id == CONV_UUID

    def test_skipped_status_is_never_reported_as_sent(
        self, run_task, conv_repo: AsyncMock
    ) -> None:
        """Meta sin configurar → status 'skipped', nunca 'sent' ficticio."""
        result, _, _ = run_task(send_status="skipped")

        assert result["status"] == "skipped"
        reply_msg = conv_repo.append_message.await_args_list[1][0][0]
        assert reply_msg.status != "sent"


# ======================================================================
# 4. Resiliencia: la persistencia no bloquea la respuesta
# ======================================================================


class TestPersistenceResilience:
    def test_db_failure_does_not_block_reply(
        self, run_task, conv_repo: AsyncMock
    ) -> None:
        conv_repo.find_by_client_and_phone.side_effect = DomainError("DB down")

        result, run_agent_mock, send_mock = run_task(send_status="sent")

        # Responde igualmente, sin memoria
        assert result["status"] == "sent"
        assert result["conversation_id"] is None
        assert run_agent_mock.await_args.kwargs["history"] == []
        send_mock.assert_called_once()
        # No intenta guardar la respuesta (no hay conversación)
        conv_repo.append_message.assert_not_awaited()

    def test_agent_not_found_returns_error(self, conv_repo: AsyncMock) -> None:
        # Caso especial: _load_agent_sync devuelve None
        with (
            patch.object(tasks_module, "_load_agent_sync", return_value=None),
            patch.object(
                tasks_module, "_get_conversation_repo", return_value=conv_repo
            ),
        ):
            result = tasks_module.process_whatsapp_message(
                client_id=str(CLIENT_UUID),
                phone=PHONE,
                message=INCOMING,
                agent_id=str(AGENT_UUID),
            )

        assert result == {"status": "error", "reason": "agent_not_found"}
        conv_repo.find_by_client_and_phone.assert_not_awaited()


# ======================================================================
# 5. _send_whatsapp_message — estados de envío
# ======================================================================


class TestSendWhatsAppMessage:
    """Fase 3: _send_whatsapp_message ahora resuelve credenciales por
    client_id (con fallback a env) antes de delegar en WhatsAppSender.
    """

    def _settings(self, *, token: str = "tok", phone_id: str = "12345"):
        return SimpleNamespace(
            whatsapp_access_token=token,
            whatsapp_phone_number_id=phone_id,
            whatsapp_api_version="v22.0",
        )

    def test_returns_skipped_when_no_credentials_anywhere(self) -> None:
        settings = self._settings(token="", phone_id="")

        with patch.object(
            tasks_module,
            "_resolve_whatsapp_credentials_sync",
            return_value=("", "", False),
        ):
            status = tasks_module._send_whatsapp_message(
                str(CLIENT_UUID), PHONE, "Hola", settings
            )

        assert status == "skipped"

    def test_returns_sent_on_success_with_client_credentials(self) -> None:
        settings = self._settings()
        resp = MagicMock(is_success=True)

        with (
            patch.object(
                tasks_module,
                "_resolve_whatsapp_credentials_sync",
                return_value=("client-pnid", "client-token", True),
            ),
            patch("httpx.post", return_value=resp) as post_mock,
        ):
            status = tasks_module._send_whatsapp_message(
                str(CLIENT_UUID), PHONE, "Hola", settings
            )

        assert status == "sent"
        url = post_mock.call_args[0][0]
        assert "graph.facebook.com" in url
        assert "client-pnid" in url
        headers = post_mock.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer client-token"

    def test_returns_failed_on_http_error(self) -> None:
        settings = self._settings()
        resp = MagicMock(is_success=False, status_code=401)
        resp.json.return_value = {"error": {"code": 190}}

        with (
            patch.object(
                tasks_module,
                "_resolve_whatsapp_credentials_sync",
                return_value=("pnid", "bad-token", True),
            ),
            patch("httpx.post", return_value=resp),
        ):
            status = tasks_module._send_whatsapp_message(
                str(CLIENT_UUID), PHONE, "Hola", settings
            )

        assert status == "failed"

    def test_returns_failed_on_exception(self) -> None:
        settings = self._settings()

        with (
            patch.object(
                tasks_module,
                "_resolve_whatsapp_credentials_sync",
                return_value=("pnid", "token", True),
            ),
            patch("httpx.post", side_effect=ConnectionError("no network")),
        ):
            status = tasks_module._send_whatsapp_message(
                str(CLIENT_UUID), PHONE, "Hola", settings
            )

        assert status == "failed"


class TestResolveWhatsappCredentials:
    """Fase 3, tarea 3.2 — estrategia de fallback de credenciales."""

    def test_uses_client_credentials_when_available(self) -> None:
        settings = SimpleNamespace(
            whatsapp_access_token="global-token",
            whatsapp_phone_number_id="global-pnid",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )
        fake_creds = SimpleNamespace(
            phone_number_id="tenant-pnid",
            access_token="tenant-token",
            has_credentials=True,
        )
        fake_repo = MagicMock()
        fake_repo.get_whatsapp_credentials = AsyncMock(return_value=fake_creds)

        with (
            patch.object(tasks_module, "get_settings", return_value=settings),
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=fake_repo,
            ),
        ):
            phone_number_id, token, is_owned = tasks_module._resolve_whatsapp_credentials_sync(
                str(CLIENT_UUID)
            )

        assert phone_number_id == "tenant-pnid"
        assert token == "tenant-token"
        assert is_owned is True

    def test_falls_back_to_global_env_when_client_has_no_credentials(self) -> None:
        settings = SimpleNamespace(
            whatsapp_access_token="global-token",
            whatsapp_phone_number_id="global-pnid",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )
        fake_creds = SimpleNamespace(phone_number_id="", access_token="", has_credentials=False)
        fake_repo = MagicMock()
        fake_repo.get_whatsapp_credentials = AsyncMock(return_value=fake_creds)

        with (
            patch.object(tasks_module, "get_settings", return_value=settings),
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=fake_repo,
            ),
        ):
            phone_number_id, token, is_owned = tasks_module._resolve_whatsapp_credentials_sync(
                str(CLIENT_UUID)
            )

        assert phone_number_id == "global-pnid"
        assert token == "global-token"
        assert is_owned is False

    def test_returns_empty_when_no_credentials_anywhere(self) -> None:
        settings = SimpleNamespace(
            whatsapp_access_token="",
            whatsapp_phone_number_id="",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )
        fake_creds = SimpleNamespace(phone_number_id="", access_token="", has_credentials=False)
        fake_repo = MagicMock()
        fake_repo.get_whatsapp_credentials = AsyncMock(return_value=fake_creds)

        with (
            patch.object(tasks_module, "get_settings", return_value=settings),
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=fake_repo,
            ),
        ):
            phone_number_id, token, is_owned = tasks_module._resolve_whatsapp_credentials_sync(
                str(CLIENT_UUID)
            )

        assert phone_number_id == ""
        assert token == ""
        assert is_owned is False

    def test_repo_exception_falls_back_to_global_env(self) -> None:
        """Un error resolviendo credenciales del tenant no debe tumbar el envío."""
        settings = SimpleNamespace(
            whatsapp_access_token="global-token",
            whatsapp_phone_number_id="global-pnid",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )
        fake_repo = MagicMock()
        fake_repo.get_whatsapp_credentials = AsyncMock(side_effect=RuntimeError("db down"))

        with (
            patch.object(tasks_module, "get_settings", return_value=settings),
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=fake_repo,
            ),
        ):
            phone_number_id, token, is_owned = tasks_module._resolve_whatsapp_credentials_sync(
                str(CLIENT_UUID)
            )

        assert phone_number_id == "global-pnid"
        assert token == "global-token"
        assert is_owned is False
