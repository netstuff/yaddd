"""Business-rules."""

from abc import ABC

from yaddd.domain.entities.entity import Entity
from yaddd.shared.specification import Candidate, Specification

# TODO: упростить интерфейс, внедрить Generic.

class BusinessRule(Specification[Candidate], ABC):
    """Specification wrapper for domain busness rules."""

    # def __init__(self, rule: Callable[bool]) -> None:
    #     """Pass specification logic as rule."""
    #     self.rule_spec = rule

    # def __call__(self, candidate: Candidate)-> bool:
    #     """Business logic runs at call."""
    #     return self.is_satisfied_by(candidate)

    def __repr__(self) -> str:
        """Return string representation of rule."""
        return str(self.__class__.__name__)

    def __str__(self) -> str:
        """Return string representation of rule."""
        return self.__repr__()
