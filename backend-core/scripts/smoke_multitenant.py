"""Smoke runner stdlib-only para la Fase 3 (multi-tenant Meta) + tarea 2.6.

Ejercita, SIN pytest/httpx/pydantic instalados, la lógica pura de:
- Cifrado de credenciales (FernetCredentialsCipher — real si 'cryptography'
  está disponible, o el fallback base64 SOLO-DEV si no).
- Categorización de errores de Meta Graph API (WhatsAppSender, sin red:
  se instala un stub mínimo de httpx si el real no está disponible).
- Estrategia de fallback de credenciales por tenant (tasks.py).
- Routing multi-tenant del webhook entrante por phone_number_id, con
  repos fake (sin Supabase real).

Uso:
    python3 scripts/smoke_multitenant.py

NO sustituye a `pytest tests/` — es un smoke check para sandboxes sin red
(PyPI bloqueado). Los tests pytest equivalentes y más exhaustivos viven en
tests/unit/test_credentials_cipher.py, test_whatsapp_sender.py,
test_process_whatsapp_task.py, test_whatsapp_multitenant_routing.py,
test_appointment_notifier.py, test_appointment_tools.py y
test_admin_use_cases.py.
"""

from __future__ import annotations

import asyncio
import sys
import traceback
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_FAILURES: list[tuple[str, str]] = []
_PASSED = 0


def _install_dependency_stubs() -> None:
    """Stubs mínimos para libs externas no instalables en este sandbox."""

    def _try(name: str) -> bool:
        try:
            __import__(name)
            return True
        except ImportError:
            return False

    if not _try("httpx"):
        mod = types.ModuleType("httpx")

        class HTTPError(Exception):
            pass

        class TimeoutException(HTTPError):
            pass

        class ConnectError(HTTPError):
            pass

        def post(*args, **kwargs):  # pragma: no cover — sobreescrito por tests via patch
            raise RuntimeError("httpx.post stub called without patching — sandbox sin red")

        mod.HTTPError = HTTPError
        mod.TimeoutException = TimeoutException
        mod.ConnectError = ConnectError
        mod.post = post
        sys.modules["httpx"] = mod

    if not _try("pydantic"):
        mod = types.ModuleType("pydantic")

        class _FieldInfo:
            def __init__(self, default=None, default_factory=None, **kwargs):
                self.default = default
                self.default_factory = default_factory
                self.alias = kwargs.get("alias")
                self.pattern = kwargs.get("pattern")

        def Field(default=None, **kwargs):
            if "default_factory" in kwargs:
                return _FieldInfo(default_factory=kwargs.pop("default_factory"), **kwargs)
            return _FieldInfo(default=default, **kwargs)

        def field_validator(*args, **kwargs):
            def decorator(fn):
                return classmethod(fn) if not isinstance(fn, classmethod) else fn

            return decorator

        def model_validator(*args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

        class _ModelMeta(type):
            def __new__(mcs, name, bases, namespace):
                annotations = namespace.get("__annotations__", {})
                namespace["_field_defaults"] = {
                    k: namespace.get(k) for k in annotations if k in namespace
                }
                return super().__new__(mcs, name, bases, namespace)

        class BaseModel(metaclass=_ModelMeta):
            model_config: dict = {}

            def __init__(self, **data):
                annotations = {}
                for klass in reversed(type(self).__mro__):
                    annotations.update(getattr(klass, "__annotations__", {}))

                for field_name, default in getattr(type(self), "_field_defaults", {}).items():
                    value = data.get(field_name, None)
                    if value is None:
                        if isinstance(default, _FieldInfo):
                            if default.default_factory is not None:
                                value = default.default_factory()
                            else:
                                value = default.default
                        else:
                            value = default
                    setattr(self, field_name, value)

                for key, value in data.items():
                    if not hasattr(self, key):
                        setattr(self, key, value)

                for field_name in annotations:
                    if not hasattr(self, field_name):
                        setattr(self, field_name, None)

            @classmethod
            def model_validate(cls, data: dict):
                return cls(**data)

        mod.BaseModel = BaseModel
        mod.Field = Field
        mod.field_validator = field_validator
        mod.model_validator = model_validator
        sys.modules["pydantic"] = mod

    if not _try("pydantic_settings"):
        mod = types.ModuleType("pydantic_settings")

        class BaseSettings:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        mod.BaseSettings = BaseSettings
        mod.SettingsConfigDict = dict
        sys.modules["pydantic_settings"] = mod

    if not _try("openai"):
        mod = types.ModuleType("openai")

        class AsyncOpenAI:
            def __init__(self, *args, **kwargs):
                pass

        mod.AsyncOpenAI = AsyncOpenAI
        sys.modules["openai"] = mod

    if not _try("celery"):
        mod = types.ModuleType("celery")

        class Celery:
            def __init__(self, *args, **kwargs):
                self.conf = types.SimpleNamespace(update=lambda **kw: None)

            def send_task(self, *args, **kwargs):  # pragma: no cover — overridden by patch
                raise RuntimeError("celery stub: send_task llamado sin patchear")

            def task(self, *args, **kwargs):
                def decorator(fn):
                    return fn

                return decorator

        mod.Celery = Celery
        sys.modules["celery"] = mod

        utils_mod = types.ModuleType("celery.utils")
        log_mod = types.ModuleType("celery.utils.log")

        def get_task_logger(name):
            import logging

            return logging.getLogger(name)

        log_mod.get_task_logger = get_task_logger
        utils_mod.log = log_mod
        sys.modules["celery.utils"] = utils_mod
        sys.modules["celery.utils.log"] = log_mod

    if not _try("langgraph.graph"):
        pkg = types.ModuleType("langgraph")
        graph = types.ModuleType("langgraph.graph")

        class StateGraph:
            def __init__(self, *args, **kwargs):
                pass

            def add_node(self, *a, **k):
                pass

            def add_edge(self, *a, **k):
                pass

            def add_conditional_edges(self, *a, **k):
                pass

            def set_entry_point(self, *a, **k):
                pass

            def compile(self):
                return self

        graph.StateGraph = StateGraph
        graph.END = "__end__"
        pkg.graph = graph
        sys.modules["langgraph"] = pkg
        sys.modules["langgraph.graph"] = graph


def check(name: str, condition: bool, detail: str = "") -> None:
    global _PASSED
    if condition:
        _PASSED += 1
    else:
        _FAILURES.append((name, detail or "assertion failed"))


def run_check(name: str, fn) -> None:
    """Ejecuta fn() (sync o coroutine) capturando cualquier excepción."""
    global _PASSED
    try:
        result = fn()
        if asyncio.iscoroutine(result):
            asyncio.run(result)
        _PASSED += 1
    except Exception:  # noqa: BLE001
        _FAILURES.append((name, traceback.format_exc()))


# ============================================================================
# 1. Cifrado de credenciales
# ============================================================================


def check_cipher_insecure_fallback_roundtrip() -> None:
    from app.infrastructure.security.credentials_cipher import FernetCredentialsCipher

    cipher = FernetCredentialsCipher(encryption_key="")
    assert cipher.is_insecure_fallback is True
    secret = "EAAB-example-meta-token"
    ciphertext = cipher.encrypt(secret)
    assert ciphertext != secret
    assert cipher.decrypt(ciphertext) == secret


def check_cipher_real_fernet_when_available() -> None:
    from app.infrastructure.security import credentials_cipher as mod
    from app.infrastructure.security.credentials_cipher import FernetCredentialsCipher

    if not mod._CRYPTOGRAPHY_AVAILABLE:
        return  # se documenta como pendiente en el reporte final

    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("ascii")
    cipher = FernetCredentialsCipher(encryption_key=key)
    assert cipher.is_insecure_fallback is False
    secret = "EAAB-example-meta-token"
    ciphertext = cipher.encrypt(secret)
    assert ciphertext != secret
    assert cipher.decrypt(ciphertext) == secret

    # Clave incorrecta no debe descifrar
    other_cipher = FernetCredentialsCipher(encryption_key=Fernet.generate_key().decode("ascii"))
    try:
        other_cipher.decrypt(ciphertext)
        raise AssertionError("decrypt con clave incorrecta debería fallar")
    except ValueError:
        pass


# ============================================================================
# 2. Categorización de errores del sender (WhatsAppSender)
# ============================================================================


def check_sender_categorizes_meta_errors() -> None:
    from app.infrastructure.whatsapp.sender import (
        WhatsAppSendStatus,
        categorize_meta_error,
    )

    assert categorize_meta_error(401, {"error": {"code": 190}}) == WhatsAppSendStatus.TOKEN_INVALID
    assert categorize_meta_error(429, {"error": {"code": 130429}}) == WhatsAppSendStatus.RATE_LIMITED
    assert categorize_meta_error(400, {"error": {"code": 131026}}) == WhatsAppSendStatus.NUMBER_INVALID
    assert categorize_meta_error(500, {"error": {"code": 999999}}) == WhatsAppSendStatus.UNKNOWN_ERROR
    assert categorize_meta_error(500, "not a dict") == WhatsAppSendStatus.UNKNOWN_ERROR


def check_sender_send_ok_and_error_paths() -> None:
    from app.infrastructure.whatsapp.sender import WhatsAppSender, WhatsAppSendStatus

    sender = WhatsAppSender()

    ok_resp = MagicMock(is_success=True)
    with patch("httpx.post", return_value=ok_resp):
        result = sender.send("PNID", "TOKEN", "5730000000", "hola")
    assert result.ok is True
    assert result.to_legacy_status() == "sent"

    err_resp = MagicMock(is_success=False, status_code=401)
    err_resp.json.return_value = {"error": {"code": 190}}
    with patch("httpx.post", return_value=err_resp):
        result = sender.send("PNID", "BAD", "5730000000", "hola")
    assert result.ok is False
    assert result.status == WhatsAppSendStatus.TOKEN_INVALID
    assert result.to_legacy_status() == "failed"


# ============================================================================
# 3. Fallback de credenciales por tenant (tasks.py)
# ============================================================================


def check_resolve_credentials_prefers_tenant_over_global() -> None:
    from types import SimpleNamespace

    from app.infrastructure.config import tasks as tasks_module

    settings = SimpleNamespace(
        whatsapp_access_token="global-token",
        whatsapp_phone_number_id="global-pnid",
        supabase_url="http://fake",
        supabase_service_key="fake-key",
    )
    fake_creds = SimpleNamespace(
        phone_number_id="tenant-pnid", access_token="tenant-token", has_credentials=True
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
        pnid, token, is_owned = tasks_module._resolve_whatsapp_credentials_sync("client-1")

    assert pnid == "tenant-pnid"
    assert token == "tenant-token"
    assert is_owned is True


def check_resolve_credentials_falls_back_to_global() -> None:
    from types import SimpleNamespace

    from app.infrastructure.config import tasks as tasks_module

    settings = SimpleNamespace(
        whatsapp_access_token="global-token",
        whatsapp_phone_number_id="global-pnid",
        supabase_url="http://fake",
        supabase_service_key="fake-key",
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
        pnid, token, is_owned = tasks_module._resolve_whatsapp_credentials_sync("client-1")

    assert pnid == "global-pnid"
    assert token == "global-token"
    assert is_owned is False


def check_resolve_credentials_none_anywhere_is_empty() -> None:
    from types import SimpleNamespace

    from app.infrastructure.config import tasks as tasks_module

    settings = SimpleNamespace(
        whatsapp_access_token="",
        whatsapp_phone_number_id="",
        supabase_url="http://fake",
        supabase_service_key="fake-key",
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
        pnid, token, is_owned = tasks_module._resolve_whatsapp_credentials_sync("client-1")

    assert pnid == "" and token == "" and is_owned is False


def check_send_whatsapp_message_skipped_without_any_credentials() -> None:
    from types import SimpleNamespace

    from app.infrastructure.config import tasks as tasks_module

    settings = SimpleNamespace(
        whatsapp_access_token="", whatsapp_phone_number_id="", whatsapp_api_version="v22.0"
    )

    with patch.object(
        tasks_module, "_resolve_whatsapp_credentials_sync", return_value=("", "", False)
    ):
        status = tasks_module._send_whatsapp_message("client-1", "5730000000", "hola", settings)

    assert status == "skipped"


# ============================================================================
# 4. Routing multi-tenant del webhook por phone_number_id (repos fake)
# ============================================================================


class _FakeClientRepoForRouting:
    def __init__(self, by_pnid: dict, by_whatsapp: dict) -> None:
        self._by_pnid = by_pnid
        self._by_whatsapp = by_whatsapp
        self.pnid_calls: list[str] = []
        self.whatsapp_calls: list[str] = []

    async def find_by_phone_number_id(self, phone_number_id: str):
        self.pnid_calls.append(phone_number_id)
        return self._by_pnid.get(phone_number_id)

    async def find_by_whatsapp(self, number: str):
        self.whatsapp_calls.append(number)
        return self._by_whatsapp.get(number)


class _FakeAgentRepoForRouting:
    def __init__(self, agent) -> None:
        self._agent = agent
        self.calls: list[str] = []

    async def find_active_by_client(self, client_id):
        self.calls.append(str(client_id))
        return [self._agent] if self._agent else []


def check_webhook_routes_by_phone_number_id() -> None:
    from uuid import uuid4

    from app.domain.agent.entity import Agent, AgentTool
    from app.domain.client.entity import Client
    from app.domain.shared.value_objects import BusinessType, ClientId, WhatsAppNumber
    from app.infrastructure.whatsapp.message_processor import process_whatsapp_message

    tenant_a_id = uuid4()
    tenant_b_id = uuid4()

    client_a = Client(
        name="Negocio A", business_type=BusinessType("otro"), whatsapp_number=WhatsAppNumber("573001111111")
    )
    object.__setattr__(client_a, "id", tenant_a_id)
    client_b = Client(
        name="Negocio B", business_type=BusinessType("otro"), whatsapp_number=WhatsAppNumber("573002222222")
    )
    object.__setattr__(client_b, "id", tenant_b_id)

    agent_a = Agent(
        id=uuid4(),
        client_id=ClientId(tenant_a_id),
        name="Agente A",
        personality="Eres un asistente amable y profesional. Diez caracteres minimo.",
        tools=[AgentTool(name="t1", description="d1", endpoint="https://n8n.example.com/t1")],
        knowledge_base_refs=[],
        is_active=True,
    )

    client_repo = _FakeClientRepoForRouting(
        by_pnid={"pnid-a": client_a, "pnid-b": client_b}, by_whatsapp={}
    )
    agent_repo = _FakeAgentRepoForRouting(agent_a)

    from app.infrastructure.config import celery_app as celery_module

    with patch.object(celery_module.celery_app, "send_task") as mock_send_task:
        mock_task = MagicMock()
        mock_task.id = "task-a"
        mock_send_task.return_value = mock_task

        result = asyncio.run(
            process_whatsapp_message(
                phone="573009999999",
                text="Hola",
                client_repo=client_repo,
                agent_repo=agent_repo,
                phone_number_id="pnid-a",
            )
        )

    assert result.status == "queued"
    assert client_repo.pnid_calls == ["pnid-a"]
    assert client_repo.whatsapp_calls == []  # no debió usar el fallback


def check_webhook_falls_back_when_pnid_not_found() -> None:
    from uuid import uuid4

    from app.domain.agent.entity import Agent, AgentTool
    from app.domain.client.entity import Client
    from app.domain.shared.value_objects import BusinessType, ClientId, WhatsAppNumber
    from app.infrastructure.whatsapp.message_processor import process_whatsapp_message

    tenant_id = uuid4()
    client_legacy = Client(
        name="Negocio Legacy", business_type=BusinessType("otro"), whatsapp_number=WhatsAppNumber("573003333333")
    )
    object.__setattr__(client_legacy, "id", tenant_id)

    agent = Agent(
        id=uuid4(),
        client_id=ClientId(tenant_id),
        name="Agente",
        personality="Eres un asistente amable y profesional. Diez caracteres minimo.",
        tools=[],
        knowledge_base_refs=[],
        is_active=True,
    )

    client_repo = _FakeClientRepoForRouting(
        by_pnid={}, by_whatsapp={"573003333333": client_legacy}
    )
    agent_repo = _FakeAgentRepoForRouting(agent)

    from app.infrastructure.config import celery_app as celery_module

    with patch.object(celery_module.celery_app, "send_task") as mock_send_task:
        mock_task = MagicMock()
        mock_task.id = "task-fallback"
        mock_send_task.return_value = mock_task

        result = asyncio.run(
            process_whatsapp_message(
                phone="573003333333",
                text="Hola",
                client_repo=client_repo,
                agent_repo=agent_repo,
                phone_number_id="unknown-pnid",
            )
        )

    assert result.status == "queued"
    assert client_repo.pnid_calls == ["unknown-pnid"]
    assert client_repo.whatsapp_calls == ["573003333333"]


# ============================================================================
# Runner
# ============================================================================


def main() -> int:
    _install_dependency_stubs()

    checks = [
        ("cipher.insecure_fallback_roundtrip", check_cipher_insecure_fallback_roundtrip),
        ("cipher.real_fernet_when_available", check_cipher_real_fernet_when_available),
        ("sender.categorizes_meta_errors", check_sender_categorizes_meta_errors),
        ("sender.send_ok_and_error_paths", check_sender_send_ok_and_error_paths),
        ("credentials.prefers_tenant_over_global", check_resolve_credentials_prefers_tenant_over_global),
        ("credentials.falls_back_to_global", check_resolve_credentials_falls_back_to_global),
        ("credentials.none_anywhere_is_empty", check_resolve_credentials_none_anywhere_is_empty),
        ("credentials.skipped_without_any", check_send_whatsapp_message_skipped_without_any_credentials),
        ("webhook.routes_by_phone_number_id", check_webhook_routes_by_phone_number_id),
        ("webhook.falls_back_when_pnid_not_found", check_webhook_falls_back_when_pnid_not_found),
    ]

    for name, fn in checks:
        run_check(name, fn)

    print(f"\n{_PASSED} passed, {len(_FAILURES)} failed")
    for name, tb in _FAILURES:
        print(f"\nFAILED {name}\n{tb}")
    return 1 if _FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
