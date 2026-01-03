"""Validator definitions for generated Pydantic models.

Provides types for defining custom field validators that can be added to generated models.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

from datamodel_code_generator.util import is_pydantic_v2

if TYPE_CHECKING:
    from pydantic import RootModel


class ValidatorMode(str, Enum):
    """Validator mode for Pydantic v2 field_validator."""

    BEFORE = "before"
    AFTER = "after"
    WRAP = "wrap"
    PLAIN = "plain"


class ValidatorDefinition(BaseModel):
    """Definition of a single validator."""

    field: str | None = None
    fields: list[str] | None = None
    function: str
    mode: ValidatorMode = ValidatorMode.AFTER


class ModelValidators(BaseModel):
    """Validators configuration for a single model."""

    validators: list[ValidatorDefinition]


if is_pydantic_v2():
    from pydantic import RootModel

    class ValidatorsConfig(RootModel[dict[str, ModelValidators]]):
        """Root model for validators configuration."""

else:  # pragma: no cover
    # Pydantic v1 doesn't support RootModel, but validators feature is v2-only anyway
    ValidatorsConfig = None  # type: ignore[assignment,misc]
