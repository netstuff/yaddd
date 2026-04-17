"""Business-rules."""

from abc import ABC
from typing import Callable

from yaddd.shared.specification import Candidate, Specification


class BusinessRule(Specification[Candidate], ABC):
    """Specification wrapper for domain busness rules."""

    # def __init__(self, rule: Callable[bool]) -> None:
    #     """Pass specification logic as rule."""
    #     self.rule_spec = rule

    # def __call__(self, candidate: Candidate)-> bool:
    #     """Business logic runs at call."""
    #     return self.is_satisfied_by(candidate)
