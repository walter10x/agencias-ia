"""Caso de uso: crear un feedback/calificación."""

from __future__ import annotations

from uuid import UUID

from app.application.dtos import CreateFeedbackInput, FeedbackOutput, feedback_to_output
from app.domain.feedback.entity import Feedback
from app.domain.feedback.repository import FeedbackRepository
from app.domain.shared.errors import InvalidFeedbackError


class CreateFeedbackUseCase:
    """Orquesta la creación de un feedback."""

    def __init__(self, repo: FeedbackRepository) -> None:
        self._repo = repo

    async def execute(self, input: CreateFeedbackInput) -> FeedbackOutput:
        if not input.client_id.strip():
            raise InvalidFeedbackError("client_id is required")
        if not (1 <= input.rating <= 5):
            raise InvalidFeedbackError("Rating must be between 1 and 5")

        try:
            feedback = Feedback(
                client_id=UUID(input.client_id),
                lead_id=UUID(input.lead_id) if input.lead_id else None,
                conversation_id=UUID(input.conversation_id) if input.conversation_id else None,
                rating=input.rating,
                comment=input.comment,
            )
        except ValueError as exc:
            raise InvalidFeedbackError(str(exc))

        await self._repo.save(feedback)
        return feedback_to_output(feedback)
