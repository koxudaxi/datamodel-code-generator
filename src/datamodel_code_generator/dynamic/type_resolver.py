"""Type resolution utilities for dynamic model generation."""

from __future__ import annotations

import builtins
import decimal
import operator
from functools import reduce
from typing import TYPE_CHECKING, Any, ForwardRef, Literal

if TYPE_CHECKING:
    from datamodel_code_generator.types import DataType

TYPE_ALIASES: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
}

CONSTRAINED_TYPE_BASE: dict[str, type[Any]] = {
    "conint": int,
    "confloat": float,
    "constr": str,
    "conbytes": bytes,
    "condecimal": decimal.Decimal,
    "conlist": list,
    "conset": set,
    "confrozenset": frozenset,
}


class TypeResolver:
    """Resolves DataType objects to actual Python types."""

    def __init__(self, models: dict[str, type[Any]]) -> None:
        """Initialize with a models lookup dictionary."""
        self._models = models

    def resolve(self, data_type: DataType) -> Any:
        """Resolve a DataType to a Python type."""
        resolved_type, _ = self.resolve_with_constraints(data_type)
        return resolved_type

    def resolve_with_constraints(self, data_type: DataType) -> tuple[Any, dict[str, Any]]:
        """Resolve a DataType to a Python type and extract constraints."""
        constraints: dict[str, Any] = {}

        if data_type.reference is not None:
            return self._resolve_reference(data_type.reference.short_name), constraints

        if data_type.literals:
            return Literal[tuple(data_type.literals)], constraints

        if len(data_type.data_types) > 1:
            inner_types = [self.resolve(dt) for dt in data_type.data_types]
            return reduce(operator.or_, inner_types), constraints

        if data_type.data_types:
            return self._resolve_container(data_type), constraints

        return self._resolve_type_string(data_type, constraints)

    def _resolve_reference(self, model_name: str) -> Any:
        """Resolve a model reference to a type or ForwardRef."""
        if model_name in self._models:
            return self._models[model_name]
        return ForwardRef(model_name)

    def _resolve_container(self, data_type: DataType) -> Any:
        """Resolve container types (list, set, dict, optional)."""
        inner = self.resolve(data_type.data_types[0])
        if data_type.is_optional:
            return inner | None
        if data_type.is_list:
            return list[inner]
        if data_type.is_set:
            return set[inner]
        if data_type.is_dict:
            key_type = self.resolve(data_type.dict_key) if data_type.dict_key else str
            return dict[key_type, inner]
        return inner

    def _resolve_type_string(self, data_type: DataType, constraints: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """Resolve type from type string."""
        if not data_type.type:
            return Any, constraints

        type_str = data_type.type

        if type_str in CONSTRAINED_TYPE_BASE:
            base_type = CONSTRAINED_TYPE_BASE[type_str]
            self._extract_constraints(data_type, constraints)
            return base_type, constraints

        normalized = TYPE_ALIASES.get(type_str, type_str)
        if builtin_type := getattr(builtins, normalized, None):
            return builtin_type, constraints

        if type_str in self._models:
            return self._models[type_str], constraints

        return Any, constraints

    @staticmethod
    def _extract_constraints(data_type: DataType, constraints: dict[str, Any]) -> None:
        """Extract constraints from DataType kwargs."""
        if not data_type.kwargs:
            return
        for key, kwarg_value in data_type.kwargs.items():
            if key == "regex":
                pattern_value = kwarg_value
                if isinstance(pattern_value, str) and pattern_value.startswith("r'") and pattern_value.endswith("'"):
                    pattern_value = pattern_value[2:-1]
                constraints["pattern"] = pattern_value
            else:
                constraints[key] = kwarg_value
