"""Unit tests de las tools nativas de agenda del agente IA.

Cubre:
- agent_tools_to_openai_format: schemas tipados para las tools de agenda
  y schema genérico para el resto.
- execute_tool: dispatcher local que invoca los use cases con el client_id
  del contexto (sin red, con repos in-memory).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.domain.agent.entity import AgentTool
from app.domain.appointment.entity import Appointment
from app.infrastructure.ai.tools import (
    AGENDA_TOOLS,
    agent_tools_to_openai_format,
    execute_tool,
)
from tests.unit.appointment_fakes import (
    FakeAppointmentRepository,
    FakeScheduleRepository,
)

CLIENT_ID = str(uuid4())
CONTEXT = {"id": CLIENT_ID}

# Lunes 2030-01-07 (futuro estable, dentro del horario por defecto 09-18 UTC)
MONDAY_10 = datetime(2030, 1, 7, 10, 0, tzinfo=timezone.utc)


def _make_fake_notifier(sent: bool = True) -> MagicMock:
    notifier = MagicMock()
    notifier.send_confirmation = AsyncMock(return_value=sent)
    return notifier


def _make_fake_client_repo(name: str = "Peluquería Ana") -> MagicMock:
    client = MagicMock()
    client.name = name
    repo = MagicMock()
    repo.find_by_id = AsyncMock(return_value=client)
    return repo


def _patch_repos(repo=None, schedule_repo=None, client_repo=None, notifier=None):
    repo = repo if repo is not None else FakeAppointmentRepository()
    schedule_repo = schedule_repo or FakeScheduleRepository()
    client_repo = client_repo if client_repo is not None else _make_fake_client_repo()
    notifier = notifier if notifier is not None else _make_fake_notifier()
    return repo, schedule_repo, patch.multiple(
        "app.infrastructure.ai.tools",
        _build_appointment_repo=lambda: repo,
        _build_schedule_repo=lambda: schedule_repo,
        _build_client_repo=lambda: client_repo,
        _build_appointment_notifier=lambda: notifier,
    )


async def _seed(repo, **overrides) -> Appointment:
    defaults = dict(
        client_id=UUID(CLIENT_ID),
        contact_phone="584121234567",
        contact_name="Ana",
        starts_at=MONDAY_10,
        ends_at=MONDAY_10 + timedelta(minutes=30),
    )
    defaults.update(overrides)
    appt = Appointment(**defaults)
    await repo.save(appt)
    return appt


# ============================================================================
# agent_tools_to_openai_format — schemas tipados
# ============================================================================


class TestOpenAIFormat:
    def test_consultar_disponibilidad_schema(self) -> None:
        tools = [AgentTool(name="consultar_disponibilidad", description="Consulta slots")]
        result = agent_tools_to_openai_format(tools)

        fn = result[0]["function"]
        assert fn["name"] == "consultar_disponibilidad"
        params = fn["parameters"]
        assert params["required"] == ["fecha"]
        assert params["properties"]["fecha"]["type"] == "string"
        assert "input" not in params["properties"]

    def test_agendar_cita_schema(self) -> None:
        tools = [AgentTool(name="agendar_cita", description="Agenda una cita")]
        params = agent_tools_to_openai_format(tools)[0]["function"]["parameters"]

        assert set(params["properties"]) == {"fecha_hora", "nombre", "telefono", "notas"}
        assert params["required"] == ["fecha_hora", "nombre"]
        assert all(p["type"] == "string" for p in params["properties"].values())

    def test_cancelar_cita_schema(self) -> None:
        tools = [AgentTool(name="cancelar_cita", description="Cancela una cita")]
        params = agent_tools_to_openai_format(tools)[0]["function"]["parameters"]

        assert params["required"] == ["referencia"]
        assert "referencia" in params["properties"]

    def test_non_agenda_tool_keeps_generic_schema(self) -> None:
        tools = [AgentTool(name="consultar_precios", description="Precios")]
        result = agent_tools_to_openai_format(tools)

        fn = result[0]["function"]
        assert fn["name"] == "consultar_precios"
        assert fn["parameters"]["required"] == ["input"]
        assert "input" in fn["parameters"]["properties"]

    def test_openai_envelope_format(self) -> None:
        tools = [AgentTool(name="agendar_cita", description="Agenda")]
        result = agent_tools_to_openai_format(tools)
        assert result[0]["type"] == "function"
        assert result[0]["function"]["description"] == "Agenda"


# ============================================================================
# execute_tool — dispatcher
# ============================================================================


class TestExecuteToolDispatch:
    @pytest.mark.asyncio
    async def test_non_agenda_tool_returns_not_configured(self) -> None:
        result = await execute_tool("consultar_precios", {"input": "corte"}, CONTEXT)
        assert "no está configurada" in result
        assert "consultar_precios" in result

    @pytest.mark.asyncio
    async def test_agenda_tool_without_client_context_returns_error(self) -> None:
        result = await execute_tool("agendar_cita", {"fecha_hora": "2030-01-07T10:00"}, {})
        assert "Error interno" in result

    def test_agenda_tools_registry(self) -> None:
        assert AGENDA_TOOLS == {
            "consultar_disponibilidad",
            "agendar_cita",
            "cancelar_cita",
        }


class TestConsultarDisponibilidad:
    @pytest.mark.asyncio
    async def test_returns_free_slots(self) -> None:
        repo, schedule_repo, patcher = _patch_repos()
        with patcher:
            result = await execute_tool(
                "consultar_disponibilidad", {"fecha": "2030-01-07"}, CONTEXT
            )

        assert "2030-01-07" in result
        assert "09:00" in result
        assert schedule_repo.calls == [CLIENT_ID]

    @pytest.mark.asyncio
    async def test_booked_slot_not_offered(self) -> None:
        repo, _, patcher = _patch_repos()
        with patcher:
            await _seed(repo)
            result = await execute_tool(
                "consultar_disponibilidad", {"fecha": "2030-01-07"}, CONTEXT
            )

        assert "10:00" not in result
        assert "10:30" in result

    @pytest.mark.asyncio
    async def test_closed_day_reports_no_availability(self) -> None:
        _, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool(
                "consultar_disponibilidad", {"fecha": "2030-01-06"}, CONTEXT  # domingo
            )

        assert "No hay horarios disponibles" in result

    @pytest.mark.asyncio
    async def test_missing_fecha_reports_error(self) -> None:
        _, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool("consultar_disponibilidad", {}, CONTEXT)

        assert "fecha" in result

    @pytest.mark.asyncio
    async def test_accepts_json_string_arguments(self) -> None:
        _, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool(
                "consultar_disponibilidad", '{"fecha": "2030-01-07"}', CONTEXT
            )

        assert "09:00" in result


class TestAgendarCita:
    @pytest.mark.asyncio
    async def test_creates_appointment_scoped_to_client(self) -> None:
        repo, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool(
                "agendar_cita",
                {
                    "fecha_hora": "2030-01-07T10:00",
                    "nombre": "Ana",
                    "telefono": "584121234567",
                    "notas": "corte de pelo",
                },
                CONTEXT,
            )

        assert "agendada" in result.lower()
        assert len(repo.items) == 1
        saved = next(iter(repo.items.values()))
        assert str(saved.client_id) == CLIENT_ID
        assert saved.contact_phone == "584121234567"
        assert saved.contact_name == "Ana"
        assert saved.notes == "corte de pelo"
        # La referencia (ID) va en la respuesta para poder cancelar después
        assert str(saved.id) in result

    @pytest.mark.asyncio
    async def test_uses_phone_from_context_when_missing(self) -> None:
        repo, _, patcher = _patch_repos()
        context = {"id": CLIENT_ID, "contact_phone": "584129999999"}
        with patcher:
            result = await execute_tool(
                "agendar_cita",
                {"fecha_hora": "2030-01-07T10:00", "nombre": "Ana"},
                context,
            )

        assert "agendada" in result.lower()
        saved = next(iter(repo.items.values()))
        assert saved.contact_phone == "584129999999"

    @pytest.mark.asyncio
    async def test_no_phone_anywhere_asks_for_it(self) -> None:
        repo, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool(
                "agendar_cita",
                {"fecha_hora": "2030-01-07T10:00", "nombre": "Ana"},
                CONTEXT,
            )

        assert "teléfono" in result
        assert repo.items == {}

    @pytest.mark.asyncio
    async def test_occupied_slot_reports_conflict(self) -> None:
        repo, _, patcher = _patch_repos()
        with patcher:
            await _seed(repo)
            result = await execute_tool(
                "agendar_cita",
                {
                    "fecha_hora": "2030-01-07T10:15",
                    "nombre": "Luis",
                    "telefono": "584120000000",
                },
                CONTEXT,
            )

        assert "No se pudo completar la operación" in result
        assert len(repo.items) == 1  # no se creó una segunda cita

    @pytest.mark.asyncio
    async def test_outside_hours_reports_error(self) -> None:
        repo, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool(
                "agendar_cita",
                {
                    "fecha_hora": "2030-01-07T22:00",
                    "nombre": "Luis",
                    "telefono": "584120000000",
                },
                CONTEXT,
            )

        assert "No se pudo completar la operación" in result
        assert repo.items == {}

    @pytest.mark.asyncio
    async def test_unparseable_datetime_reports_error(self) -> None:
        _, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool(
                "agendar_cita",
                {"fecha_hora": "mañana 10am", "nombre": "Ana", "telefono": "58412"},
                CONTEXT,
            )

        assert "No se pudo completar la operación" in result


class TestCancelarCita:
    @pytest.mark.asyncio
    async def test_cancels_by_appointment_id(self) -> None:
        repo, _, patcher = _patch_repos()
        with patcher:
            appt = await _seed(repo)
            result = await execute_tool(
                "cancelar_cita", {"referencia": str(appt.id)}, CONTEXT
            )

        assert "cancelada" in result
        assert repo.items[str(appt.id)].status.value == "cancelled"

    @pytest.mark.asyncio
    async def test_cancels_next_appointment_by_phone(self) -> None:
        repo, _, patcher = _patch_repos()
        with patcher:
            appt = await _seed(repo)
            result = await execute_tool(
                "cancelar_cita", {"referencia": "584121234567"}, CONTEXT
            )

        assert "cancelada" in result
        assert repo.items[str(appt.id)].status.value == "cancelled"

    @pytest.mark.asyncio
    async def test_unknown_phone_reports_not_found(self) -> None:
        _, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool(
                "cancelar_cita", {"referencia": "584100000000"}, CONTEXT
            )

        assert "No se encontró" in result

    @pytest.mark.asyncio
    async def test_cannot_cancel_appointment_of_other_tenant(self) -> None:
        """Aislamiento: una referencia de otro tenant no se puede cancelar."""
        repo, _, patcher = _patch_repos()
        with patcher:
            other = await _seed(repo, client_id=uuid4())
            result = await execute_tool(
                "cancelar_cita", {"referencia": str(other.id)}, CONTEXT
            )

        assert "No se encontró" in result
        assert repo.items[str(other.id)].status.value == "pending"

    @pytest.mark.asyncio
    async def test_missing_referencia_reports_error(self) -> None:
        _, _, patcher = _patch_repos()
        with patcher:
            result = await execute_tool("cancelar_cita", {}, CONTEXT)

        assert "referencia" in result


# ============================================================================
# Confirmación de cita por WhatsApp (Fase 2, tarea 2.6)
# ============================================================================


class TestAppointmentConfirmationNotification:
    """La tool agendar_cita debe notificar por WhatsApp tras crear la cita.

    Contrato best-effort: un fallo de notificación NUNCA debe impedir que
    la cita se cree ni que la tool devuelva su mensaje de éxito habitual.
    """

    @pytest.mark.asyncio
    async def test_sends_confirmation_after_creating_appointment(self) -> None:
        notifier = _make_fake_notifier(sent=True)
        client_repo = _make_fake_client_repo(name="Peluquería Ana")
        repo, _, patcher = _patch_repos(client_repo=client_repo, notifier=notifier)

        with patcher:
            await execute_tool(
                "agendar_cita",
                {
                    "fecha_hora": "2030-01-07T10:00",
                    "nombre": "Ana",
                    "telefono": "584121234567",
                },
                CONTEXT,
            )

        notifier.send_confirmation.assert_awaited_once()
        call_kwargs = notifier.send_confirmation.await_args.kwargs
        assert call_kwargs["client_id"] == CLIENT_ID
        assert call_kwargs["contact_phone"] == "584121234567"
        assert call_kwargs["business_name"] == "Peluquería Ana"
        assert "lunes" in call_kwargs["starts_at_label"]
        assert "10:00" in call_kwargs["starts_at_label"]

    @pytest.mark.asyncio
    async def test_appointment_still_created_when_notification_fails(self) -> None:
        """Best-effort: notifier retorna False → la cita ya está creada igual."""
        notifier = _make_fake_notifier(sent=False)
        repo, _, patcher = _patch_repos(notifier=notifier)

        with patcher:
            result = await execute_tool(
                "agendar_cita",
                {
                    "fecha_hora": "2030-01-07T10:00",
                    "nombre": "Ana",
                    "telefono": "584121234567",
                },
                CONTEXT,
            )

        assert "agendada" in result.lower()
        assert len(repo.items) == 1

    @pytest.mark.asyncio
    async def test_appointment_still_created_when_notifier_raises(self) -> None:
        """Best-effort: una excepción del notifier no debe propagar ni deshacer la cita."""
        notifier = MagicMock()
        notifier.send_confirmation = AsyncMock(side_effect=RuntimeError("network down"))
        repo, _, patcher = _patch_repos(notifier=notifier)

        with patcher:
            result = await execute_tool(
                "agendar_cita",
                {
                    "fecha_hora": "2030-01-07T10:00",
                    "nombre": "Ana",
                    "telefono": "584121234567",
                },
                CONTEXT,
            )

        assert "agendada" in result.lower()
        assert len(repo.items) == 1

    @pytest.mark.asyncio
    async def test_appointment_still_created_when_client_repo_raises(self) -> None:
        """Best-effort: fallo buscando el nombre del negocio no impide la cita."""
        client_repo = MagicMock()
        client_repo.find_by_id = AsyncMock(side_effect=RuntimeError("db down"))
        repo, _, patcher = _patch_repos(client_repo=client_repo)

        with patcher:
            result = await execute_tool(
                "agendar_cita",
                {
                    "fecha_hora": "2030-01-07T10:00",
                    "nombre": "Ana",
                    "telefono": "584121234567",
                },
                CONTEXT,
            )

        assert "agendada" in result.lower()
        assert len(repo.items) == 1
