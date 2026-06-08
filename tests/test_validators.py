"""Tests for validator configuration helpers."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from datamodel_code_generator.validators import format_validation_error
from tests.conftest import assert_output

EXPECTED_PATH = Path(__file__).parent / "data" / "expected" / "validators"


def assert_validation_error_message(error: ValidationError, expected_file: Path) -> None:
    """Assert the formatted validation error message matches expected output."""
    assert_output(f"{format_validation_error(error)}\n", expected_file)


def test_format_validation_error_without_location_returns_message() -> None:
    """Validation errors without a location are formatted as a message only."""
    error = ValidationError.from_exception_data(
        "ValidatorDefinition",
        [
            {
                "type": "value_error",
                "loc": (),
                "input": "x",
                "ctx": {"error": ValueError("plain message")},
            }
        ],
    )

    assert_validation_error_message(error, EXPECTED_PATH / "format_validation_error_without_location.txt")
