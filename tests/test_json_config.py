"""Tests for JSON configuration loading and schema generation."""

from __future__ import annotations

import json

import pytest

from datamodel_code_generator.json_config import json_config_json_schema, load_json_config_field


def test_json_config_schema_contains_strict_enum_values() -> None:
    """JSON config schema documents enum-field-as-literal-map values."""
    schema = json.loads(json_config_json_schema())

    enum_map_schema = schema["$defs"]["EnumFieldAsLiteralMapConfig"]

    assert enum_map_schema["additionalProperties"]["enum"] == ["literal", "enum"]


def test_enum_field_as_literal_map_legacy_value_warns_and_falls_back() -> None:
    """Legacy enum-field-as-literal-map values warn before falling back."""
    with pytest.warns(FutureWarning, match="falls back to legacy validation"):
        result = load_json_config_field("enum_field_as_literal_map", '{"status": "legacy"}')

    assert result == {"status": "legacy"}


def test_duplicate_name_suffix_legacy_key_warns_and_falls_back() -> None:
    """Legacy duplicate-name-suffix keys warn before falling back."""
    with pytest.warns(FutureWarning, match="falls back to legacy validation"):
        result = load_json_config_field("duplicate_name_suffix", '{"model": "Schema", "custom": "Suffix"}')

    assert result == {"model": "Schema", "custom": "Suffix"}
