"""yaddd exception hierarchy.

All library-raised exceptions derive from :class:`YadddError`, so users can
catch a single base without losing the ability to narrow down by layer.
"""

__all__ = [
    "ApplicationError",
    "BusinessRuleViolationError",
    "ConnectorError",
    "DomainError",
    "EntityNotFoundError",
    "HandlerNotFoundError",
    "InfrastructureError",
    "InvariantViolationError",
    "SensitiveValueAccessError",
    "ValidationError",
    "YadddError",
]


class YadddError(Exception):
    """Base for all yaddd exceptions."""


class DomainError(YadddError):
    """An error raised by the domain layer."""


class BusinessRuleViolationError(DomainError):
    """A business rule (specification) is not satisfied."""


class InvariantViolationError(DomainError):
    """An aggregate invariant is violated."""


class ValidationError(DomainError):
    """A value object rejected the given raw value."""


class SensitiveValueAccessError(DomainError):
    """Access to a sensitive value object payload is not allowed."""

    def __init__(self, vo_name: str) -> None:
        super().__init__(f"Access to {vo_name} is not allowed.")


class ApplicationError(YadddError):
    """An error raised by the application layer."""


class HandlerNotFoundError(ApplicationError):
    """No handler is registered for the given command or query."""


class InfrastructureError(YadddError):
    """An error raised by the infrastructure layer."""


class EntityNotFoundError(InfrastructureError):
    """A repository could not find the requested record."""


class ConnectorError(InfrastructureError):
    """A connector to an external data source failed."""
