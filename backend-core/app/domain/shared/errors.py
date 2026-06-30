"""Errores de dominio."""


class DomainError(Exception):
    """Error base para todos los errores de dominio."""

    message: str

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InvalidClientError(DomainError):
    """Error cuando los datos del cliente son inválidos."""

    pass


class ClientNotFoundError(DomainError):
    """Error cuando el cliente no existe."""

    pass


class InvalidAgentError(DomainError):
    """Error cuando la configuración del agente es inválida."""

    pass


class AgentNotFoundError(DomainError):
    """Error cuando el agente no existe."""

    pass


class InvalidMessageError(DomainError):
    """Error cuando el mensaje a procesar es inválido."""

    pass


class ConversationNotFoundError(DomainError):
    """Error cuando la conversación no existe."""

    pass


class InvalidLeadError(DomainError):
    """Error cuando los datos del lead son inválidos."""
    pass


class LeadNotFoundError(DomainError):
    """Error cuando el lead no existe."""
    pass


class InvalidFeedbackError(DomainError):
    """Error cuando los datos del feedback son inválidos."""
    pass


class FeedbackNotFoundError(DomainError):
    """Error cuando el feedback no existe."""
    pass


class ProactiveMessageLimitError(DomainError):
    """Error cuando se excede el límite de mensajes proactivos diarios."""
    pass


class InvalidTemplateError(DomainError):
    """Error cuando la plantilla es inválida o no se puede aplicar."""
    pass


class TemplateNotFoundError(DomainError):
    """Error cuando la plantilla no existe."""
    pass


class LandingNotFoundError(DomainError):
    """Error cuando no se encuentra una landing page por slug."""
    pass


class LandingInactiveError(DomainError):
    """Error cuando la landing page está desactivada."""
    pass


class LandingRateLimitError(DomainError):
    """Error cuando se excede el rate limit de submissions por IP."""
    pass


class EmailError(DomainError):
    """Error cuando falla el envio de email."""
    pass
