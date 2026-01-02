"""Validator definitions for generated Pydantic models.

Provides types for defining custom field validators that can be added to generated models.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypedDict

    class ValidatorDefinition(TypedDict, total=False):
        """Definition of a single validator."""

        field: str
        fields: list[str]
        function: str
        mode: str

    class ModelValidators(TypedDict, total=False):
        """Validators configuration for a single model."""

        validators: list[ValidatorDefinition]

    ValidatorsConfigType = dict[str, ModelValidators]


class ValidatorMode(str, Enum):
    """Validator mode for Pydantic v2 field_validator."""

    BEFORE = "before"
    AFTER = "after"
    WRAP = "wrap"
    PLAIN = "plain"
