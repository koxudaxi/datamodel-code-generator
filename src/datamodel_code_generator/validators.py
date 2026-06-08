"""Validator definitions for generated Pydantic models.

Provides types for defining custom field validators that can be added to generated models.
"""

from __future__ import annotations

import keyword
from enum import Enum
from typing import Any

from pydantic import BaseModel, RootModel, ValidationError, field_validator

_MIN_DOTTED_PATH_PARTS = 2


class ValidatorMode(str, Enum):
    """Validator mode for Pydantic v2 field_validator."""

    BEFORE = "before"
    AFTER = "after"
    WRAP = "wrap"
    PLAIN = "plain"


def _is_python_identifier(value: str) -> bool:
    return value.isidentifier() and not keyword.iskeyword(value)


def _validate_python_identifier(value: str) -> str:
    if not _is_python_identifier(value):
        msg = f"must be a valid Python identifier: {value!r}"
        raise ValueError(msg)
    return value


def _validate_dotted_python_identifier_path(value: str) -> str:
    parts = value.split(".")
    if len(parts) < _MIN_DOTTED_PATH_PARTS or any(not _is_python_identifier(part) for part in parts):
        msg = f"must be a dotted Python identifier path: {value!r}"
        raise ValueError(msg)
    return value


def _validator_mode_values() -> set[str]:
    return {mode.value for mode in ValidatorMode}


class ValidatorDefinition(BaseModel):
    """Definition of a single validator."""

    field: str | None = None
    fields: list[str] | None = None
    function: str
    mode: ValidatorMode = ValidatorMode.AFTER

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str | None) -> str | None:
        """Validate a single field name."""
        if value is None:
            return value
        return _validate_python_identifier(value)

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: list[str] | None) -> list[str] | None:
        """Validate multiple field names."""
        if value is None:
            return value
        for field_name in value:
            _validate_python_identifier(field_name)
        return value

    @field_validator("function")
    @classmethod
    def validate_function(cls, value: str) -> str:
        """Validate the imported validator function path."""
        return _validate_dotted_python_identifier_path(value)

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, value: Any) -> Any:
        """Validate the Pydantic field_validator mode."""
        if isinstance(value, ValidatorMode):
            return value
        if isinstance(value, str) and value in _validator_mode_values():
            return value
        allowed_values = ", ".join(repr(mode.value) for mode in ValidatorMode)
        msg = f"must be one of: {allowed_values}"
        raise ValueError(msg)


class ModelValidators(BaseModel):
    """Validators configuration for a single model."""

    validators: list[ValidatorDefinition]


class ValidatorsConfig(RootModel[dict[str, ModelValidators]]):
    """Root model for validators configuration."""


def format_validation_error(error: ValidationError) -> str:
    """Format the first Pydantic validation error as a concise, stable message."""
    errors = error.errors()
    if not errors:
        return str(error)  # pragma: no cover

    first_error = errors[0]
    location = ".".join(str(part) for part in first_error.get("loc", ()))
    context = first_error.get("ctx") or {}
    context_error = context.get("error")
    message = str(context_error) if context_error else str(first_error["msg"])

    if location:
        return f"{location}: {message}"
    return message


def normalize_validators(validators: Any) -> list[dict[str, Any]]:
    """Validate and normalize raw validators extra template data."""
    model_validators = ModelValidators.model_validate({"validators": validators})
    return [validator.model_dump(mode="json", exclude_none=True) for validator in model_validators.validators]
