"""Pydantic v1 type manager.

Maps schema types to Pydantic v1 specific types (constr, conint, AnyUrl, etc.).
"""

from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.model.pydantic_v2.types import _PydanticDataTypeManager

HOSTNAME_REGEX = (  # Pydantic v1 requires \Z anchor (not $) to avoid matching trailing newline
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.)*"
    r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9])\Z"
)


class DataTypeManager(_PydanticDataTypeManager):
    """Manage data type mappings for Pydantic v1 models."""

    PATTERN_KEY: ClassVar[str] = "regex"
    HOSTNAME_REGEX: ClassVar[str] = HOSTNAME_REGEX
