"""Type resolution utilities for dynamic model generation."""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import TYPE_CHECKING, Any, ForwardRef, Literal, Union

if TYPE_CHECKING:
    from datamodel_code_generator.types import DataType

FORMAT_TYPE_MAP: dict[str, type[Any]] = {
    "date": datetime.date,
    "date-time": datetime.datetime,
    "time": datetime.time,
    "uuid": uuid.UUID,
    "uuid1": uuid.UUID,
    "uuid2": uuid.UUID,
    "uuid3": uuid.UUID,
    "uuid4": uuid.UUID,
    "uuid5": uuid.UUID,
    "decimal": decimal.Decimal,
    "email": str,
    "uri": str,
    "hostname": str,
    "ipv4": str,
    "ipv6": str,
    "binary": bytes,
    "byte": bytes,
}

PRIMITIVE_TYPE_MAP: dict[str, type[Any]] = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": bool,
    "boolean": bool,
    "bytes": bytes,
    "None": type(None),
    "Any": Any,  # type: ignore[dict-item]
}

CONSTRAINED_TYPE_MAP: dict[str, type[Any]] = {
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
            model_name = data_type.reference.short_name
            if model_name in self._models:
                return self._models[model_name], constraints
            return ForwardRef(model_name), constraints

        if data_type.literals:
            return Literal[tuple(data_type.literals)], constraints  # type: ignore[valid-type]

        if len(data_type.data_types) > 1:
            inner_types = tuple(self.resolve(dt) for dt in data_type.data_types)
            return Union[inner_types], constraints  # type: ignore[valid-type] # noqa: UP007

        if data_type.is_optional and data_type.data_types:
            inner = self.resolve(data_type.data_types[0])
            return inner | None, constraints  # type: ignore[operator]

        return self._resolve_type_string(data_type, constraints)

    def _resolve_type_string(self, data_type: DataType, constraints: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """Resolve type from type string."""
        if not data_type.type:
            return Any, constraints  # type: ignore[return-value]

        type_str = data_type.type

        if type_str in CONSTRAINED_TYPE_MAP:
            base_type = CONSTRAINED_TYPE_MAP[type_str]
            self._extract_constraints(data_type, constraints)
            return base_type, constraints

        if type_str in PRIMITIVE_TYPE_MAP:
            return PRIMITIVE_TYPE_MAP[type_str], constraints

        if type_str in self._models:
            return self._models[type_str], constraints

        return Any, constraints  # type: ignore[return-value]

    def _extract_constraints(self, data_type: DataType, constraints: dict[str, Any]) -> None:  # noqa: PLR6301
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
