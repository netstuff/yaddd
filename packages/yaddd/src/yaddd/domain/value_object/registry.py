"""Registry mapping base value object classes to the basic types they wrap."""

from collections.abc import Iterable
from types import UnionType
from typing import Annotated, Any, Final, cast, get_args, get_origin

from yaddd.domain.value_object.base import ValueObject


__all__ = ["VOBaseTypesRegistry"]


class _VOBaseTypesRegistry:
    def __init__(self) -> None:
        self._cls_to_basic_types: dict[type[ValueObject[Any]], tuple[type[Any], ...]] = {}
        self._basic_type_to_cls: dict[type[Any], type[ValueObject[Any]]] = {}

    @property
    def registered_vo_classes(self) -> Iterable[type[ValueObject[Any]]]:
        return self._cls_to_basic_types.keys()

    def register[T: ValueObject[Any]](self, vo_cls: type[T]) -> type[T]:
        self._ensure_value_object(vo_cls)

        self._process_class_registration(vo_cls)
        return vo_cls

    @staticmethod
    def _ensure_value_object(vo_cls: type[Any]) -> None:
        if not issubclass(vo_cls, ValueObject):
            raise TypeError(f"{vo_cls.__name__} must be a ValueObject subclass")

    def select_matching_vo_classes(self, target_type: Any) -> list[type[ValueObject[Any]]]:
        """Return registered VO classes whose basic types are superclasses of ``target_type``."""
        processed_type = self._normalize_type(target_type)
        matches: list[type[ValueObject[Any]]] = [cast(type[ValueObject[Any]], ValueObject)]  # abstract default

        for vo_cls, basic_types in self._cls_to_basic_types.items():
            if issubclass(processed_type, basic_types):
                matches.append(vo_cls)

        return matches

    def select_most_matching_vo_class(self, target_type: Any) -> type[ValueObject[Any]]:
        """Return the registered VO class with the most specific basic type for ``target_type``."""
        candidates = self.select_matching_vo_classes(target_type)
        if len(candidates) == 1:
            return candidates[0]

        processed_type = self._normalize_type(target_type)

        def mro_complexity(cls: type[ValueObject[Any]]) -> int:
            basic_types = self._cls_to_basic_types.get(cls, (object,))
            relevant_mros = [bt.__mro__ for bt in basic_types if issubclass(processed_type, bt)]
            return max(len(mro) for mro in relevant_mros) if relevant_mros else 0

        return max(candidates, key=mro_complexity)

    def _process_class_registration(self, vo_cls: type[ValueObject[Any]]) -> None:
        basic_types = self._extract_basic_types(vo_cls)

        self._cls_to_basic_types[vo_cls] = basic_types

        for bt in basic_types:
            if existing := self._basic_type_to_cls.get(bt):
                raise ValueError(f"Type conflict: {bt} already registered by {existing.__name__}")
            self._basic_type_to_cls[bt] = vo_cls

    @staticmethod
    def _normalize_type(target_type: Any) -> type[Any]:
        if get_origin(target_type) is Annotated:
            return cast(type[Any], get_args(target_type)[0])
        return cast(type[Any], get_origin(target_type) or target_type)

    @staticmethod
    def _extract_basic_types(vo_cls: type[ValueObject[Any]]) -> tuple[type[Any], ...]:
        generic_bases = [
            base
            for base in getattr(vo_cls, "__orig_bases__", ())
            if issubclass(get_origin(base) or base, ValueObject) and len(get_args(base)) == _VO_TYPEVARS_COUNT
        ]

        if not generic_bases:
            raise TypeError(f"Missing type parameters in {vo_cls.__name__}")
        if len(generic_bases) > 1:
            raise TypeError(f"Multiple generic bases in {vo_cls.__name__}")

        type_var = get_args(generic_bases[0])[0]

        if isinstance(type_var, UnionType):
            return get_args(type_var)
        return (get_origin(type_var) or type_var,)


VOBaseTypesRegistry = _VOBaseTypesRegistry()
del _VOBaseTypesRegistry

_VO_TYPEVARS_COUNT: Final[int] = len(ValueObject.__type_params__)
