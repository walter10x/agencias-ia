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
        settings = SimpleNamespace(whatsapp_access_token="", whatsapp_phone_number_id="")

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
            whatsapp_access_token="global-token", whatsapp_phone_number_id="global-pnid"
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
        settings = SimpleNamespace(whatsapp_access_token="", whatsapp_phone_number_id="")
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
        settings = SimpleNamespace(whatsapp_access_token="", whatsapp_phone_number_id="")
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
        settings = SimpleNamespace(whatsapp_access_token="", whatsapp_phone_number_id="")
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
