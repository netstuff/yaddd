import operator
from json import JSONEncoder
from typing import Any, Callable

from ..base import ValueObject


vo_compatible_encoder: Callable[[ValueObject[Any]], Any] = operator.attrgetter("_validated_value")


class JSONEncoderError(Exception):
    """Value is unexpected, so cannot be encoded."""


def patch_json_encoder(encoder_cls: type[JSONEncoder] = JSONEncoder) -> None:
    """Modify JSONEncoder to support ValueObject.

    Make sure to use noly once on app initialization.
    """

    def _encode_value_object(o: ValueObject[Any] | Any) -> Any:
        if isinstance(o, ValueObject):
            return vo_compatible_encoder(o)
        raise JSONEncoderError

    _original_default = encoder_cls.default

    def _json_encode(self: encoder_cls, o: Any) -> Any:
        try:
            return _encode_value_object(o)
        except JSONEncoderError:
            return _original_default(self, o)

    encoder_cls.default = _json_encode
