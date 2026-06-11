"""Shared helpers for schema converter parsers."""

from __future__ import annotations

import copy
import re
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

JsonSchemaT = TypeVar("JsonSchemaT", bound=dict[str, Any])


def _copy_schema(schema: JsonSchemaT) -> JsonSchemaT:
    return copy.deepcopy(schema)


def _unique_name(name: str, used_names: set[str]) -> str:
    candidate = name
    suffix = 2
    while candidate in used_names:
        candidate = f"{name}{suffix}"
        suffix += 1
    return candidate


def _namespace_name(namespace: str | None, to_class_title: Callable[[str], str]) -> str:
    if not namespace:
        return "NoNamespace"
    parts = re.findall(r"[A-Za-z0-9]+", namespace)
    return "".join(to_class_title(part) for part in parts) or "Namespace"
