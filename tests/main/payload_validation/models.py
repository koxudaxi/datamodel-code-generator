"""Shared models for schema-derived payload validation tests."""

from __future__ import annotations

from collections import UserDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

JsonPath = tuple[str | int, ...]


@dataclass(frozen=True)
class SchemaCase:
    """A schema candidate that should generate a model named Payload."""

    id: str
    input_file_type: str
    source_path: Path
    source_schema: dict[str, Any] = field(repr=False)
    codegen_schema: dict[str, Any] = field(repr=False)
    temp_input_suffix: str


@dataclass(frozen=True)
class InvalidPayloadMutation:
    """A schema-invalid payload derived from a valid seed payload."""

    constraint: str
    path: JsonPath
    payload: Any = field(repr=False)
    reason: str


class GeneratedModelCache(UserDict[str, Any]):
    """Cache wrapper with compact Hypothesis failure representation."""

    def __repr__(self) -> str:
        """Return a compact representation for Hypothesis failure output."""
        return "GeneratedModelCache(...)"
