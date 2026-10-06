"""Value objects of the orders slice.

Every value object is a ``PydanticVO``: constraints declared in
``pydantic_type`` double as domain validation *and* as the pydantic schema, so
the same object can be used as a domain value and as a request field.
"""

from typing import Annotated

from pydantic import Field
from yaddd import SensitiveValueObject
from yaddd_pydantic import PydanticVO


__all__ = ["CardToken", "Money", "OrderReference"]


class OrderReference(PydanticVO[str]):
    """Human-readable order reference such as ``ORD-1A2B3C4D``."""

    pydantic_type = Annotated[str, Field(pattern=r"^ORD-[0-9A-F]{8}$")]


class Money(PydanticVO[int]):
    """Monetary amount in minor currency units (kopeks, cents).

    Integer minor units keep the value exact across SQL backends; converting
    to a major-unit decimal belongs to the presentation layer.
    """

    pydantic_type = Annotated[int, Field(ge=0, le=999_999_999)]


class CardToken(SensitiveValueObject[str], PydanticVO[str]):
    """Opaque payment token that must never leak into logs.

    ``SensitiveValueObject`` keeps ``repr()`` masked and ``str()`` raising,
    while ``PydanticVO`` adds the length constraints.
    """

    pydantic_type = Annotated[str, Field(min_length=8, max_length=64)]
