"""Unit tests de WhatsAppAppointmentNotifier (adaptador de AppointmentNotificationPort)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.whatsapp.appointment_notifier import WhatsAppAppointmentNotifier
from app.infrastructure.whatsapp.sender import WhatsAppSendResult, WhatsAppSendStatus

CLIENT_ID = "11111111-1111-1111-1111-111111111111"


def _fake_repo(has_credentials: bool, phone_number_id: str = "", access_token: str = "") -> MagicMock:
    creds = SimpleNamespace(
        has_credentials=has_credentials,
        phone_number_id=phone_number_id,
        access_token=access_token,
    )
    repo = MagicMock()
    repo.get_whatsapp_credentials = AsyncMock(return_value=creds)
    return repo


class TestSendConfirmation:
    @pytest.mark.asyncio
    async def test_sends_with_client_credentials(self) -> None:
        repo = _fake_repo(True, phone_number_id="tenant-pnid", access_token="tenant-token")
        settings = SimpleNamespace(
            whatsapp_access_token="",
            whatsapp_phone_number_id="",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )

        sender = MagicMock()
        sender.send.return_value = WhatsAppSendResult(status=WhatsAppSendStatus.OK)
        notifier = WhatsAppAppointmentNotifier(sender=sender)

        with (
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=repo,
            ),
            patch(
                "app.infrastructure.config.settings.get_settings",
                return_value=settings,
            ),
        ):
            result = await notifier.send_confirmation(
                client_id=CLIENT_ID,
                contact_phone="573000000000",
                business_name="Peluquería Ana",
                starts_at_label="lunes 7 de enero a las 10:00",
            )

        assert result is True
        sender.send.assert_called_once()
        call_kwargs = sender.send.call_args
        assert call_kwargs[0][0] == "tenant-pnid"
        assert call_kwargs[0][1] == "tenant-token"

    @pytest.mark.asyncio
    async def test_falls_back_to_global_credentials(self) -> None:
        repo = _fake_repo(False)
        settings = SimpleNamespace(
            whatsapp_access_token="global-token",
            whatsapp_phone_number_id="global-pnid",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )

        sender = MagicMock()
        sender.send.return_value = WhatsAppSendResult(status=WhatsAppSendStatus.OK)
        notifier = WhatsAppAppointmentNotifier(sender=sender)

        with (
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=repo,
            ),
            patch(
                "app.infrastructure.config.settings.get_settings",
                return_value=settings,
            ),
        ):
            result = await notifier.send_confirmation(
                client_id=CLIENT_ID,
                contact_phone="573000000000",
                business_name="Peluquería Ana",
                starts_at_label="lunes 7 de enero a las 10:00",
            )

        assert result is True
        call_kwargs = sender.send.call_args
        assert call_kwargs[0][0] == "global-pnid"
        assert call_kwargs[0][1] == "global-token"

    @pytest.mark.asyncio
    async def test_returns_false_without_any_credentials(self) -> None:
        repo = _fake_repo(False)
        settings = SimpleNamespace(
            whatsapp_access_token="",
            whatsapp_phone_number_id="",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )
        sender = MagicMock()
        notifier = WhatsAppAppointmentNotifier(sender=sender)

        with (
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=repo,
            ),
            patch(
                "app.infrastructure.config.settings.get_settings",
                return_value=settings,
            ),
        ):
            result = await notifier.send_confirmation(
                client_id=CLIENT_ID,
                contact_phone="573000000000",
                business_name="Peluquería Ana",
                starts_at_label="lunes 7 de enero a las 10:00",
            )

        assert result is False
        sender.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_false_when_sender_fails(self) -> None:
        repo = _fake_repo(True, phone_number_id="pnid", access_token="token")
        settings = SimpleNamespace(
            whatsapp_access_token="",
            whatsapp_phone_number_id="",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )
        sender = MagicMock()
        sender.send.return_value = WhatsAppSendResult(
            status=WhatsAppSendStatus.TOKEN_INVALID, detail="expired"
        )
        notifier = WhatsAppAppointmentNotifier(sender=sender)

        with (
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=repo,
            ),
            patch(
                "app.infrastructure.config.settings.get_settings",
                return_value=settings,
            ),
        ):
            result = await notifier.send_confirmation(
                client_id=CLIENT_ID,
                contact_phone="573000000000",
                business_name="Peluquería Ana",
                starts_at_label="lunes 7 de enero a las 10:00",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_never_raises_when_credentials_resolution_fails(self) -> None:
        repo = MagicMock()
        repo.get_whatsapp_credentials = AsyncMock(side_effect=RuntimeError("db down"))
        settings = SimpleNamespace(
            whatsapp_access_token="",
            whatsapp_phone_number_id="",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )
        sender = MagicMock()
        notifier = WhatsAppAppointmentNotifier(sender=sender)

        with (
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=repo,
            ),
            patch(
                "app.infrastructure.config.settings.get_settings",
                return_value=settings,
            ),
        ):
            result = await notifier.send_confirmation(
                client_id=CLIENT_ID,
                contact_phone="573000000000",
                business_name="Peluquería Ana",
                starts_at_label="lunes 7 de enero a las 10:00",
            )

        assert result is False
        sender.send.assert_not_called()


class TestSendTeamAlert:
    @pytest.mark.asyncio
    async def test_skips_when_team_phone_empty(self) -> None:
        settings = SimpleNamespace(
            team_notify_whatsapp="",
            whatsapp_access_token="tok",
            whatsapp_phone_number_id="pnid",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
        )
        sender = MagicMock()
        notifier = WhatsAppAppointmentNotifier(sender=sender)

        with patch(
            "app.infrastructure.config.settings.get_settings",
            return_value=settings,
        ):
            result = await notifier.send_team_alert(
                client_id=CLIENT_ID,
                contact_phone="+34600111222",
                contact_name="Lead",
                business_name="Orinoco Studios",
                starts_at_label="jueves 10:00",
                notes="chatbot",
            )

        assert result is False
        sender.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_alert_to_team_phone(self) -> None:
        repo = _fake_repo(True, phone_number_id="tenant-pnid", access_token="tenant-token")
        settings = SimpleNamespace(
            team_notify_whatsapp="+34602438307",
            whatsapp_access_token="",
            whatsapp_phone_number_id="",
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-service-key",
            whatsapp_provider="ycloud",
            ycloud_api_key="k",
            ycloud_from_number="+34682743315",
        )
        sender = MagicMock()
        sender.send.return_value = WhatsAppSendResult(status=WhatsAppSendStatus.OK)
        notifier = WhatsAppAppointmentNotifier(sender=sender)

        with (
            patch(
                "app.infrastructure.persistence.client_repository.SupabaseClientRepository",
                return_value=repo,
            ),
            patch(
                "app.infrastructure.config.settings.get_settings",
                return_value=settings,
            ),
        ):
            result = await notifier.send_team_alert(
                client_id=CLIENT_ID,
                contact_phone="+34600111222",
                contact_name="Lead Acme",
                business_name="Orinoco Studios",
                starts_at_label="jueves 10:00",
                notes="quiere chatbot",
            )

        assert result is True
        sender.send.assert_called_once()
        args = sender.send.call_args.args
        assert args[0] == "tenant-pnid"
        assert args[1] == "tenant-token"
        assert args[2] == "+34602438307"
        assert "Lead Acme" in args[3]
        assert "quiere chatbot" in args[3]
        assert "Orinoco" in args[3]
