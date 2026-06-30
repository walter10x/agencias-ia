"""Shared fixtures for unit tests — mock external dependencies like Celery."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_celery_send_task() -> MagicMock:
    """Prevent celery_app.send_task from trying to connect to Redis broker.

    All unit tests run without a real Redis/Celery broker.
    Tests that need to verify celery calls can use their own
    `with patch(...)` to capture call arguments.
    """
    task = MagicMock()
    task.id = "mock-task-id"

    with patch(
        "app.infrastructure.whatsapp.message_processor.celery_app.send_task",
        return_value=task,
    ) as mock:
        yield mock
