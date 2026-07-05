"""Unit tests de WhatsAppSender — categorización de errores de Meta Graph API.

httpx se mockea con unittest.mock (no se requiere pytest-httpx real, aunque
es compatible si está instalado).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.whatsapp.sender import (
    WhatsAppSendStatus,
    WhatsAppSender,
    categorize_meta_error,
)


def _mock_response(status_code: int, json_body: dict | None = None, is_success: bool = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = is_success if is_success is not None else (200 <= status_code < 300)
    resp.json.return_value = json_body or {}
    resp.text = str(json_body or {})
    return resp


class TestCategorizeMetaError:
    def test_token_expired_code_190(self) -> None:
        result = categorize_meta_error(401, {"error": {"code": 190}})
        assert result == WhatsAppSendStatus.TOKEN_INVALID

    def test_rate_limit_code(self) -> None:
        result = categorize_meta_error(429, {"error": {"code": 130429}})
        assert result == WhatsAppSendStatus.RATE_LIMITED

    def test_invalid_number_code(self) -> None:
        result = categorize_meta_error(400, {"error": {"code": 131026}})
        assert result == WhatsAppSendStatus.NUMBER_INVALID

    def test_http_401_without_known_code_defaults_to_token_invalid(self) -> None:
        result = categorize_meta_error(401, {})
        assert result == WhatsAppSendStatus.TOKEN_INVALID

    def test_http_429_without_known_code_defaults_to_rate_limited(self) -> None:
        result = categorize_meta_error(429, {})
        assert result == WhatsAppSendStatus.RATE_LIMITED

    def test_http_400_without_known_code_defaults_to_number_invalid(self) -> None:
        result = categorize_meta_error(400, {})
        assert result == WhatsAppSendStatus.NUMBER_INVALID

    def test_unrecognized_error_is_unknown(self) -> None:
        result = categorize_meta_error(500, {"error": {"code": 999999}})
        assert result == WhatsAppSendStatus.UNKNOWN_ERROR

    def test_non_dict_body_does_not_crash(self) -> None:
        result = categorize_meta_error(500, "internal server error")
        assert result == WhatsAppSendStatus.UNKNOWN_ERROR


class TestWhatsAppSenderSend:
    def test_successful_send_returns_ok(self) -> None:
        sender = WhatsAppSender()
        with patch("httpx.post", return_value=_mock_response(200, {"messages": [{"id": "wamid.1"}]})):
            result = sender.send("PNID", "TOKEN", "5730000000", "hola")

        assert result.ok is True
        assert result.status == WhatsAppSendStatus.OK

    def test_token_invalid_maps_correctly(self) -> None:
        sender = WhatsAppSender()
        body = {"error": {"code": 190, "message": "Error validating access token"}}
        with patch("httpx.post", return_value=_mock_response(401, body)):
            result = sender.send("PNID", "BAD_TOKEN", "5730000000", "hola")

        assert result.ok is False
        assert result.status == WhatsAppSendStatus.TOKEN_INVALID

    def test_rate_limited_maps_correctly(self) -> None:
        sender = WhatsAppSender()
        body = {"error": {"code": 130429, "message": "Rate limit hit"}}
        with patch("httpx.post", return_value=_mock_response(429, body)):
            result = sender.send("PNID", "TOKEN", "5730000000", "hola")

        assert result.ok is False
        assert result.status == WhatsAppSendStatus.RATE_LIMITED

    def test_number_invalid_maps_correctly(self) -> None:
        sender = WhatsAppSender()
        body = {"error": {"code": 131026, "message": "Recipient not on WhatsApp"}}
        with patch("httpx.post", return_value=_mock_response(400, body)):
            result = sender.send("PNID", "TOKEN", "0000000000", "hola")

        assert result.ok is False
        assert result.status == WhatsAppSendStatus.NUMBER_INVALID

    def test_unparseable_json_body_falls_back_to_text(self) -> None:
        sender = WhatsAppSender()
        resp = _mock_response(500, is_success=False)
        resp.json.side_effect = ValueError("not json")
        resp.text = "<html>Internal Server Error</html>"
        with patch("httpx.post", return_value=resp):
            result = sender.send("PNID", "TOKEN", "5730000000", "hola")

        assert result.ok is False
        assert result.status == WhatsAppSendStatus.UNKNOWN_ERROR

    def test_network_timeout_returns_unknown_error(self) -> None:
        import httpx

        sender = WhatsAppSender()
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            result = sender.send("PNID", "TOKEN", "5730000000", "hola")

        assert result.ok is False
        assert result.status == WhatsAppSendStatus.UNKNOWN_ERROR

    def test_to_legacy_status_ok(self) -> None:
        sender = WhatsAppSender()
        with patch("httpx.post", return_value=_mock_response(200)):
            result = sender.send("PNID", "TOKEN", "5730000000", "hola")
        assert result.to_legacy_status() == "sent"

    def test_to_legacy_status_failed(self) -> None:
        sender = WhatsAppSender()
        with patch("httpx.post", return_value=_mock_response(401, {"error": {"code": 190}})):
            result = sender.send("PNID", "TOKEN", "5730000000", "hola")
        assert result.to_legacy_status() == "failed"
