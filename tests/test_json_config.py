"""Tests for JSON configuration loading and schema generation."""

from __future__ import annotations

import json
from collections import defaultdict
from io import StringIO
from pathlib import Path

import pytest

from datamodel_code_generator.json_config import (
    JsonConfigError,
    json_config_json_schema,
    load_json_config_field,
    validate_json_value_or_file,
)


@pytest.mark.allow_direct_assert
def test_json_config_schema_contains_strict_enum_values() -> None:
    """JSON config schema documents enum-field-as-literal-map values."""
    schema = json.loads(json_config_json_schema())

    enum_map_schema = schema["$defs"]["EnumFieldAsLiteralMapConfig"]

    assert enum_map_schema["additionalProperties"]["enum"] == ["literal", "enum"]


@pytest.mark.allow_direct_assert
def test_load_json_config_field_returns_none_for_missing_value() -> None:
    """JSON config loader should preserve None for unset options."""
    assert load_json_config_field("aliases", None) is None


@pytest.mark.allow_direct_assert
def test_load_json_config_field_accepts_mapping_source() -> None:
    """Already-loaded mapping values should pass through validation."""
    assert load_json_config_field("model_name_map", {"User": "Account"}) == {"User": "Account"}


@pytest.mark.allow_direct_assert
def test_load_json_config_field_accepts_text_io_source() -> None:
    """Text IO values should be loaded as JSON and closed after use."""
    data = StringIO('{"name": "fullName"}')

    assert load_json_config_field("serialization_aliases", data) == {"name": "fullName"}
    assert data.closed


def test_load_json_config_field_rejects_invalid_text_io_source() -> None:
    """Invalid JSON from Text IO should use the option's load error label."""
    with pytest.raises(JsonConfigError, match="Unable to load alias mapping"):
        load_json_config_field("aliases", StringIO("["))


@pytest.mark.allow_direct_assert
def test_load_json_config_field_accepts_file_path(tmp_path: Path) -> None:
    """JSON file paths should be loaded through the same validation path."""
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('{"User": "custom.Base"}', encoding="utf-8")

    assert load_json_config_field("base_class_map", mapping_path) == {"User": "custom.Base"}


def test_load_json_config_field_reports_file_read_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """File read failures should surface as JSON config errors."""

    def fail_read_text(self: Path, encoding: str) -> str:  # noqa: ARG001
        msg = "utf-8"
        raise UnicodeDecodeError(msg, b"\xff", 0, 1, "invalid start byte")

    def is_file(self: Path) -> bool:  # noqa: ARG001
        return True

    monkeypatch.setattr(Path, "is_file", is_file)
    monkeypatch.setattr(Path, "read_text", fail_read_text)

    with pytest.raises(JsonConfigError, match="Unable to read JSON file"):
        load_json_config_field("model_name_map", "mapping.json")


@pytest.mark.allow_direct_assert
def test_load_json_config_field_treats_path_probe_errors_as_inline_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Path probing errors should fall back to inline JSON parsing."""

    def fail_is_file(self: Path) -> bool:  # noqa: ARG001
        msg = "too long"
        raise OSError(msg)

    monkeypatch.setattr(Path, "is_file", fail_is_file)

    assert load_json_config_field("model_name_map", '{"User": "Account"}') == {"User": "Account"}


def test_load_json_config_field_rejects_invalid_inline_json_with_load_label() -> None:
    """Inline JSON decode errors should keep legacy load labels where configured."""
    with pytest.raises(JsonConfigError, match="Unable to load alias mapping"):
        load_json_config_field("aliases", "[")


def test_validate_json_value_or_file_rejects_invalid_inline_json_with_option_name() -> None:
    """Argparse-compatible JSON parsing should include the option name when provided."""
    with pytest.raises(JsonConfigError, match="Invalid JSON for --example"):
        validate_json_value_or_file("[", option_name="--example")


def test_validate_json_value_or_file_rejects_invalid_inline_json_without_option_name() -> None:
    """Argparse-compatible JSON parsing should have a generic invalid JSON fallback."""
    with pytest.raises(JsonConfigError, match="Invalid JSON:"):
        validate_json_value_or_file("[")


def test_validate_json_value_or_file_requires_json_object() -> None:
    """Argparse-compatible JSON parsing should reject non-object values."""
    with pytest.raises(JsonConfigError, match="Expected a JSON object, got list"):
        validate_json_value_or_file("[]")


@pytest.mark.allow_direct_assert
def test_validate_json_value_or_file_accepts_json_file(tmp_path: Path) -> None:
    """Argparse-compatible JSON parsing should accept JSON file paths."""
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text('{"User": "Account"}', encoding="utf-8")

    assert validate_json_value_or_file(str(mapping_path)) == {"User": "Account"}


@pytest.mark.allow_direct_assert
def test_extra_template_data_uses_recursive_defaultdict() -> None:
    """Extra template data should preserve legacy defaultdict behavior."""
    result = load_json_config_field("extra_template_data", '{"User": {"additional_imports": ["x"]}}')

    assert isinstance(result, defaultdict)
    assert isinstance(result["Missing"], dict)
    assert result["User"]["additional_imports"] == ["x"]


@pytest.mark.parametrize(
    ("field_name", "value", "match"),
    [
        ("aliases", '{"field": 1}', "Unable to load alias mapping"),
        ("default_values", "[]", "Unable to load default values mapping"),
        ("base_class_map", '{"User": 1}', "Invalid --base-class-map"),
        ("validators", '{"User": {"validators": [{"function": 1}]}}', "Invalid validators configuration"),
    ],
)
def test_load_json_config_field_rejects_invalid_strict_values(field_name: str, value: str, match: str) -> None:
    """Strict validation errors should retain their legacy-facing error prefixes."""
    with pytest.raises(JsonConfigError, match=match):
        load_json_config_field(field_name, value)


@pytest.mark.allow_direct_assert
def test_enum_field_as_literal_map_legacy_value_warns_and_falls_back() -> None:
    """Legacy enum-field-as-literal-map values warn before falling back."""
    with pytest.warns(FutureWarning, match="falls back to legacy validation"):
        result = load_json_config_field("enum_field_as_literal_map", '{"status": "legacy"}')

    assert result == {"status": "legacy"}


@pytest.mark.allow_direct_assert
def test_enum_field_as_literal_map_legacy_value_can_skip_warning() -> None:
    """Legacy fallback warning should be optional for internal callers."""
    result = load_json_config_field(
        "enum_field_as_literal_map",
        '{"status": "legacy"}',
        warn_on_legacy_fallback=False,
    )

    assert result == {"status": "legacy"}


@pytest.mark.allow_direct_assert
def test_duplicate_name_suffix_legacy_key_warns_and_falls_back() -> None:
    """Legacy duplicate-name-suffix keys warn before falling back."""
    with pytest.warns(FutureWarning, match="falls back to legacy validation"):
        result = load_json_config_field("duplicate_name_suffix", '{"model": "Schema", "custom": "Suffix"}')

    assert result == {"model": "Schema", "custom": "Suffix"}


def test_duplicate_name_suffix_rejects_values_outside_legacy_shape() -> None:
    """Legacy fallback should still reject values that were never valid mappings."""
    with pytest.raises(JsonConfigError, match="Invalid --duplicate-name-suffix"):
        load_json_config_field("duplicate_name_suffix", "[]")
