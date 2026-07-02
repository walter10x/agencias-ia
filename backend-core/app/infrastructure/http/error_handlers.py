"""FastAPI exception handlers for domain errors."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.shared.errors import (
    AgentNotFoundError,
    ClientNotFoundError,
    ConversationNotFoundError,
    DomainError,
    EmailError,
    FeedbackNotFoundError,
    ForbiddenError,
    InvalidAgentError,
    InvalidClientError,
    InvalidFeedbackError,
    InvalidLeadError,
    InvalidTemplateError,
    LandingInactiveError,
    LandingNotFoundError,
    LandingRateLimitError,
    LeadNotFoundError,
    ProactiveMessageLimitError,
    TemplateNotFoundError,
)


async def invalid_client_error_handler(request: Request, exc: InvalidClientError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error_type": "invalid_client", "detail": exc.message},
    )


async def invalid_agent_error_handler(request: Request, exc: InvalidAgentError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error_type": "invalid_agent", "detail": exc.message},
    )


async def client_not_found_handler(request: Request, exc: ClientNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_type": "client_not_found", "detail": exc.message},
    )


async def agent_not_found_handler(request: Request, exc: AgentNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_type": "agent_not_found", "detail": exc.message},
    )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error_type": "domain_error", "detail": exc.message},
    )


async def conversation_not_found_handler(request: Request, exc: ConversationNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_type": "conversation_not_found", "detail": exc.message},
    )


async def invalid_lead_error_handler(request: Request, exc: InvalidLeadError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error_type": "invalid_lead", "detail": exc.message},
    )


async def lead_not_found_handler(request: Request, exc: LeadNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_type": "lead_not_found", "detail": exc.message},
    )


async def invalid_feedback_error_handler(request: Request, exc: InvalidFeedbackError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error_type": "invalid_feedback", "detail": exc.message},
    )


async def feedback_not_found_handler(request: Request, exc: FeedbackNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_type": "feedback_not_found", "detail": exc.message},
    )


async def proactive_message_limit_handler(request: Request, exc: ProactiveMessageLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error_type": "proactive_message_limit", "detail": exc.message},
    )


async def invalid_template_error_handler(request: Request, exc: InvalidTemplateError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error_type": "invalid_template", "detail": exc.message},
    )


async def template_not_found_handler(request: Request, exc: TemplateNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_type": "template_not_found", "detail": exc.message},
    )


async def landing_not_found_handler(request: Request, exc: LandingNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_type": "landing_not_found", "detail": exc.message},
    )


async def landing_inactive_handler(request: Request, exc: LandingInactiveError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error_type": "landing_not_found", "detail": exc.message},
    )


async def landing_rate_limit_handler(request: Request, exc: LandingRateLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error_type": "landing_rate_limit", "detail": exc.message},
    )


async def forbidden_error_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error_type": "forbidden", "detail": exc.message},
    )


async def email_error_handler(request: Request, exc: EmailError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"error_type": "email_error", "detail": exc.message},
    )


def register_error_handlers(app):
    """Register all domain exception handlers on a FastAPI app.

    DomainError must be last since other errors are subclasses.
    FastAPI matches the most specific handler first.
    """
    app.add_exception_handler(InvalidClientError, invalid_client_error_handler)
    app.add_exception_handler(InvalidAgentError, invalid_agent_error_handler)
    app.add_exception_handler(ClientNotFoundError, client_not_found_handler)
    app.add_exception_handler(AgentNotFoundError, agent_not_found_handler)
    app.add_exception_handler(ConversationNotFoundError, conversation_not_found_handler)
    app.add_exception_handler(InvalidLeadError, invalid_lead_error_handler)
    app.add_exception_handler(LeadNotFoundError, lead_not_found_handler)
    app.add_exception_handler(InvalidFeedbackError, invalid_feedback_error_handler)
    app.add_exception_handler(FeedbackNotFoundError, feedback_not_found_handler)
    app.add_exception_handler(ProactiveMessageLimitError, proactive_message_limit_handler)
    app.add_exception_handler(InvalidTemplateError, invalid_template_error_handler)
    app.add_exception_handler(TemplateNotFoundError, template_not_found_handler)
    app.add_exception_handler(LandingNotFoundError, landing_not_found_handler)
    app.add_exception_handler(LandingInactiveError, landing_inactive_handler)
    app.add_exception_handler(LandingRateLimitError, landing_rate_limit_handler)
    app.add_exception_handler(ForbiddenError, forbidden_error_handler)
    app.add_exception_handler(EmailError, email_error_handler)
    app.add_exception_handler(DomainError, domain_error_handler)
