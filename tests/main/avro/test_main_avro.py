"""Tests for Avro schema code generation."""

from __future__ import annotations

from pathlib import Path

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


@pytest.mark.allow_direct_assert
def test_convert_avro_schema_data_isolates_raw_lists() -> None:
    """Keep converted Avro metadata and enum lists independent from raw schema input."""
    record_aliases = ["LegacyExample"]
    field_aliases = ["legacy_status"]
    enum_aliases = ["LegacyStatus"]
    enum_symbols = ["ACTIVE", "INACTIVE"]
    raw_schema = {
        "type": "record",
        "name": "Example",
        "aliases": record_aliases,
        "fields": [
            {
                "name": "status",
                "aliases": field_aliases,
                "type": {
                    "type": "enum",
                    "name": "Status",
                    "aliases": enum_aliases,
                    "symbols": enum_symbols,
                },
            }
        ],
    }

    converted = convert_avro_schema_data(raw_schema)
    record_schema = converted["definitions"]["Example"]
    field_schema = record_schema["properties"]["status"]
    enum_schema = converted["definitions"]["Status"]

    assert record_schema["x-avro-aliases"] == record_aliases
    assert record_schema["x-avro-aliases"] is not record_aliases
    assert field_schema["x-avro-aliases"] == field_aliases
    assert field_schema["x-avro-aliases"] is not field_aliases
    assert enum_schema["x-avro-aliases"] == enum_aliases
    assert enum_schema["x-avro-aliases"] is not enum_aliases
    assert enum_schema["enum"] == enum_symbols
    assert enum_schema["enum"] is not enum_symbols

    record_schema["x-avro-aliases"].append("MutatedExample")
    field_schema["x-avro-aliases"].append("mutated_status")
    enum_schema["x-avro-aliases"].append("MutatedStatus")
    enum_schema["enum"].append("MUTATED")

    assert record_aliases == ["LegacyExample"]
    assert field_aliases == ["legacy_status"]
    assert enum_aliases == ["LegacyStatus"]
    assert enum_symbols == ["ACTIVE", "INACTIVE"]


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
