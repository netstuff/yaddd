"""Business rules."""

from typing import ClassVar

from yaddd.exceptions import BusinessRuleViolationError
from yaddd.shared.specification import Specification


__all__ = ["BusinessRule"]


class BusinessRule[C](Specification[C]):
    """A specification with a failure message.

    Use :meth:`check` where a violated rule must raise; use the inherited
    specification combinators (``&``, ``|``, ``~``, ``^``) to compose rules.
    """

    message: ClassVar[str] = ""

    def check(self, candidate: C) -> None:
        """Raise :class:`BusinessRuleViolationError` if the rule is not satisfied."""
        if not self.is_satisfied_by(candidate):
            raise BusinessRuleViolationError(self.message or f"{type(self).__name__} is not satisfied")

    def __repr__(self) -> str:
        return type(self).__name__

    def __str__(self) -> str:
        return repr(self)
