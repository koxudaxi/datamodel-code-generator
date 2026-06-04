"""Tests for Avro schema code generation."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.format import PythonVersion, is_supported_in_black
from datamodel_code_generator.parser.avro import convert_avro_schema_data
from tests.main.avro.conftest import assert_file_content
from tests.main.conftest import (
    AVRO_DATA_PATH,
    CURRENT_PYTHON_VERSION,
    LEGACY_BLACK_SKIP,
    get_current_version_args,
    run_main_and_assert,
)

_CURRENT_PYTHON_VERSION = PythonVersion(CURRENT_PYTHON_VERSION)
_SKIP_BLACK = pytest.mark.skipif(
    not is_supported_in_black(_CURRENT_PYTHON_VERSION),
    reason=f"Installed black doesn't support Python {CURRENT_PYTHON_VERSION}",
)


def _expected_file(expected_file: str) -> str:
    return f"py{CURRENT_PYTHON_VERSION.replace('.', '')}/{expected_file}"


def _avro_bytes_default(*values: int) -> str:
    return bytes(values).decode("latin1")


def test_convert_avro_schema_data_normalizes_binary_defaults() -> None:
    """Convert Avro bytes/fixed default strings to Python bytes."""
    uuid_text = "00112233-4455-6677-8899-aabbccddeeff"
    uuid_bytes_default = UUID(uuid_text).bytes.decode("latin1")
    duration_default = _avro_bytes_default(0, 0, 0, 0, 2, 0, 0, 0, 0xB8, 0x0B, 0, 0)

    converted = convert_avro_schema_data({
        "type": "record",
        "name": "Defaults",
        "fields": [
            {"name": "nullByteDefault", "type": "bytes", "default": _avro_bytes_default(0)},
            {"name": "asciiByteDefault", "type": "bytes", "default": _avro_bytes_default(0x7F)},
            {"name": "firstHighByteDefault", "type": "bytes", "default": _avro_bytes_default(0x80)},
            {"name": "multiByteDefault", "type": "bytes", "default": _avro_bytes_default(0xFF, 0)},
            {"name": "bytesDefault", "type": "bytes", "default": "\u00ff"},
            {"name": "fixedDefault", "type": {"type": "fixed", "name": "FixedDefault", "size": 1}, "default": "\u00ff"},
            {"name": "namedFixedDefault", "type": "FixedDefault", "default": "\u00ff"},
            {
                "name": "unionDefault",
                "type": [{"type": "fixed", "name": "UnionFixed", "size": 1}, "null"],
                "default": "\u00ff",
            },
            {"name": "wrappedUnionDefault", "type": {"type": ["bytes", "null"]}, "default": "\u00ff"},
            {"name": "wrappedTypeDefault", "type": {"type": {"type": "bytes"}}, "default": "\u00ff"},
            {
                "name": "decimalDefault",
                "type": {"type": "bytes", "logicalType": "decimal", "precision": 4, "scale": 2},
                "default": "\u0004\u00d2",
            },
            {
                "name": "fixedUuidDefault",
                "type": {"type": "fixed", "name": "DefaultUuid", "size": 16, "logicalType": "uuid"},
                "default": uuid_bytes_default,
            },
            {
                "name": "stringUuidDefault",
                "type": {"type": "string", "logicalType": "uuid"},
                "default": uuid_text,
            },
            {
                "name": "durationDefault",
                "type": {"type": "fixed", "name": "DefaultDuration", "size": 12, "logicalType": "duration"},
                "default": duration_default,
            },
            {"name": "arrayDefault", "type": {"type": "array", "items": "bytes"}, "default": ["\u00ff"]},
            {"name": "mapDefault", "type": {"type": "map", "values": "bytes"}, "default": {"k": "\u00ff"}},
            {
                "name": "recordDefault",
                "type": {
                    "type": "record",
                    "name": "NestedDefault",
                    "fields": [{"name": "payload", "type": "bytes"}],
                },
                "default": {"payload": "\u00ff"},
            },
        ],
    })

    properties = converted["properties"]
    assert properties["nullByteDefault"]["default"] == b"\x00"
    assert properties["asciiByteDefault"]["default"] == b"\x7f"
    assert properties["firstHighByteDefault"]["default"] == b"\x80"
    assert properties["multiByteDefault"]["default"] == b"\xff\x00"
    assert properties["bytesDefault"]["default"] == b"\xff"
    assert properties["fixedDefault"]["default"] == b"\xff"
    assert properties["namedFixedDefault"]["default"] == b"\xff"
    assert properties["unionDefault"]["default"] == b"\xff"
    assert properties["wrappedUnionDefault"]["default"] == b"\xff"
    assert properties["wrappedTypeDefault"]["default"] == b"\xff"
    assert properties["decimalDefault"]["default"] == Decimal("12.34")
    assert properties["fixedUuidDefault"]["default"] == UUID(uuid_text)
    assert properties["stringUuidDefault"]["default"] == UUID(uuid_text)
    assert repr(properties["durationDefault"]["default"]) == "timedelta(days=2, milliseconds=3000)"
    assert properties["arrayDefault"]["default"] == [b"\xff"]
    assert properties["mapDefault"]["default"] == {"k": b"\xff"}
    assert properties["recordDefault"]["default"] == {"payload": b"\xff"}


def test_convert_avro_schema_data_keeps_values_for_unsupported_default_shapes() -> None:
    """Keep defaults unchanged when schemas or values cannot contain Avro binary defaults."""
    duration_with_months = _avro_bytes_default(1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    duration_days = _avro_bytes_default(0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0)
    duration_millis = _avro_bytes_default(0, 0, 0, 0, 0, 0, 0, 0, 0xB8, 0x0B, 0, 0)
    duration_zero = _avro_bytes_default(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    converted = convert_avro_schema_data({
        "type": "record",
        "name": "UnsupportedDefaults",
        "fields": [
            {"name": "bytesNonString", "type": "bytes", "default": 1},
            {"name": "bytesHighCodepoint", "type": "bytes", "default": "\u0100"},
            {"name": "arrayDefaultNotList", "type": {"type": "array", "items": "bytes"}, "default": "unchanged"},
            {
                "name": "recordDefaultExtraField",
                "type": {
                    "type": "record",
                    "name": "GuardRecord",
                    "fields": [{"name": "payload", "type": "bytes"}],
                },
                "default": {"payload": "\u00ff", "unknown": "\u00ff"},
            },
            {"name": "bigDecimalDefault", "type": {"type": "bytes", "logicalType": "big-decimal"}, "default": "\u00ff"},
            {"name": "decimalHighCodepoint", "type": {"type": "bytes", "logicalType": "decimal"}, "default": "\u0100"},
            {
                "name": "decimalInvalidScale",
                "type": {"type": "bytes", "logicalType": "decimal", "scale": "invalid"},
                "default": "\u00ff",
            },
            {
                "name": "durationWithMonths",
                "type": {"type": "fixed", "name": "DurationWithMonths", "size": 12, "logicalType": "duration"},
                "default": duration_with_months,
            },
            {
                "name": "durationWrongLength",
                "type": {"type": "fixed", "name": "DurationWrongLength", "size": 12, "logicalType": "duration"},
                "default": "\u00ff",
            },
            {
                "name": "durationDays",
                "type": {"type": "fixed", "name": "DurationDays", "size": 12, "logicalType": "duration"},
                "default": duration_days,
            },
            {
                "name": "durationMillis",
                "type": {"type": "fixed", "name": "DurationMillis", "size": 12, "logicalType": "duration"},
                "default": duration_millis,
            },
            {
                "name": "durationZero",
                "type": {"type": "fixed", "name": "DurationZero", "size": 12, "logicalType": "duration"},
                "default": duration_zero,
            },
            {
                "name": "uuidInvalid",
                "type": {"type": "fixed", "name": "InvalidUuid", "size": 16, "logicalType": "uuid"},
                "default": "not-a-uuid",
            },
        ],
    })

    properties = converted["properties"]
    assert properties["bytesNonString"]["default"] == 1
    assert properties["bytesHighCodepoint"]["default"] == "\u0100"
    assert properties["arrayDefaultNotList"]["default"] == "unchanged"
    assert properties["recordDefaultExtraField"]["default"] == {"payload": b"\xff", "unknown": "\u00ff"}
    assert properties["bigDecimalDefault"]["default"] == "\u00ff"
    assert properties["decimalHighCodepoint"]["default"] == "\u0100"
    assert properties["decimalInvalidScale"]["default"] == "\u00ff"
    assert properties["durationWithMonths"]["default"] == duration_with_months
    assert properties["durationWrongLength"]["default"] == "\u00ff"
    assert repr(properties["durationDays"]["default"]) == "timedelta(days=2)"
    assert repr(properties["durationMillis"]["default"]) == "timedelta(milliseconds=3000)"
    assert repr(properties["durationZero"]["default"]) == "timedelta(0)"
    assert properties["uuidInvalid"]["default"] == "not-a-uuid"


@_SKIP_BLACK
def test_main_avro_constructs(output_file: Path) -> None:
    """Generate models for Avro primitive, complex, named, union, default, and logical types."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "constructs.avsc",
        output_path=output_file,
        input_file_type="avro",
        assert_func=assert_file_content,
        expected_file=_expected_file("constructs.py"),
        extra_args=get_current_version_args("--use-field-description"),
        force_exec_validation=True,
    )


@_SKIP_BLACK
def test_main_avro_infer_input_file_type(output_file: Path) -> None:
    """Infer Avro schema input and generate a model."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "constructs.avsc",
        output_path=output_file,
        assert_func=assert_file_content,
        expected_file=_expected_file("constructs.py"),
        extra_args=get_current_version_args("--use-field-description"),
        force_exec_validation=True,
    )


@_SKIP_BLACK
def test_main_avro_namespace_collisions(output_file: Path) -> None:
    """Resolve Avro fullname collisions by namespace."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "namespace_collisions.avsc",
        output_path=output_file,
        input_file_type="avro",
        assert_func=assert_file_content,
        expected_file=_expected_file("namespace_collisions.py"),
        extra_args=get_current_version_args(),
        force_exec_validation=True,
    )


@_SKIP_BLACK
def test_main_avro_official_spec_long_list(output_file: Path) -> None:
    """Generate the recursive LongList record from the Apache Avro specification."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "official_long_list.avsc",
        output_path=output_file,
        input_file_type="avro",
        assert_func=assert_file_content,
        expected_file=_expected_file("official_long_list.py"),
        extra_args=get_current_version_args(),
        force_exec_validation=True,
    )


@_SKIP_BLACK
def test_main_avro_spec_matrix(output_file: Path) -> None:
    """Generate models for Avro specification schema forms and edge-case attributes."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "spec_matrix.avsc",
        output_path=output_file,
        input_file_type="avro",
        assert_func=assert_file_content,
        expected_file=_expected_file("spec_matrix.py"),
        extra_args=get_current_version_args("--use-field-description"),
        force_exec_validation=True,
    )


@pytest.mark.parametrize(
    ("fixture_name", "explicit_type"),
    [
        ("root_string.avsc", False),
        ("root_type_object.avsc", False),
        ("root_type_union.avsc", True),
        ("root_map.avsc", False),
        ("root_array.avsc", True),
        ("root_enum.avsc", True),
        ("root_fixed.avsc", True),
        ("root_fixed_uuid.avsc", True),
        pytest.param("root_union_named.avsc", False, marks=LEGACY_BLACK_SKIP),
        ("name_suffix_collision.avsc", True),
        ("namespace_null_collision.avsc", True),
    ],
)
@_SKIP_BLACK
def test_main_avro_schema_declaration_forms(output_file: Path, fixture_name: str, explicit_type: bool) -> None:
    """Generate importable code for Avro schema string/object/array declaration forms."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / fixture_name,
        output_path=output_file,
        input_file_type="avro" if explicit_type else None,
        assert_func=assert_file_content,
        expected_file=_expected_file(f"schema_declaration_forms/{Path(fixture_name).stem}.py"),
        extra_args=get_current_version_args(),
        force_exec_validation=True,
    )


OFFICIAL_SCHEMA_PASS_FIXTURES = tuple(sorted((AVRO_DATA_PATH / "official_schema_pass").glob("*.avsc")))


@pytest.mark.parametrize("fixture_path", OFFICIAL_SCHEMA_PASS_FIXTURES, ids=lambda path: path.stem)
@_SKIP_BLACK
def test_main_avro_official_c_schema_pass_corpus(output_file: Path, fixture_path: Path) -> None:
    """Generate importable code for Apache Avro release-1.12.1 C schema pass fixtures."""
    run_main_and_assert(
        input_path=fixture_path,
        output_path=output_file,
        input_file_type="avro",
        assert_func=assert_file_content,
        expected_file=_expected_file(f"official_schema_pass/{fixture_path.stem}.py"),
        extra_args=get_current_version_args(),
        force_exec_validation=True,
    )


def test_main_avro_schema_version_not_supported(output_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Reject explicit schema-version for Avro, which does not define an in-schema version marker."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "constructs.avsc",
        output_path=output_file,
        input_file_type="avro",
        extra_args=["--schema-version", "1.12"],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Avro schemas do not carry a version marker",
    )


@pytest.mark.parametrize(
    ("fixture_name", "expected_stderr_contains"),
    [
        ("invalid_schema_no_type.avsc", "Avro schema object requires a string, object, or union type"),
        ("invalid_schema_bad_name.avsc", "Avro record schema requires a string name"),
        ("invalid_schema_bad_fields.avsc", "Avro record fields must be a list"),
        ("invalid_schema_bad_field.avsc", "Avro record field requires a string name"),
        ("invalid_schema_field_item.avsc", "Avro record field requires a string name"),
        ("invalid_schema_field_value.avsc", "Unsupported Avro schema value"),
        ("invalid_schema_duplicate.avsc", "Duplicate Avro named type"),
        ("invalid_schema_unknown_ref.avsc", "Unknown Avro named type reference"),
        ("invalid_schema_root_ref.avsc", "Unknown Avro named type reference"),
        ("invalid_schema_simple_ref.avsc", "Unknown Avro named type reference"),
        ("invalid_schema_unknown_simple_ref_in_namespace.avsc", "Unknown Avro named type reference"),
        ("invalid_schema_bad_enum_symbols.avsc", "Avro enum symbols must be a list of strings"),
        ("invalid_schema_duplicate_enum_symbol.avsc", "Duplicate Avro enum symbol"),
        ("invalid_schema_bad_enum_symbol_name.avsc", "Invalid Avro enum symbol"),
        ("invalid_schema_bad_fixed_size.avsc", "Avro fixed size must be an integer"),
        ("invalid_schema_duplicate_field_name.avsc", "Duplicate Avro record field name"),
        ("invalid_schema_bad_named_type_name.avsc", "Invalid Avro record name"),
        ("invalid_schema_bad_namespace.avsc", "Invalid Avro namespace"),
        ("invalid_schema_bad_field_name.avsc", "Invalid Avro record field name"),
        ("invalid_schema_primitive_name_reuse.avsc", "Avro primitive type names may not be redefined"),
        ("invalid_schema_union_bad_value.avsc", "Unsupported Avro union value"),
        ("invalid_schema_union_nested.avsc", "Avro unions may not immediately contain other unions"),
        ("invalid_schema_union_type_list.avsc", "Avro unions may not immediately contain other unions"),
        ("invalid_schema_union_duplicate.avsc", "Avro unions may not contain duplicate unnamed type"),
        ("invalid_schema_union_ref.avsc", "Unknown Avro named type reference"),
    ],
)
def test_main_avro_invalid_schema_errors(
    output_file: Path,
    capsys: pytest.CaptureFixture[str],
    fixture_name: str,
    expected_stderr_contains: str,
) -> None:
    """Report Avro parser errors through the normal CLI path."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / fixture_name,
        output_path=output_file,
        input_file_type="avro",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=expected_stderr_contains,
    )


@pytest.mark.parametrize(
    ("file_text", "expected_stderr_contains"),
    [
        ("[]", "Can't infer input file type"),
        ("[1]", "Can't infer input file type"),
        ('["Custom"]', "Can't infer input file type"),
        ('[{"not": "a schema"}]', "Can't infer input file type"),
    ],
)
def test_main_avro_auto_detection_rejects_non_avro_shapes(
    tmp_path: Path,
    output_file: Path,
    capsys: pytest.CaptureFixture[str],
    file_text: str,
    expected_stderr_contains: str,
) -> None:
    """Avoid auto-detecting generic JSON/YAML shapes as Avro schemas."""
    input_path = tmp_path / "input.json"
    input_path.write_text(file_text, encoding="utf-8")
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=expected_stderr_contains,
    )


@pytest.mark.parametrize(
    ("file_text", "expected_stderr_contains"),
    [
        ('[["null", "string"]]', "Avro unions may not immediately contain other unions"),
        ('[{"type": ["null", "string"]}]', "Avro unions may not immediately contain other unions"),
        ('["null", "example.Ref"]', "Unknown Avro named type reference"),
        ('[{"type": "example.Ref"}]', "Unknown Avro named type reference"),
        ('{"type": "example.Ref"}', "Unknown Avro named type reference"),
    ],
)
def test_main_avro_auto_detection_routes_invalid_avro_shapes_to_avro_errors(
    tmp_path: Path,
    output_file: Path,
    capsys: pytest.CaptureFixture[str],
    file_text: str,
    expected_stderr_contains: str,
) -> None:
    """Infer Avro-looking inputs before reporting Avro parser errors."""
    input_path = tmp_path / "input.avsc"
    input_path.write_text(file_text, encoding="utf-8")
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=expected_stderr_contains,
    )


@pytest.mark.parametrize(
    "file_text",
    [
        '{"type": ["null", "string"]}',
        '{"type": "record"}',
        '{"type": "enum", "name": "Broken"}',
        '{"type": "fixed", "name": "Broken"}',
        '{"type": 1}',
        '{"$schema": "http://json-schema.org/draft-07/schema#", "type": "object"}',
    ],
)
def test_main_avro_auto_detection_leaves_json_schema_shapes_as_json_schema(
    tmp_path: Path,
    output_file: Path,
    capsys: pytest.CaptureFixture[str],
    file_text: str,
) -> None:
    """Do not route JSON Schema-looking inputs through the Avro parser."""
    input_path = tmp_path / "input.json"
    input_path.write_text(file_text, encoding="utf-8")
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        capsys=capsys,
        expected_stderr_contains="The input file type was determined to be:",
    )
