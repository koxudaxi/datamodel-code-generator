"""Validator definitions for generated Pydantic models.

Provides types for defining custom field validators that can be added to generated models.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, RootModel


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


class ValidatorsConfig(RootModel[dict[str, ModelValidators]]):
    """Root model for validators configuration."""
