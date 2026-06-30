"""Caso de uso: listar feedbacks de un cliente."""

from __future__ import annotations

from app.application.dtos import FeedbackOutput, ListFeedbackInput, feedback_to_output
from app.domain.feedback.repository import FeedbackRepository


class ListFeedbackUseCase:
    """Orquesta la consulta paginada de feedbacks."""

    def __init__(self, repo: FeedbackRepository) -> None:
        self._repo = repo

    async def execute(
        self, input: ListFeedbackInput
    ) -> tuple[list[FeedbackOutput], int]:
        if not input.client_id.strip():
            raise ValueError("client_id is required")

        feedbacks = await self._repo.list_by_client(
            client_id=input.client_id,
            limit=input.limit,
            offset=input.offset,
        )
        total = await self._repo.count_by_client(client_id=input.client_id)

        return [feedback_to_output(f) for f in feedbacks], total
