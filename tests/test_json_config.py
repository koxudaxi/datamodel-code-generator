"""Tests for JSON configuration loading."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import pytest

from datamodel_code_generator.json_config import JsonConfigError, load_json_config_field
from tests.conftest import assert_output, assert_warnings_contain, assert_warnings_do_not_contain

DATA_PATH = Path(__file__).parent / "data"
CONFIG_DATA_PATH = DATA_PATH / "config"
EXPECTED_JSON_CONFIG_PATH = DATA_PATH / "expected" / "json_config"


def _dump_json_payload(value: Any) -> str:
    return f"{json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)}\n"


def test_load_json_config_field_returns_none_for_missing_value() -> None:
    """Missing JSON config values remain unset."""
    assert_output(
        _dump_json_payload(load_json_config_field("aliases", None)),
        EXPECTED_JSON_CONFIG_PATH / "missing_value.txt",
    )


def test_load_json_config_field_accepts_mapping_source() -> None:
    """Mapping sources are validated without an inline JSON parse step."""
    assert_output(
        _dump_json_payload(load_json_config_field("base_class_map", {"User": ["custom.Base", "custom.Mixin"]})),
        EXPECTED_JSON_CONFIG_PATH / "mapping_source.txt",
    )


def test_load_json_config_field_accepts_text_io_source() -> None:
    """Text IO sources are read through the same validation path."""
    with (CONFIG_DATA_PATH / "base_class_map.json").open(encoding="utf-8") as data:
        payload = load_json_config_field("base_class_map", data)

    assert_output(_dump_json_payload(payload), EXPECTED_JSON_CONFIG_PATH / "text_io_source.txt")


def test_load_json_config_field_warns_for_legacy_fallback() -> None:
    """Legacy-compatible values warn during the strict-validation migration."""
    with warnings.catch_warnings(record=True) as warning_records:
        warnings.simplefilter("always")
        payload = load_json_config_field("enum_field_as_literal_map", {"status": "legacy"})

    assert_output(_dump_json_payload(payload), EXPECTED_JSON_CONFIG_PATH / "legacy_fallback.txt")
    assert_warnings_contain(
        warning_records,
        "JSON configuration values that do not match the documented schema are deprecated",
        "--enum-field-as-literal-map currently falls back to legacy validation for compatibility",
    )


def test_load_json_config_field_can_skip_legacy_fallback_warning() -> None:
    """Programmatic callers can suppress legacy fallback warnings when needed."""
    with warnings.catch_warnings(record=True) as warning_records:
        warnings.simplefilter("always")
        payload = load_json_config_field(
            "enum_field_as_literal_map",
            {"status": "legacy"},
            warn_on_legacy_fallback=False,
        )

    assert_output(_dump_json_payload(payload), EXPECTED_JSON_CONFIG_PATH / "legacy_fallback.txt")
    assert_warnings_do_not_contain(
        warning_records,
        "JSON configuration values that do not match the documented schema are deprecated",
    )


def test_load_json_config_field_rejects_invalid_text_io_source() -> None:
    """Invalid JSON from a Text IO source reports the option-specific load error."""
    with (CONFIG_DATA_PATH / "invalid.json").open(encoding="utf-8") as data:
        with pytest.raises(JsonConfigError, match="Unable to load alias mapping"):
            load_json_config_field("aliases", data)


def test_load_json_config_field_rejects_invalid_strict_mapping_value() -> None:
    """Strict validation failures use the option name when no custom load name exists."""
    with pytest.raises(JsonConfigError, match="Invalid --base-class-map"):
        load_json_config_field("base_class_map", {"User": 1})


def test_load_json_config_field_rejects_invalid_legacy_fallback_value() -> None:
    """Legacy fallback still fails when the legacy schema also rejects the value."""
    with pytest.raises(JsonConfigError, match="Invalid --enum-field-as-literal-map"):
        load_json_config_field("enum_field_as_literal_map", {"status": 1})
