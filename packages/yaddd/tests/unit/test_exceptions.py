import pytest

from yaddd import (
    ApplicationError,
    BusinessRuleViolationError,
    ConnectorError,
    DomainError,
    EntityNotFoundError,
    HandlerNotFoundError,
    InfrastructureError,
    InvariantViolationError,
    SensitiveValueAccessError,
    ValidationError,
    YadddError,
)


def test_all_errors_derive_from_yaddd_error():
    for exc_class in (
        DomainError,
        BusinessRuleViolationError,
        InvariantViolationError,
        ValidationError,
        SensitiveValueAccessError,
        ApplicationError,
        HandlerNotFoundError,
        InfrastructureError,
        EntityNotFoundError,
        ConnectorError,
    ):
        assert issubclass(exc_class, YadddError)


def test_layer_errors_are_intermediate_bases():
    assert issubclass(BusinessRuleViolationError, DomainError)
    assert issubclass(HandlerNotFoundError, ApplicationError)
    assert issubclass(EntityNotFoundError, InfrastructureError)


def test_sensitive_value_access_error_message():
    with pytest.raises(SensitiveValueAccessError, match="Access to Secret is not allowed"):
        raise SensitiveValueAccessError("Secret")
