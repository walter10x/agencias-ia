"""Unit tests de SupabaseAppointmentRepository — fully mocked (Fase 4).

Cubre los métodos nuevos de la Fase 4: find_reminder_candidates (query
cross-tenant amplia) y mark_reminder_sent (idempotencia vía
reminder_sent_at). El resto de métodos del repositorio ya estaban
cubiertos indirectamente por los use cases (test_appointment_use_cases.py
usa el fake in-memory); aquí se prueba el adaptador Supabase real.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.persistence.appointment_repository import (
    SupabaseAppointmentRepository,
)

NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def _make_mock_chain() -> MagicMock:
    """Mock que retorna self en cada método encadenado (mismo patrón que
    test_client_repository.py::_make_mock_chain)."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.neq.return_value = chain
    chain.gt.return_value = chain
    chain.gte.return_value = chain
    chain.lt.return_value = chain
    chain.lte.return_value = chain
    chain.in_.return_value = chain
    chain.is_.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.offset.return_value = chain
    chain.update.return_value = chain
    chain.execute.return_value = chain
    return chain


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    chain = _make_mock_chain()
    db.table.return_value = chain
    db._chain = chain
    return db


@pytest.fixture
def repo(mock_db: MagicMock) -> SupabaseAppointmentRepository:
    return SupabaseAppointmentRepository(mock_db)


def _make_row(
    *,
    id_: str | None = None,
    client_id: str | None = None,
    starts_at: datetime = NOW,
    status: str = "pending",
    reminder_sent_at: str | None = None,
) -> dict:
    return {
        "id": id_ or str(uuid4()),
        "client_id": client_id or str(uuid4()),
        "conversation_id": None,
        "contact_phone": "573000000000",
        "contact_name": "Ana",
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(minutes=30)).isoformat(),
        "status": status,
        "notes": "",
        "reminder_sent_at": reminder_sent_at,
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }


# ======================================================================
# find_reminder_candidates()
# ======================================================================


class TestFindReminderCandidates:
    @pytest.mark.asyncio
    async def test_returns_mapped_appointments(
        self, repo: SupabaseAppointmentRepository, mock_db: MagicMock
    ) -> None:
        row = _make_row(starts_at=NOW + timedelta(hours=2))
        mock_db._chain.data = [row]

        result = await repo.find_reminder_candidates(
            starts_from=NOW, starts_to=NOW + timedelta(hours=48)
        )

        assert len(result) == 1
        assert str(result[0].id) == row["id"]
        assert result[0].reminder_sent_at is None

    @pytest.mark.asyncio
    async def test_filters_by_status_pending_and_confirmed(
        self, repo: SupabaseAppointmentRepository, mock_db: MagicMock
    ) -> None:
        mock_db._chain.data = []

        await repo.find_reminder_candidates(
            starts_from=NOW, starts_to=NOW + timedelta(hours=48)
        )

        # in_() se llama con los status activos (orden alfabético, ver
        # AppointmentStatus.blocking_statuses()).
        mock_db._chain.in_.assert_called_once()
        args = mock_db._chain.in_.call_args[0]
        assert args[0] == "status"
        assert sorted(args[1]) == ["confirmed", "pending"]

    @pytest.mark.asyncio
    async def test_filters_reminder_sent_at_is_null(
        self, repo: SupabaseAppointmentRepository, mock_db: MagicMock
    ) -> None:
        mock_db._chain.data = []

        await repo.find_reminder_candidates(
            starts_from=NOW, starts_to=NOW + timedelta(hours=48)
        )

        mock_db._chain.is_.assert_called_once_with("reminder_sent_at", "null")

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(
        self, repo: SupabaseAppointmentRepository, mock_db: MagicMock
    ) -> None:
        mock_db._chain.data = []

        result = await repo.find_reminder_candidates(
            starts_from=NOW, starts_to=NOW + timedelta(hours=48)
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_query_failure_raises_domain_error(
        self, repo: SupabaseAppointmentRepository, mock_db: MagicMock
    ) -> None:
        from app.domain.shared.errors import DomainError

        mock_db._chain.execute.side_effect = RuntimeError("Supabase error: {}")

        with pytest.raises(DomainError):
            await repo.find_reminder_candidates(
                starts_from=NOW, starts_to=NOW + timedelta(hours=48)
            )


# ======================================================================
# mark_reminder_sent()
# ======================================================================


class TestMarkReminderSent:
    @pytest.mark.asyncio
    async def test_updates_reminder_sent_at_and_updated_at(
        self, repo: SupabaseAppointmentRepository, mock_db: MagicMock
    ) -> None:
        appointment_id = str(uuid4())

        await repo.mark_reminder_sent(appointment_id)

        mock_db._chain.update.assert_called_once()
        payload = mock_db._chain.update.call_args[0][0]
        assert "reminder_sent_at" in payload
        assert "updated_at" in payload
        assert payload["reminder_sent_at"] == payload["updated_at"]

    @pytest.mark.asyncio
    async def test_filters_by_id(
        self, repo: SupabaseAppointmentRepository, mock_db: MagicMock
    ) -> None:
        appointment_id = str(uuid4())

        await repo.mark_reminder_sent(appointment_id)

        mock_db._chain.eq.assert_called_once_with("id", appointment_id)

    @pytest.mark.asyncio
    async def test_failure_raises_domain_error(
        self, repo: SupabaseAppointmentRepository, mock_db: MagicMock
    ) -> None:
        from app.domain.shared.errors import DomainError

        mock_db._chain.execute.side_effect = RuntimeError("Supabase error: {}")

        with pytest.raises(DomainError):
            await repo.mark_reminder_sent(str(uuid4()))
