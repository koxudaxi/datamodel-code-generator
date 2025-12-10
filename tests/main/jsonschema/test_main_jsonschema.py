"""Tests for JSON Schema input file code generation."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import call

import black
import pytest
from packaging import version

from datamodel_code_generator import (
    MIN_VERSION,
    DataModelType,
    InputFileType,
    PythonVersion,
    PythonVersionMin,
    chdir,
    generate,
)
from datamodel_code_generator.__main__ import Exit, main
from datamodel_code_generator.format import is_supported_in_black
from tests.conftest import assert_directory_content, freeze_time
from tests.main.conftest import (
    ALIASES_DATA_PATH,
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    LEGACY_BLACK_SKIP,
    MSGSPEC_LEGACY_BLACK_SKIP,
    TIMESTAMP,
    run_main_and_assert,
    run_main_url_and_assert,
    run_main_with_args,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH, assert_file_content

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

FixtureRequest = pytest.FixtureRequest


@pytest.mark.benchmark
def test_main_inheritance_forward_ref(output_file: Path, tmp_path: Path) -> None:
    """Test inheritance with forward references."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "inheritance_forward_ref.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        copy_files=[(DATA_PATH / "pyproject.toml", tmp_path / "pyproject.toml")],
    )


@pytest.mark.benchmark
def test_main_inheritance_forward_ref_keep_model_order(output_file: Path, tmp_path: Path) -> None:
    """Test inheritance with forward references keeping model order."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "inheritance_forward_ref.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--keep-model-order"],
        copy_files=[(DATA_PATH / "pyproject.toml", tmp_path / "pyproject.toml")],
    )


@pytest.mark.benchmark
def test_main_type_alias_forward_ref_keep_model_order(output_file: Path) -> None:
    """Test TypeAliasType with forward references keeping model order."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_alias_forward_ref.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=[
            "--keep-model-order",
            "--output-model-type",
            "typing.TypedDict",
            "--use-standard-collections",
            "--use-union-operator",
            "--use-type-alias",
            "--target-python-version",
            "3.10",
        ],
    )


@pytest.mark.skip(reason="pytest-xdist does not support the test")
def test_main_without_arguments() -> None:
    """Test main function without arguments raises SystemExit."""
    with pytest.raises(SystemExit):
        main()


@pytest.mark.benchmark
def test_main_autodetect(output_file: Path) -> None:
    """Test automatic input file type detection."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        input_file_type="auto",
        assert_func=assert_file_content,
    )


def test_main_autodetect_failed(tmp_path: Path) -> None:
    """Test autodetect failure with invalid input."""
    input_file: Path = tmp_path / "input.yaml"
    output_file: Path = tmp_path / "output.py"
    input_file.write_text(":", encoding="utf-8")
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        input_file_type="auto",
        expected_exit=Exit.ERROR,
    )


def test_main_jsonschema(output_file: Path) -> None:
    """Test JSON Schema file code generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="general.py",
    )


def test_main_jsonschema_dataclass_arguments_with_pydantic(output_file: Path) -> None:
    """Test JSON Schema code generation with dataclass arguments passed but using Pydantic model.

    This verifies that dataclass_arguments is properly ignored for non-dataclass models.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="general.py",
        extra_args=[
            "--output-model",
            "pydantic.BaseModel",
            "--dataclass-arguments",
            '{"slots": true, "order": true}',
        ],
    )


def test_main_jsonschema_dataclass_frozen_keyword_only(output_file: Path) -> None:
    """Test JSON Schema code generation with frozen and keyword-only dataclass.

    This tests the 'if existing:' False branch in _create_data_model when
    no --dataclass-arguments is provided but --frozen and --keyword-only are set.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="general_dataclass_frozen_kw_only.py",
        extra_args=[
            "--output-model",
            "dataclasses.dataclass",
            "--frozen",
            "--keyword-only",
            "--target-python-version",
            "3.10",
        ],
    )


@pytest.mark.benchmark
def test_main_jsonschema_nested_deep(tmp_path: Path) -> None:
    """Test deeply nested JSON Schema generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_person.json",
        output_path=tmp_path,
        output_to_expected=[
            ("__init__.py", EXPECTED_JSON_SCHEMA_PATH / "nested_deep" / "__init__.py"),
            ("nested/deep.py", EXPECTED_JSON_SCHEMA_PATH / "nested_deep" / "nested" / "deep.py"),
            (
                "empty_parent/nested/deep.py",
                EXPECTED_JSON_SCHEMA_PATH / "nested_deep" / "empty_parent" / "nested" / "deep.py",
            ),
        ],
        assert_func=assert_file_content,
        input_file_type="jsonschema",
    )


def test_main_jsonschema_nested_skip(output_dir: Path) -> None:
    """Test nested JSON Schema with skipped items."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_skip.json",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "nested_skip",
        input_file_type="jsonschema",
    )


@pytest.mark.benchmark
def test_main_jsonschema_external_files(output_file: Path) -> None:
    """Test JSON Schema with external file references."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_parent_root.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="external_files.py",
    )


@pytest.mark.benchmark
def test_main_jsonschema_collapsed_external_references(tmp_path: Path) -> None:
    """Test collapsed external references in JSON Schema."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_reference",
        output_path=tmp_path,
        output_to_expected=[
            ("ref0.py", "external_ref0.py"),
            ("other/ref2.py", EXPECTED_JSON_SCHEMA_PATH / "external_other_ref2.py"),
        ],
        assert_func=assert_file_content,
        input_file_type="jsonschema",
        extra_args=["--collapse-root-models"],
    )


@pytest.mark.benchmark
def test_main_jsonschema_multiple_files(output_dir: Path) -> None:
    """Test JSON Schema generation from multiple files."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "multiple_files",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "multiple_files",
        input_file_type="jsonschema",
    )


@pytest.mark.benchmark
def test_main_jsonschema_no_empty_collapsed_external_model(tmp_path: Path) -> None:
    """Test no empty files with collapsed external models."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_collapse",
        output_path=tmp_path,
        file_should_not_exist=tmp_path / "child.py",
        input_file_type="jsonschema",
        extra_args=["--collapse-root-models"],
    )
    assert (tmp_path / "__init__.py").exists()


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "null_and_array.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "null_and_array_v2.py",
        ),
    ],
)
def test_main_null_and_array(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test handling of null and array types."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "null_and_array.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model", output_model],
    )


def test_use_default_pydantic_v2_with_json_schema_const(output_file: Path) -> None:
    """Test use-default with const in Pydantic v2."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_default_with_const.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="use_default_with_const.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--use-default"],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output", "option"),
    [
        (
            "pydantic.BaseModel",
            "complicated_enum_default_member.py",
            "--set-default-enum-member",
        ),
        (
            "dataclasses.dataclass",
            "complicated_enum_default_member_dataclass.py",
            "--set-default-enum-member",
        ),
        (
            "dataclasses.dataclass",
            "complicated_enum_default_member_dataclass.py",
            None,
        ),
    ],
)
def test_main_complicated_enum_default_member(
    output_model: str, expected_output: str, option: str | None, output_file: Path
) -> None:
    """Test complicated enum with default member."""
    extra_args = [a for a in [option, "--output-model", output_model] if a]
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "complicated_enum.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=extra_args,
    )


@pytest.mark.benchmark
def test_main_json_reuse_enum_default_member(output_file: Path) -> None:
    """Test enum reuse with default member."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "duplicate_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--reuse-model", "--set-default-enum-member"],
    )


def test_main_invalid_model_name_failed(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Test invalid model name error handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "invalid_model_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--class-name", "with"],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="title='with' is invalid class name. You have to set `--class-name` option",
    )


def test_main_invalid_model_name_converted(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Test invalid model name conversion error."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "invalid_model_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="title='1Xyz' is invalid class name. You have to set `--class-name` option",
    )


def test_main_invalid_model_name(output_file: Path) -> None:
    """Test invalid model name with custom class name."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "invalid_model_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--class-name", "ValidModelName"],
    )


def test_main_jsonschema_reserved_field_names(output_file: Path) -> None:
    """Test reserved names are safely suffixed and aliased."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reserved_property.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="reserved_property.py",
    )


def test_main_jsonschema_with_local_anchor(output_file: Path) -> None:
    """Test $id anchor lookup resolves without error and reuses definitions."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "with_anchor.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="with_anchor.py",
    )


def test_main_jsonschema_missing_anchor_reports_error(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Test missing $id anchor produces a clear error instead of KeyError trace."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "missing_anchor.json",
        output_path=output_file,
        input_file_type="jsonschema",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Unresolved $id reference '#address'",
    )


def test_main_root_id_jsonschema_with_local_file(mocker: MockerFixture, output_file: Path) -> None:
    """Test root ID JSON Schema with local file reference."""
    root_id_response = mocker.Mock()
    root_id_response.text = "dummy"
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / "person.json").read_text()
    httpx_get_mock = mocker.patch("httpx.get", side_effect=[person_response])
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_id.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_id.py",
    )
    httpx_get_mock.assert_not_called()


def test_main_root_id_jsonschema_with_remote_file(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test root ID JSON Schema with remote file reference."""
    root_id_response = mocker.Mock()
    root_id_response.text = "dummy"
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / "person.json").read_text()
    httpx_get_mock = mocker.patch("httpx.get", side_effect=[person_response])
    input_file = tmp_path / "root_id.json"
    output_file: Path = tmp_path / "output.py"
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_id.py",
        copy_files=[(JSON_SCHEMA_DATA_PATH / "root_id.json", input_file)],
    )
    httpx_get_mock.assert_has_calls([
        call(
            "https://example.com/person.json",
            headers=None,
            verify=True,
            follow_redirects=True,
            params=None,
        ),
    ])


@pytest.mark.benchmark
def test_main_root_id_jsonschema_self_refs_with_local_file(mocker: MockerFixture, output_file: Path) -> None:
    """Test root ID JSON Schema self-references with local file."""
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / "person.json").read_text()
    httpx_get_mock = mocker.patch("httpx.get", side_effect=[person_response])
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_id_self_ref.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_id.py",
        transform=lambda s: s.replace("filename:  root_id_self_ref.json", "filename:  root_id.json"),
    )
    httpx_get_mock.assert_not_called()


@pytest.mark.benchmark
def test_main_root_id_jsonschema_self_refs_with_remote_file(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test root ID JSON Schema self-references with remote file."""
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / "person.json").read_text()
    httpx_get_mock = mocker.patch("httpx.get", side_effect=[person_response])
    input_file = tmp_path / "root_id_self_ref.json"
    output_file: Path = tmp_path / "output.py"
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_id.py",
        transform=lambda s: s.replace("filename:  root_id_self_ref.json", "filename:  root_id.json"),
        copy_files=[(JSON_SCHEMA_DATA_PATH / "root_id_self_ref.json", input_file)],
    )
    httpx_get_mock.assert_has_calls([
        call(
            "https://example.com/person.json",
            headers=None,
            verify=True,
            follow_redirects=True,
            params=None,
        ),
    ])


def test_main_root_id_jsonschema_with_absolute_remote_file(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test root ID JSON Schema with absolute remote file URL."""
    root_id_response = mocker.Mock()
    root_id_response.text = "dummy"
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / "person.json").read_text()
    httpx_get_mock = mocker.patch("httpx.get", side_effect=[person_response])
    input_file = tmp_path / "root_id_absolute_url.json"
    output_file: Path = tmp_path / "output.py"
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_id_absolute_url.py",
        copy_files=[(JSON_SCHEMA_DATA_PATH / "root_id_absolute_url.json", input_file)],
    )
    httpx_get_mock.assert_has_calls([
        call(
            "https://example.com/person.json",
            headers=None,
            verify=True,
            follow_redirects=True,
            params=None,
        ),
    ])


def test_main_root_id_jsonschema_with_absolute_local_file(output_file: Path) -> None:
    """Test root ID JSON Schema with absolute local file path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_id_absolute_url.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_id_absolute_url.py",
    )


@pytest.mark.benchmark
def test_main_jsonschema_id(output_file: Path) -> None:
    """Test JSON Schema with ID field."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "id.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="id.py",
    )


def test_main_jsonschema_id_as_stdin(monkeypatch: pytest.MonkeyPatch, output_file: Path) -> None:
    """Test JSON Schema ID handling from stdin."""
    run_main_and_assert(
        stdin_path=JSON_SCHEMA_DATA_PATH / "id.json",
        output_path=output_file,
        monkeypatch=monkeypatch,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="id_stdin.py",
    )


def test_main_jsonschema_stdin_oneof_ref(monkeypatch: pytest.MonkeyPatch, output_file: Path) -> None:
    """Test JSON Schema with oneOf $ref from stdin."""
    run_main_and_assert(
        stdin_path=JSON_SCHEMA_DATA_PATH / "stdin_oneof_ref.json",
        output_path=output_file,
        monkeypatch=monkeypatch,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="stdin_oneof_ref.py",
    )


def test_main_jsonschema_ids(output_dir: Path) -> None:
    """Test JSON Schema with multiple IDs."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / "ids" / "Organization.schema.json",
            output_path=output_dir,
            expected_directory=EXPECTED_JSON_SCHEMA_PATH / "ids",
            input_file_type="jsonschema",
        )


@pytest.mark.benchmark
def test_main_external_definitions(output_file: Path) -> None:
    """Test external definitions in JSON Schema."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_definitions_root.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_external_files_in_directory(output_file: Path) -> None:
    """Test external files in directory structure."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_files_in_directory" / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_nested_directory(output_dir: Path) -> None:
    """Test nested directory structure generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_files_in_directory",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "nested_directory",
        input_file_type="jsonschema",
    )


def test_main_circular_reference(output_file: Path) -> None:
    """Test circular reference handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "circular_reference.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_invalid_enum_name(output_file: Path) -> None:
    """Test invalid enum name handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "invalid_enum_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_invalid_enum_name_snake_case_field(output_file: Path) -> None:
    """Test invalid enum name with snake case fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "invalid_enum_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--snake-case-field"],
    )


def test_main_json_reuse_enum(output_file: Path) -> None:
    """Test enum reuse in JSON generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "duplicate_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--reuse-model"],
    )


def test_main_json_capitalise_enum_members(output_file: Path) -> None:
    """Test enum member capitalization."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "many_case_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--capitalise-enum-members"],
    )


def test_main_json_capitalise_enum_members_without_enum(output_file: Path) -> None:
    """Test enum member capitalization without enum flag."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="autodetect.py",
    )


def test_main_similar_nested_array(output_file: Path) -> None:
    """Test similar nested array structures."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "similar_nested_array.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "require_referenced_field",
        ),
        (
            "pydantic_v2.BaseModel",
            "require_referenced_field_pydantic_v2",
        ),
    ],
)
def test_main_require_referenced_field(output_model: str, expected_output: str, tmp_path: Path) -> None:
    """Test required referenced fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "require_referenced_field/",
        output_path=tmp_path,
        output_to_expected=[
            ("referenced.py", f"{expected_output}/referenced.py"),
            ("required.py", f"{expected_output}/required.py"),
        ],
        assert_func=assert_file_content,
        input_file_type="jsonschema",
        extra_args=["--output-datetime-class", "AwareDatetime", "--output-model-type", output_model],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "require_referenced_field",
        ),
        (
            "pydantic_v2.BaseModel",
            "require_referenced_field_naivedatetime",
        ),
    ],
)
def test_main_require_referenced_field_naive_datetime(output_model: str, expected_output: str, tmp_path: Path) -> None:
    """Test required referenced field with naive datetime."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "require_referenced_field/",
        output_path=tmp_path,
        output_to_expected=[
            ("referenced.py", f"{expected_output}/referenced.py"),
            ("required.py", f"{expected_output}/required.py"),
        ],
        assert_func=assert_file_content,
        input_file_type="jsonschema",
        extra_args=["--output-datetime-class", "NaiveDatetime", "--output-model-type", output_model],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "require_referenced_field",
        ),
        (
            "pydantic_v2.BaseModel",
            "require_referenced_field_pydantic_v2",
        ),
        (
            "msgspec.Struct",
            "require_referenced_field_msgspec",
        ),
    ],
)
def test_main_require_referenced_field_datetime(output_model: str, expected_output: str, tmp_path: Path) -> None:
    """Test required referenced field with datetime."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "require_referenced_field/",
        output_path=tmp_path,
        output_to_expected=[
            ("referenced.py", f"{expected_output}/referenced.py"),
            ("required.py", f"{expected_output}/required.py"),
        ],
        assert_func=assert_file_content,
        input_file_type="jsonschema",
        extra_args=["--output-model-type", output_model],
    )


def test_main_json_pointer(output_file: Path) -> None:
    """Test JSON pointer references."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "json_pointer.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_nested_json_pointer(output_file: Path) -> None:
    """Test nested JSON pointer references."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_json_pointer.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_jsonschema_multiple_files_json_pointer(output_dir: Path) -> None:
    """Test JSON pointer with multiple files."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "multiple_files_json_pointer",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "multiple_files_json_pointer",
        input_file_type="jsonschema",
    )


def test_main_root_model_with_additional_properties(output_file: Path) -> None:
    """Test root model with additional properties."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_with_additional_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_root_model_with_additional_properties_use_generic_container_types(output_file: Path) -> None:
    """Test root model additional properties with generic containers."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_with_additional_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--use-generic-container-types"],
    )


def test_main_root_model_with_additional_properties_use_standard_collections(output_file: Path) -> None:
    """Test root model additional properties with standard collections."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_with_additional_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--use-standard-collections"],
    )


def test_main_root_model_with_additional_properties_literal(min_version: str, output_file: Path) -> None:
    """Test root model additional properties with literal types."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_with_additional_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--enum-field-as-literal", "all", "--target-python-version", min_version],
    )


def test_main_jsonschema_multiple_files_ref(output_dir: Path) -> None:
    """Test multiple files with references."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "multiple_files_self_ref",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "multiple_files_self_ref",
        input_file_type="jsonschema",
    )


def test_main_jsonschema_multiple_files_ref_test_json(output_file: Path) -> None:
    """Test main jsonschema multiple files ref json."""
    with chdir(JSON_SCHEMA_DATA_PATH / "multiple_files_self_ref"):
        run_main_and_assert(
            input_path=Path("test.json"),
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file="multiple_files_self_ref_single.py",
        )


def test_main_space_field_enum_snake_case_field(output_file: Path) -> None:
    """Test enum with space in field name using snake case."""
    with chdir(JSON_SCHEMA_DATA_PATH / "space_field_enum.json"):
        run_main_and_assert(
            input_path=Path("space_field_enum.json"),
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            extra_args=["--snake-case-field", "--original-field-name-delimiter", " "],
        )


@pytest.mark.benchmark
def test_main_all_of_ref(output_file: Path) -> None:
    """Test allOf with references."""
    with chdir(JSON_SCHEMA_DATA_PATH / "all_of_ref"):
        run_main_and_assert(
            input_path=Path("test.json"),
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            extra_args=["--class-name", "Test"],
        )


def test_main_all_of_with_object(output_file: Path) -> None:
    """Test allOf with object types."""
    with chdir(JSON_SCHEMA_DATA_PATH):
        run_main_and_assert(
            input_path=Path("all_of_with_object.json"),
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
        )


def test_main_all_of_merge_same_property(output_file: Path) -> None:
    """Test allOf merging when duplicate property names exist across refs."""
    with chdir(JSON_SCHEMA_DATA_PATH):
        run_main_and_assert(
            input_path=Path("all_of_merge_same_property.json"),
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file="all_of_merge_same_property.py",
            extra_args=["--class-name", "Model"],
        )


def test_main_all_of_merge_boolean_property(output_file: Path) -> None:
    """Test allOf merging when a property has a boolean schema (false)."""
    with chdir(JSON_SCHEMA_DATA_PATH):
        run_main_and_assert(
            input_path=Path("all_of_merge_boolean_property.json"),
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file="all_of_merge_boolean_property.py",
            extra_args=["--class-name", "Model"],
        )


def test_main_all_of_ref_with_property_override(output_file: Path) -> None:
    """Test allOf with $ref preserves inheritance when properties are overridden."""
    with chdir(JSON_SCHEMA_DATA_PATH):
        run_main_and_assert(
            input_path=Path("all_of_ref_with_property_override.json"),
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file="all_of_ref_with_property_override.py",
        )


@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
def test_main_combined_array(output_file: Path) -> None:
    """Test combined array types."""
    with chdir(JSON_SCHEMA_DATA_PATH):
        run_main_and_assert(
            input_path=Path("combined_array.json"),
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
        )


def test_main_jsonschema_pattern(output_file: Path) -> None:
    """Test JSON Schema pattern validation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern.py",
    )


def test_main_generate(tmp_path: Path) -> None:
    """Test code generation function."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "person.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )

    assert_file_content(output_file, "general.py")


def test_main_generate_non_pydantic_output(tmp_path: Path) -> None:
    """Test generation with non-Pydantic output models (see issue #1452)."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "simple_string.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.DataclassesDataclass,
    )

    assert_file_content(output_file, "generate_non_pydantic_output.py")


def test_main_generate_from_directory(tmp_path: Path) -> None:
    """Test generation from directory input."""
    input_ = (JSON_SCHEMA_DATA_PATH / "external_files_in_directory").relative_to(Path.cwd())
    assert not input_.is_absolute()
    assert input_.is_dir()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=tmp_path,
    )

    main_nested_directory = EXPECTED_JSON_SCHEMA_PATH / "nested_directory"
    assert_directory_content(tmp_path, main_nested_directory)


def test_main_generate_custom_class_name_generator(tmp_path: Path) -> None:
    """Test custom class name generator."""

    def custom_class_name_generator(title: str) -> str:
        return f"Custom{title}"

    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "person.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        custom_class_name_generator=custom_class_name_generator,
    )

    assert_file_content(
        output_file,
        "general.py",
        transform=lambda s: s.replace("CustomPerson", "Person"),
    )


def test_main_generate_custom_class_name_generator_additional_properties(tmp_path: Path) -> None:
    """Test custom class name generator with additional properties."""
    output_file = tmp_path / "models.py"

    def custom_class_name_generator(name: str) -> str:
        return f"Custom{name[0].upper() + name[1:]}"

    input_ = (JSON_SCHEMA_DATA_PATH / "root_model_with_additional_properties.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        custom_class_name_generator=custom_class_name_generator,
    )

    assert_file_content(output_file, "root_model_with_additional_properties_custom_class_name.py")


def test_main_http_jsonschema(mocker: MockerFixture, output_file: Path) -> None:
    """Test HTTP JSON Schema fetching."""
    external_directory = JSON_SCHEMA_DATA_PATH / "external_files_in_directory"
    base_url = "https://example.com/external_files_in_directory/"

    url_to_path = {
        f"{base_url}person.json": "person.json",
        f"{base_url}definitions/relative/animal/pet/pet.json": "definitions/relative/animal/pet/pet.json",
        f"{base_url}definitions/relative/animal/fur.json": "definitions/relative/animal/fur.json",
        f"{base_url}definitions/friends.json": "definitions/friends.json",
        f"{base_url}definitions/food.json": "definitions/food.json",
        f"{base_url}definitions/machine/robot.json": "definitions/machine/robot.json",
        f"{base_url}definitions/drink/coffee.json": "definitions/drink/coffee.json",
        f"{base_url}definitions/drink/tea.json": "definitions/drink/tea.json",
    }

    def get_mock_response(url: str, **_: object) -> mocker.Mock:
        path = url_to_path.get(url)
        mock = mocker.Mock()
        mock.text = (external_directory / path).read_text()
        return mock

    httpx_get_mock = mocker.patch(
        "httpx.get",
        side_effect=get_mock_response,
    )
    run_main_url_and_assert(
        url="https://example.com/external_files_in_directory/person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="external_files_in_directory.py",
        transform=lambda s: s.replace(
            "#   filename:  https://example.com/external_files_in_directory/person.json",
            "#   filename:  person.json",
        ),
    )
    httpx_get_mock.assert_has_calls(
        [
            call(
                "https://example.com/external_files_in_directory/person.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/relative/animal/pet/pet.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/relative/animal/fur.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/friends.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/food.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/machine/robot.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/drink/coffee.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/drink/tea.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
            ),
        ],
        any_order=True,
    )
    assert httpx_get_mock.call_count == 8


@pytest.mark.parametrize(
    (
        "headers_arguments",
        "headers_requests",
        "query_parameters_arguments",
        "query_parameters_requests",
        "http_ignore_tls",
    ),
    [
        (
            ("Authorization: Basic dXNlcjpwYXNz",),
            [("Authorization", "Basic dXNlcjpwYXNz")],
            ("key=value",),
            [("key", "value")],
            False,
        ),
        (
            ("Authorization: Basic dXNlcjpwYXNz", "X-API-key: abcefg"),
            [("Authorization", "Basic dXNlcjpwYXNz"), ("X-API-key", "abcefg")],
            ("key=value", "newkey=newvalue"),
            [("key", "value"), ("newkey", "newvalue")],
            True,
        ),
    ],
)
def test_main_http_jsonschema_with_http_headers_and_http_query_parameters_and_ignore_tls(
    mocker: MockerFixture,
    headers_arguments: tuple[str, str],
    headers_requests: list[tuple[str, str]],
    query_parameters_arguments: tuple[str, ...],
    query_parameters_requests: list[tuple[str, str]],
    http_ignore_tls: bool,
    tmp_path: Path,
) -> None:
    """Test HTTP JSON Schema with headers, query params, and TLS ignore."""
    external_directory = JSON_SCHEMA_DATA_PATH / "external_files_in_directory"
    base_url = "https://example.com/external_files_in_directory/"

    url_to_path = {
        f"{base_url}person.json": "person.json",
        f"{base_url}definitions/relative/animal/pet/pet.json": "definitions/relative/animal/pet/pet.json",
        f"{base_url}definitions/relative/animal/fur.json": "definitions/relative/animal/fur.json",
        f"{base_url}definitions/friends.json": "definitions/friends.json",
        f"{base_url}definitions/food.json": "definitions/food.json",
        f"{base_url}definitions/machine/robot.json": "definitions/machine/robot.json",
        f"{base_url}definitions/drink/coffee.json": "definitions/drink/coffee.json",
        f"{base_url}definitions/drink/tea.json": "definitions/drink/tea.json",
    }

    def get_mock_response(url: str, **_: object) -> mocker.Mock:
        path = url_to_path.get(url)
        mock = mocker.Mock()
        mock.text = (external_directory / path).read_text()
        return mock

    httpx_get_mock = mocker.patch(
        "httpx.get",
        side_effect=get_mock_response,
    )
    output_file: Path = tmp_path / "output.py"
    extra_args = [
        "--http-headers",
        *headers_arguments,
        "--http-query-parameters",
        *query_parameters_arguments,
    ]
    if http_ignore_tls:
        extra_args.append("--http-ignore-tls")

    run_main_url_and_assert(
        url="https://example.com/external_files_in_directory/person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="external_files_in_directory.py",
        extra_args=extra_args,
        transform=lambda s: s.replace(
            "#   filename:  https://example.com/external_files_in_directory/person.json",
            "#   filename:  person.json",
        ),
    )
    httpx_get_mock.assert_has_calls(
        [
            call(
                "https://example.com/external_files_in_directory/person.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/relative/animal/pet/pet.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/relative/animal/fur.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/friends.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/food.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/machine/robot.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/drink/coffee.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/drink/tea.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
            ),
        ],
        any_order=True,
    )
    assert httpx_get_mock.call_count == 8


def test_main_self_reference(output_file: Path) -> None:
    """Test self-referencing schemas."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "self_reference.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


@pytest.mark.benchmark
def test_main_strict_types(output_file: Path) -> None:
    """Test strict type generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "strict_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
def test_main_strict_types_all(output_file: Path) -> None:
    """Test strict types for all fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "strict_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--strict-types", "str", "bytes", "int", "float", "bool"],
    )


def test_main_strict_types_all_with_field_constraints(output_file: Path) -> None:
    """Test strict types with field constraints."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "strict_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="strict_types_all_field_constraints.py",
        extra_args=["--strict-types", "str", "bytes", "int", "float", "bool", "--field-constraints"],
    )


def test_main_jsonschema_special_enum(output_file: Path) -> None:
    """Test special enum handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "special_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="special_enum.py",
    )


def test_main_jsonschema_special_enum_special_field_name_prefix(output_file: Path) -> None:
    """Test special enum with field name prefix."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "special_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="special_enum_special_field_name_prefix.py",
        extra_args=["--special-field-name-prefix", "special"],
    )


def test_main_jsonschema_special_enum_special_field_name_prefix_keep_private(output_file: Path) -> None:
    """Test special enum with prefix keeping private fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "special_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="special_enum_special_field_name_prefix_keep_private.py",
        extra_args=["--special-field-name-prefix", ""],
    )


def test_main_jsonschema_special_model_remove_special_field_name_prefix(output_file: Path) -> None:
    """Test removing special field name prefix from models."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "special_prefix_model.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="special_model_remove_special_field_name_prefix.py",
        extra_args=["--remove-special-field-name-prefix"],
    )


def test_main_jsonschema_subclass_enum(output_file: Path) -> None:
    """Test enum subclassing."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "subclass_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="subclass_enum.py",
        extra_args=["--use-subclass-enum"],
    )


def test_main_jsonschema_allof_enum_ref(output_file: Path) -> None:
    """Test allOf referencing enum from another schema."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "allof_enum_ref.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_jsonschema_allof_enum_no_external_ref(output_file: Path) -> None:
    """Test allOf referencing enum without external $ref.

    This covers the case where existing_ref is None in parse_all_of,
    so the schema is optimized to directly return the enum reference.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "allof_enum_no_external_ref.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support the old style",
)
def test_main_jsonschema_specialized_enums(output_file: Path) -> None:
    """Test specialized enum generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "subclass_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="enum_specialized.py",
        extra_args=["--target-python-version", "3.11"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support the old style",
)
def test_main_jsonschema_specialized_enums_disabled(output_file: Path) -> None:
    """Test with specialized enums disabled."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "subclass_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="enum_specialized_disable.py",
        extra_args=["--target-python-version", "3.11", "--no-use-specialized-enum"],
    )


def test_main_jsonschema_special_enum_empty_enum_field_name(output_file: Path) -> None:
    """Test special enum with empty field name."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "special_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="special_enum_empty_enum_field_name.py",
        extra_args=["--empty-enum-field-name", "empty"],
    )


@pytest.mark.benchmark
def test_main_jsonschema_special_field_name(output_file: Path) -> None:
    """Test special field name handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "special_field_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="special_field_name.py",
    )


def test_main_jsonschema_complex_one_of(output_file: Path) -> None:
    """Test complex oneOf schemas."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "complex_one_of.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="complex_one_of.py",
    )


def test_main_jsonschema_complex_any_of(output_file: Path) -> None:
    """Test complex anyOf schemas."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "complex_any_of.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="complex_any_of.py",
    )


def test_main_jsonschema_combine_one_of_object(output_file: Path) -> None:
    """Test combining oneOf with objects."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "combine_one_of_object.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="combine_one_of_object.py",
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.parametrize(
    ("union_mode", "output_model", "expected_output"),
    [
        (None, "pydantic.BaseModel", "combine_any_of_object.py"),
        (None, "pydantic_v2.BaseModel", "combine_any_of_object_v2.py"),
        (
            "left_to_right",
            "pydantic_v2.BaseModel",
            "combine_any_of_object_left_to_right.py",
        ),
    ],
)
def test_main_jsonschema_combine_any_of_object(
    union_mode: str | None, output_model: str, expected_output: str, output_file: Path
) -> None:
    """Test combining anyOf with objects."""
    extra_args = ["--output-model", output_model]
    if union_mode is not None:
        extra_args.extend(["--union-mode", union_mode])
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "combine_any_of_object.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=extra_args,
    )


@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("extra_args", "expected_file"),
    [
        (["--output-model", "pydantic_v2.BaseModel"], "jsonschema_root_model_ordering.py"),
        (
            ["--output-model", "pydantic_v2.BaseModel", "--keep-model-order"],
            "jsonschema_root_model_ordering_keep_model_order.py",
        ),
    ],
)
def test_main_jsonschema_root_model_ordering(output_file: Path, extra_args: list[str], expected_file: str) -> None:
    """Test RootModel is ordered after the types it references."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_ordering.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_file,
        extra_args=extra_args,
    )


@pytest.mark.benchmark
def test_main_jsonschema_field_include_all_keys(output_file: Path) -> None:
    """Test field generation including all keys."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="general.py",
        extra_args=["--field-include-all-keys"],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "field_extras_field_include_all_keys.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "field_extras_field_include_all_keys_v2.py",
        ),
    ],
)
def test_main_jsonschema_field_extras_field_include_all_keys(
    output_model: str, expected_output: str, output_file: Path
) -> None:
    """Test field extras including all keys."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extras.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--output-model",
            output_model,
            "--field-include-all-keys",
            "--field-extra-keys-without-x-prefix",
            "x-repr",
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "field_extras_field_extra_keys.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "field_extras_field_extra_keys_v2.py",
        ),
    ],
)
def test_main_jsonschema_field_extras_field_extra_keys(
    output_model: str, expected_output: str, output_file: Path
) -> None:
    """Test field extras with extra keys."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extras.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--output-model",
            output_model,
            "--field-extra-keys",
            "key2",
            "invalid-key-1",
            "--field-extra-keys-without-x-prefix",
            "x-repr",
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "field_extras.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "field_extras_v2.py",
        ),
    ],
)
def test_main_jsonschema_field_extras(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test field extras generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extras.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model", output_model],
    )


def test_main_jsonschema_custom_base_path(output_file: Path) -> None:
    """Test custom base path configuration."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "custom_base_path.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="custom_base_path.py",
    )


def test_long_description(output_file: Path) -> None:
    """Test long description handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "long_description.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_long_description_wrap_string_literal(output_file: Path) -> None:
    """Test long description with string literal wrapping."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "long_description.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--wrap-string-literal"],
    )


def test_version(capsys: pytest.CaptureFixture) -> None:
    """Test version output."""
    with pytest.raises(SystemExit) as e:
        run_main_with_args(["--version"])
    assert e.value.code == Exit.OK
    captured = capsys.readouterr()
    assert captured.out != "0.0.0\n"
    assert not captured.err


def test_jsonschema_pattern_properties(output_file: Path) -> None:
    """Test JSON Schema pattern properties."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern_properties.py",
    )


def test_jsonschema_pattern_properties_field_constraints(output_file: Path) -> None:
    """Test pattern properties with field constraints."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern_properties_field_constraints.py",
        extra_args=["--field-constraints"],
    )


def test_jsonschema_titles(output_file: Path) -> None:
    """Test JSON Schema title handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "titles.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="titles.py",
    )


def test_jsonschema_titles_use_title_as_name(output_file: Path) -> None:
    """Test using title as model name."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "titles.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="titles_use_title_as_name.py",
        extra_args=["--use-title-as-name"],
    )


def test_jsonschema_without_titles_use_title_as_name(output_file: Path) -> None:
    """Test title as name without titles present."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "without_titles.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="without_titles_use_title_as_name.py",
        extra_args=["--use-title-as-name"],
    )


def test_jsonschema_title_with_dots(output_file: Path) -> None:
    """Test using title as name when title contains dots (e.g., version numbers)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "title_with_dots.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="title_with_dots.py",
        extra_args=["--use-title-as-name"],
    )


def test_main_jsonschema_has_default_value(output_file: Path) -> None:
    """Test default value handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "has_default_value.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="has_default_value.py",
    )


def test_main_jsonschema_boolean_property(output_file: Path) -> None:
    """Test boolean property generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "boolean_property.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="boolean_property.py",
    )


def test_main_jsonschema_modular_default_enum_member(output_dir: Path) -> None:
    """Test modular enum with default member."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / "modular_default_enum_member",
            output_path=output_dir,
            expected_directory=EXPECTED_JSON_SCHEMA_PATH / "modular_default_enum_member",
            extra_args=["--set-default-enum-member"],
        )


@pytest.mark.skipif(
    black.__version__.split(".")[0] < "22",
    reason="Installed black doesn't support Python version 3.10",
)
def test_main_use_union_operator(output_dir: Path) -> None:
    """Test union operator usage."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_files_in_directory",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "use_union_operator",
        input_file_type="jsonschema",
        extra_args=["--use-union-operator"],
    )


@pytest.mark.parametrize("as_module", [True, False])
def test_treat_dot_as_module(as_module: bool, output_dir: Path) -> None:
    """Test dot notation as module separator."""
    path_extension = "treat_dot_as_module" if as_module else "treat_dot_not_as_module"
    extra_args = ["--treat-dot-as-module"] if as_module else None
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "treat_dot_as_module",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / path_extension,
        extra_args=extra_args,
    )


def test_treat_dot_as_module_single_file(output_dir: Path) -> None:
    """Test treat-dot-as-module with single file having short path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "treat_dot_as_module_single",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "treat_dot_as_module_single",
        extra_args=["--treat-dot-as-module"],
    )


def test_main_jsonschema_duplicate_name(output_dir: Path) -> None:
    """Test duplicate name handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "duplicate_name",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "duplicate_name",
        input_file_type="jsonschema",
    )


def test_main_jsonschema_items_boolean(output_file: Path) -> None:
    """Test items with boolean values."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "items_boolean.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="items_boolean.py",
    )


def test_main_jsonschema_array_in_additional_properites(output_file: Path) -> None:
    """Test array in additional properties."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "array_in_additional_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="array_in_additional_properties.py",
    )


def test_main_jsonschema_object_with_only_additional_properties(output_file: Path) -> None:
    """Test object with only additional properties."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "string_dict.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="string_dict.py",
    )


def test_main_jsonschema_nullable_object(output_file: Path) -> None:
    """Test nullable object handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nullable_object.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="nullable_object.py",
    )


def test_main_jsonschema_ref_type_has_null(output_file: Path) -> None:
    """Test that type: [type, null] from $ref schema is propagated."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "ref_type_has_null.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="ref_type_has_null.py",
        extra_args=["--use-union-operator"],
    )


def test_main_jsonschema_object_has_one_of(output_file: Path) -> None:
    """Test object with oneOf constraint."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "object_has_one_of.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="object_has_one_of.py",
    )


def test_main_jsonschema_oneof_const_enum(output_file: Path) -> None:
    """Test oneOf with const values generates enum (issue #1925)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum.py",
    )


def test_main_jsonschema_oneof_const_enum_nullable(output_file: Path) -> None:
    """Test nullable oneOf with const values generates optional enum."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_nullable.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_nullable.py",
    )


def test_main_jsonschema_oneof_const_enum_nested(output_file: Path) -> None:
    """Test nested oneOf with const values in properties and array items."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_nested.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_nested.py",
    )


def test_main_jsonschema_oneof_const_enum_nested_literal(output_file: Path) -> None:
    """Test nested oneOf const with --enum-field-as-literal all."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_nested.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_nested_literal.py",
        extra_args=["--enum-field-as-literal", "all"],
    )


def test_main_jsonschema_oneof_const_enum_int(output_file: Path) -> None:
    """Test oneOf with integer const values generates IntEnum."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_int.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_int.py",
    )


def test_main_jsonschema_oneof_const_enum_type_list(output_file: Path) -> None:
    """Test oneOf with const values and type list (nullable)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_type_list.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_type_list.py",
    )


def test_main_jsonschema_oneof_const_enum_literal(output_file: Path) -> None:
    """Test oneOf with const values as Literal type."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_literal.py",
        extra_args=["--enum-field-as-literal", "all"],
    )


def test_main_jsonschema_oneof_const_enum_infer_type(output_file: Path) -> None:
    """Test oneOf with const values and inferred type."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_infer_type.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_infer_type.py",
    )


def test_main_jsonschema_oneof_const_enum_bool(output_file: Path) -> None:
    """Test oneOf with boolean const values."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_bool.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_bool.py",
    )


def test_main_jsonschema_oneof_const_enum_float(output_file: Path) -> None:
    """Test oneOf with float const values."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_float.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_float.py",
    )


def test_main_jsonschema_anyof_const_enum_nested(output_file: Path) -> None:
    """Test nested anyOf with const values in properties and array items."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "anyof_const_enum_nested.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="anyof_const_enum_nested.py",
    )


def test_main_jsonschema_anyof_const_enum_nested_literal(output_file: Path) -> None:
    """Test nested anyOf const with --enum-field-as-literal all."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "anyof_const_enum_nested.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="anyof_const_enum_nested_literal.py",
        extra_args=["--enum-field-as-literal", "all"],
    )


def test_main_jsonschema_oneof_const_mixed_with_ref(output_file: Path) -> None:
    """Test oneOf with mixed const and $ref falls back to Union."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_mixed_with_ref.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_mixed_with_ref.py",
    )


def test_main_jsonschema_oneof_const_with_properties(output_file: Path) -> None:
    """Test oneOf with const and properties falls back to Union."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_with_properties.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_with_properties.py",
    )


def test_main_jsonschema_oneof_const_enum_type_list_no_null(output_file: Path) -> None:
    """Test oneOf const with type list without null."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_type_list_no_null.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_type_list_no_null.py",
    )


def test_main_jsonschema_oneof_const_enum_object(output_file: Path) -> None:
    """Test oneOf with object const values for type inference coverage."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "oneof_const_enum_object.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="oneof_const_enum_object.py",
    )


def test_main_jsonschema_json_pointer_array(output_file: Path) -> None:
    """Test JSON pointer with arrays."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "json_pointer_array.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="json_pointer_array.py",
    )


@pytest.mark.filterwarnings("error")
def test_main_disable_warnings_config(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Test disable warnings configuration."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        capsys=capsys,
        assert_no_stderr=True,
        input_file_type="jsonschema",
        extra_args=[
            "--use-union-operator",
            "--target-python-version",
            f"3.{MIN_VERSION}",
            "--disable-warnings",
        ],
    )


@pytest.mark.filterwarnings("error")
def test_main_disable_warnings(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Test disable warnings flag."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_of_with_object.json",
        output_path=output_file,
        capsys=capsys,
        assert_no_stderr=True,
        input_file_type="jsonschema",
        extra_args=["--disable-warnings"],
    )


def test_main_jsonschema_pattern_properties_by_reference(output_file: Path) -> None:
    """Test pattern properties by reference."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern_properties_by_reference.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern_properties_by_reference.py",
    )


def test_main_dataclass_field(output_file: Path) -> None:
    """Test dataclass field generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "user.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "dataclasses.dataclass"],
    )


@pytest.mark.skipif(
    not is_supported_in_black(PythonVersion.PY_312),
    reason="Black does not support Python 3.12",
)
def test_main_dataclass_field_py312(output_file: Path) -> None:
    """Test dataclass field generation with Python 3.12 type statement."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "user.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--target-python-version",
            "3.12",
        ],
    )


def test_main_jsonschema_enum_root_literal(output_file: Path) -> None:
    """Test enum root with literal type."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "enum_in_root" / "enum_in_root.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_in_enum.py",
        extra_args=[
            "--use-schema-description",
            "--use-title-as-name",
            "--field-constraints",
            "--target-python-version",
            "3.9",
            "--allow-population-by-field-name",
            "--strip-default-none",
            "--use-default",
            "--enum-field-as-literal",
            "all",
            "--snake-case-field",
            "--collapse-root-models",
        ],
    )


def test_main_nullable_any_of(output_file: Path) -> None:
    """Test nullable anyOf schemas."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nullable_any_of.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--field-constraints"],
    )


def test_main_nullable_any_of_use_union_operator(output_file: Path) -> None:
    """Test nullable anyOf with union operator."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nullable_any_of.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--field-constraints", "--use-union-operator"],
    )


def test_main_nested_all_of(output_file: Path) -> None:
    """Test nested allOf schemas."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_all_of.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_all_of_any_of(output_dir: Path) -> None:
    """Test combination of allOf and anyOf."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_of_any_of",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "all_of_any_of",
        input_file_type="jsonschema",
    )


def test_main_all_of_any_of_base_class_ref(output_file: Path) -> None:
    """Test allOf/anyOf with base class references to avoid invalid imports."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_of_any_of_base_class_ref.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--snake-case-field", "--use-double-quotes", "--reuse-model"],
    )


def test_main_all_of_one_of(output_dir: Path) -> None:
    """Test combination of allOf and oneOf."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_of_one_of",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "all_of_one_of",
        input_file_type="jsonschema",
    )


def test_main_null(output_file: Path) -> None:
    """Test null type handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "null.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.3.0"),
    reason="Require Black version 23.3.0 or later ",
)
def test_main_typed_dict_special_field_name_with_inheritance_model(output_file: Path) -> None:
    """Test TypedDict special field names with inheritance."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "special_field_name_with_inheritance_model.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "typing.TypedDict", "--target-python-version", "3.11"],
    )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.3.0"),
    reason="Require Black version 23.3.0 or later ",
)
def test_main_typed_dict_not_required_nullable(output_file: Path) -> None:
    """Test main function writing to TypedDict, with combos of Optional/NotRequired."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "not_required_nullable.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "typing.TypedDict", "--target-python-version", "3.11"],
    )


def test_main_typed_dict_const(output_file: Path) -> None:
    """Test main function writing to TypedDict with const fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "const.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "typing.TypedDict", "--target-python-version", "3.10"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] < "24",
    reason="Installed black doesn't support the new style",
)
def test_main_typed_dict_additional_properties(output_file: Path) -> None:
    """Test main function writing to TypedDict with additional properties, and no other fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "string_dict.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="typed_dict_with_only_additional_properties.py",
        extra_args=["--output-model-type", "typing.TypedDict", "--target-python-version", "3.11"],
    )


def test_main_dataclass_const(output_file: Path) -> None:
    """Test main function writing to dataclass with const fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "const.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "dataclasses.dataclass", "--target-python-version", "3.10"],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "discriminator_literals.py",
        ),
        (
            "msgspec.Struct",
            "discriminator_literals_msgspec.py",
        ),
    ],
)
@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 24,
    reason="Installed black doesn't support the new style",
)
def test_main_jsonschema_discriminator_literals(
    output_model: str, expected_output: str, min_version: str, output_file: Path
) -> None:
    """Test discriminator with literal types."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "discriminator_literals.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model, "--target-python", min_version],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 24,
    reason="Installed black doesn't support the new style",
)
def test_main_jsonschema_discriminator_literals_with_no_mapping(min_version: str, output_file: Path) -> None:
    """Test discriminator literals without mapping."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "discriminator_no_mapping.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="discriminator_no_mapping.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--target-python", min_version],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "discriminator_with_external_reference.py",
        ),
        pytest.param(
            "msgspec.Struct",
            "discriminator_with_external_reference_msgspec.py",
            marks=MSGSPEC_LEGACY_BLACK_SKIP,
        ),
    ],
)
def test_main_jsonschema_external_discriminator(
    output_model: str, expected_output: str, min_version: str, output_file: Path
) -> None:
    """Test external discriminator references."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "discriminator_with_external_reference" / "inner_folder" / "schema.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model, "--target-python", min_version],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "discriminator_with_external_references_folder",
        ),
        pytest.param(
            "msgspec.Struct",
            "discriminator_with_external_references_folder_msgspec",
            marks=MSGSPEC_LEGACY_BLACK_SKIP,
        ),
    ],
)
def test_main_jsonschema_external_discriminator_folder(
    output_model: str, expected_output: str, min_version: str, output_dir: Path
) -> None:
    """Test external discriminator in folder structure."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "discriminator_with_external_reference",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / expected_output,
        extra_args=[
            "--output-model-type",
            output_model,
            "--target-python",
            min_version,
        ],
    )


def test_main_duplicate_field_constraints(output_dir: Path) -> None:
    """Test duplicate field constraint handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "duplicate_field_constraints",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "duplicate_field_constraints",
        input_file_type="jsonschema",
        extra_args=[
            "--collapse-root-models",
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_duplicate_field_constraints_msgspec(min_version: str, output_dir: Path) -> None:
    """Test duplicate field constraints with msgspec."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "duplicate_field_constraints",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "duplicate_field_constraints_msgspec",
        input_file_type="jsonschema",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--target-python-version",
            min_version,
        ],
    )


def test_main_dataclass_field_defs(output_file: Path) -> None:
    """Test dataclass field definitions."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "user_defs.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="dataclass_field.py",
        extra_args=["--output-model-type", "dataclasses.dataclass"],
        transform=lambda s: s.replace("filename:  user_defs.json", "filename:  user.json"),
    )


def test_main_dataclass_default(output_file: Path) -> None:
    """Test dataclass default values."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "user_default.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="dataclass_field_default.py",
        extra_args=["--output-model-type", "dataclasses.dataclass"],
    )


def test_main_all_of_ref_self(output_file: Path) -> None:
    """Test allOf with self-reference."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_of_ref_self.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_array_field_constraints(output_file: Path) -> None:
    """Test array field constraints."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "array_field_constraints.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--field-constraints"],
    )


def test_all_of_use_default(output_file: Path) -> None:
    """Test allOf with use-default option."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_of_default.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--use-default"],
    )


def test_main_root_one_of(output_dir: Path) -> None:
    """Test root-level oneOf schemas."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_one_of",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "root_one_of",
        input_file_type="jsonschema",
    )


def test_one_of_with_sub_schema_array_item(output_file: Path) -> None:
    """Test oneOf with sub-schema array items."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "one_of_with_sub_schema_array_item.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_jsonschema_with_custom_formatters(output_file: Path, tmp_path: Path) -> None:
    """Test custom formatter integration."""
    formatter_config = {
        "license_file": str(Path(__file__).parent.parent.parent / "data/python/custom_formatters/license_example.txt")
    }
    formatter_config_path = tmp_path / "formatter_config"
    formatter_config_path.write_text(json.dumps(formatter_config))
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="custom_formatters.py",
        extra_args=[
            "--custom-formatters",
            "tests.data.python.custom_formatters.add_license",
            "--custom-formatters-kwargs",
            str(formatter_config_path),
        ],
    )


def test_main_imports_correct(output_dir: Path) -> None:
    """Test correct import generation."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "imports_correct",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "imports_correct",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "duration_pydantic_v2.py",
        ),
        (
            "msgspec.Struct",
            "duration_msgspec.py",
        ),
    ],
)
def test_main_jsonschema_duration(output_model: str, expected_output: str, min_version: str, output_file: Path) -> None:
    """Test duration type handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "duration.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model, "--target-python", min_version],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 24,
    reason="Installed black doesn't support the new style",
)
def test_main_jsonschema_keyword_only_msgspec(min_version: str, output_file: Path) -> None:
    """Test msgspec keyword-only arguments."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "discriminator_literals.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="discriminator_literals_msgspec_keyword_only.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--keyword-only",
            "--target-python-version",
            min_version,
        ],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 24,
    reason="Installed black doesn't support the new style",
)
def test_main_jsonschema_keyword_only_msgspec_with_extra_data(min_version: str, output_file: Path) -> None:
    """Test msgspec keyword-only with extra data."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "discriminator_literals.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="discriminator_literals_msgspec_keyword_only_omit_defaults.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--keyword-only",
            "--target-python-version",
            min_version,
            "--extra-template-data",
            str(JSON_SCHEMA_DATA_PATH / "extra_data_msgspec.json"),
        ],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 24,
    reason="Installed black doesn't support the new style",
)
def test_main_jsonschema_openapi_keyword_only_msgspec_with_extra_data(tmp_path: Path) -> None:
    """Test OpenAPI msgspec keyword-only with extra data."""
    extra_data = json.loads((JSON_SCHEMA_DATA_PATH / "extra_data_msgspec.json").read_text())
    output_file: Path = tmp_path / "output.py"
    generate(
        input_=JSON_SCHEMA_DATA_PATH / "discriminator_literals.json",
        output=output_file,
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.MsgspecStruct,
        keyword_only=True,
        target_python_version=PythonVersionMin,
        extra_template_data=defaultdict(dict, extra_data),
        # Following values are implied by `msgspec.Struct` in the CLI
        use_annotated=True,
        field_constraints=True,
    )
    assert_file_content(output_file, "discriminator_literals_msgspec_keyword_only_omit_defaults.py")


@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_msgspec_discriminator_with_type_string(output_file: Path) -> None:
    """Test msgspec Struct generation with discriminator using type: string + const."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "discriminator_with_type_string.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="discriminator_with_type_string_msgspec.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--target-python-version",
            "3.10",
        ],
    )


@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_msgspec_discriminator_with_meta(output_file: Path) -> None:
    """Test msgspec Struct generation with discriminator ClassVar having Meta constraints."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "discriminator_with_meta_msgspec.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="discriminator_with_meta_msgspec.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--target-python-version",
            "3.10",
        ],
    )


@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_msgspec_discriminator_without_annotated(output_file: Path) -> None:
    """Test msgspec Struct discriminator generates ClassVar even without use_annotated."""
    generate(
        JSON_SCHEMA_DATA_PATH / "discriminator_with_type_string.json",
        output=output_file,
        output_model_type=DataModelType.MsgspecStruct,
        target_python_version=PythonVersion.PY_310,
        use_annotated=False,
    )
    assert_file_content(output_file, "discriminator_with_type_string_msgspec_no_annotated.py")


@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_msgspec_null_field(output_file: Path) -> None:
    """Test msgspec Struct generation with null type fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "msgspec_null_field.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--use-union-operator",
            "--target-python-version",
            "3.10",
        ],
    )


@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_msgspec_falsy_defaults(output_file: Path) -> None:
    """Test msgspec Struct generation preserves falsy default values (0, '', False)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "msgspec_falsy_defaults.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--use-union-operator",
            "--target-python-version",
            "3.10",
        ],
    )


def test_main_invalid_import_name(output_dir: Path) -> None:
    """Test invalid import name handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "invalid_import_name",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "invalid_import_name",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_alias_import_alias(output_dir: Path) -> None:
    """Ensure imports with aliases are retained after cleanup."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "alias_import_alias",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "alias_import_alias",
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "field_has_same_name_v2.py",
        ),
        (
            "pydantic.BaseModel",
            "field_has_same_name.py",
        ),
    ],
)
def test_main_jsonschema_field_has_same_name(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test field with same name as parent."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "field_has_same_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model],
    )


@pytest.mark.benchmark
def test_main_jsonschema_required_and_any_of_required(output_file: Path) -> None:
    """Test required field with anyOf required."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "required_and_any_of_required.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="required_and_any_of_required.py",
    )


def test_main_json_pointer_escaped_segments(tmp_path: Path) -> None:
    """Test JSON pointer with escaped segments."""
    schema = {
        "definitions": {
            "foo/bar": {"type": "object", "properties": {"value": {"type": "string"}}},
            "baz~qux": {"type": "object", "properties": {"value": {"type": "integer"}}},
        },
        "properties": {
            "foo_bar": {"$ref": "#/definitions/foo~1bar"},
            "baz_qux": {"$ref": "#/definitions/baz~0qux"},
        },
        "type": "object",
    }
    expected = (
        "# generated by datamodel-codegen:\n"
        "#   filename: input.json\n"
        "#   timestamp: 2019-07-26T00:00:00+00:00\n\n"
        "from __future__ import annotations\n\n"
        "from typing import Optional\n\n"
        "from pydantic import BaseModel\n\n"
        "class FooBar(BaseModel):\n    value: Optional[str] = None\n\n"
        "class BazQux(BaseModel):\n    value: Optional[int] = None\n\n"
        "class Baz0qux(BaseModel):\n    value: Optional[int] = None\n\n"
        "class Foo1bar(BaseModel):\n    value: Optional[str] = None\n\n"
        "class Model(BaseModel):\n    foo_bar: Optional[Foo1bar] = None\n    baz_qux: Optional[Baz0qux] = None\n"
    )

    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.py"
    input_file.write_text(json.dumps(schema))
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        expected_output=expected,
        input_file_type="jsonschema",
        ignore_whitespace=True,
    )


def test_main_json_pointer_percent_encoded_segments(tmp_path: Path) -> None:
    """Test JSON pointer with percent-encoded segments."""
    schema = {
        "definitions": {
            "foo/bar": {"type": "object", "properties": {"value": {"type": "string"}}},
            "baz~qux": {"type": "object", "properties": {"value": {"type": "integer"}}},
            "space key": {"type": "object", "properties": {"value": {"type": "boolean"}}},
        },
        "properties": {
            "foo_bar": {"$ref": "#/definitions/foo%2Fbar"},
            "baz_qux": {"$ref": "#/definitions/baz%7Equx"},
            "space_key": {"$ref": "#/definitions/space%20key"},
        },
        "type": "object",
    }
    expected = (
        "# generated by datamodel-codegen:\n"
        "#   filename: input.json\n"
        "#   timestamp: 2019-07-26T00:00:00+00:00\n\n"
        "from __future__ import annotations\n\n"
        "from typing import Optional\n\n"
        "from pydantic import BaseModel\n\n"
        "class FooBar(BaseModel):\n    value: Optional[str] = None\n\n"
        "class BazQux(BaseModel):\n    value: Optional[int] = None\n\n"
        "class SpaceKey(BaseModel):\n    value: Optional[bool] = None\n\n"
        "class Baz7Equx(BaseModel):\n    value: Optional[int] = None\n\n"
        "class Foo2Fbar(BaseModel):\n    value: Optional[str] = None\n\n"
        "class Space20key(BaseModel):\n    value: Optional[bool] = None\n\n"
        "class Model(BaseModel):\n    foo_bar: Optional[Foo2Fbar] = None\n"
        "    baz_qux: Optional[Baz7Equx] = None\n"
        "    space_key: Optional[Space20key] = None\n"
    )

    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.py"
    input_file.write_text(json.dumps(schema))
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        expected_output=expected,
        input_file_type="jsonschema",
        ignore_whitespace=True,
    )


@pytest.mark.parametrize(
    ("extra_fields", "output_model", "expected_output"),
    [
        (
            "allow",
            "pydantic.BaseModel",
            "extra_fields_allow.py",
        ),
        (
            "forbid",
            "pydantic.BaseModel",
            "extra_fields_forbid.py",
        ),
        (
            "ignore",
            "pydantic.BaseModel",
            "extra_fields_ignore.py",
        ),
        (
            "allow",
            "pydantic_v2.BaseModel",
            "extra_fields_v2_allow.py",
        ),
        (
            "forbid",
            "pydantic_v2.BaseModel",
            "extra_fields_v2_forbid.py",
        ),
        (
            "ignore",
            "pydantic_v2.BaseModel",
            "extra_fields_v2_ignore.py",
        ),
    ],
)
def test_main_extra_fields(extra_fields: str, output_model: str, expected_output: str, output_file: Path) -> None:
    """Test extra fields configuration."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extra_fields.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--extra-fields", extra_fields, "--output-model-type", output_model],
    )


def test_main_jsonschema_same_name_objects(output_file: Path) -> None:
    """Test objects with same name (see issue #2460)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "same_name_objects.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="same_name_objects.py",
    )


def test_main_jsonschema_forwarding_reference_collapse_root(output_dir: Path) -> None:
    """Test forwarding reference with collapsed root (see issue #1466)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "forwarding_reference",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "forwarding_reference",
        input_file_type="jsonschema",
        extra_args=["--collapse-root-models"],
    )


def test_main_jsonschema_type_alias(output_file: Path) -> None:
    """Test that TypeAliasType is generated for Python 3.9-3.11."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_alias.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="type_alias.py",
        extra_args=["--use-type-alias"],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 23,
    reason="Installed black doesn't support the new 'type' statement",
)
def test_main_jsonschema_type_alias_py312(output_file: Path) -> None:
    """Test that type statement syntax is generated for Python 3.12+ with Pydantic v2."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_alias.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="type_alias_py312.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.12",
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_type_alias_with_field_description(output_file: Path) -> None:
    """Test that TypeAliasType is generated with field descriptions for Python 3.9-3.11."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_alias.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="type_alias_with_field_description.py",
        extra_args=["--use-type-alias", "--use-field-description"],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 23,
    reason="Installed black doesn't support the new 'type' statement",
)
def test_main_jsonschema_type_alias_with_field_description_py312(output_file: Path) -> None:
    """Test that type statement syntax is generated with field descriptions for Python 3.12+ and Pydantic v2."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_alias.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="type_alias_with_field_description_py312.py",
        extra_args=[
            "--use-type-alias",
            "--use-field-description",
            "--target-python-version",
            "3.12",
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_type_mappings(output_file: Path) -> None:
    """Test --type-mappings option to override format-to-type mappings."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_mappings.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="type_mappings.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--type-mappings",
            "binary=string",
        ],
    )


def test_main_jsonschema_type_mappings_with_type_prefix(output_file: Path) -> None:
    """Test --type-mappings option with type+format syntax."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_mappings.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="type_mappings.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--type-mappings",
            "string+binary=string",
        ],
    )


def test_main_jsonschema_type_mappings_to_type_default(output_file: Path) -> None:
    """Test --type-mappings option mapping to a type's default (e.g., binary=integer)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_mappings.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="type_mappings_to_integer.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--type-mappings",
            "binary=integer",
        ],
    )


def test_main_jsonschema_type_mappings_to_boolean(output_file: Path) -> None:
    """Test --type-mappings option mapping to a top-level type (e.g., binary=boolean)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_mappings.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="type_mappings_to_boolean.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--type-mappings",
            "binary=boolean",
        ],
    )


def test_main_jsonschema_type_mappings_invalid_format(output_file: Path) -> None:
    """Test --type-mappings option with invalid format raises error."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_mappings.json",
        output_path=output_file,
        input_file_type="jsonschema",
        expected_exit=Exit.ERROR,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--type-mappings",
            "invalid_without_equals",
        ],
        expected_stderr_contains="Invalid type mapping format",
    )


def test_main_jsonschema_reuse_scope_tree(output_dir: Path) -> None:
    """Test --reuse-scope=tree to deduplicate models across multiple files."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
    )


def test_main_jsonschema_reuse_scope_tree_enum(output_dir: Path) -> None:
    """Test --reuse-scope=tree to deduplicate enum models across multiple files."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_enum",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_enum",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
    )


def test_main_jsonschema_reuse_scope_tree_warning(capsys: pytest.CaptureFixture[str], output_dir: Path) -> None:
    """Test warning when --reuse-scope=tree is used without --reuse-model."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=["--reuse-scope", "tree"],
        capsys=capsys,
        expected_stderr_contains="Warning: --reuse-scope=tree has no effect without --reuse-model",
    )


def test_main_jsonschema_reuse_scope_tree_no_dup(output_dir: Path) -> None:
    """Test --reuse-scope=tree when there are no duplicate models."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_no_dup",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_no_dup",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
    )


def test_main_jsonschema_reuse_scope_tree_self_ref(output_dir: Path) -> None:
    """Test --reuse-scope=tree with self-referencing models."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_self_ref",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_self_ref",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
    )


def test_main_jsonschema_reuse_scope_tree_conflict(capsys: pytest.CaptureFixture[str], output_dir: Path) -> None:
    """Test --reuse-scope=tree error when schema file name conflicts with shared module."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_conflict",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Schema file or directory 'shared' conflicts with the shared module name",
    )


def test_main_jsonschema_reuse_scope_tree_conflict_dir(capsys: pytest.CaptureFixture[str], output_dir: Path) -> None:
    """Test --reuse-scope=tree error when schema directory name conflicts with shared module."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_conflict_dir",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Schema file or directory 'shared' conflicts with the shared module name",
    )


def test_main_jsonschema_reuse_scope_tree_no_conflict_dir(output_dir: Path) -> None:
    """Test --reuse-scope=tree does not error when shared/ dir exists but no duplicates."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_no_conflict_dir",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_no_conflict_dir",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
    )


def test_main_jsonschema_reuse_scope_tree_multi(output_dir: Path) -> None:
    """Test --reuse-scope=tree with multiple files where canonical is not in first module."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_multi",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_multi",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
    )


def test_main_jsonschema_reuse_scope_tree_branch(output_dir: Path) -> None:
    """Test --reuse-scope=tree branch coverage with duplicate in later modules."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_branch",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_branch",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree"],
    )


def test_main_jsonschema_reuse_scope_tree_dataclass(output_dir: Path) -> None:
    """Test --reuse-scope=tree with dataclasses output type (supports inheritance)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_dataclass",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_dataclass",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree", "--output-model-type", "dataclasses.dataclass"],
    )


def test_main_jsonschema_reuse_scope_tree_typeddict(output_dir: Path) -> None:
    """Test --reuse-scope=tree with TypedDict output type (no inheritance, direct reference)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_typeddict",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_typeddict",
        input_file_type="jsonschema",
        extra_args=["--reuse-model", "--reuse-scope", "tree", "--output-model-type", "typing.TypedDict"],
    )


def test_main_jsonschema_empty_items_array(output_file: Path) -> None:
    """Test that arrays with empty items ({}) generate List[Any] instead of bare List."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "empty_items_array.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_jsonschema_hierarchical_aliases_scoped(output_file: Path) -> None:
    """Test hierarchical aliases with scoped format (ClassName.field)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "hierarchical_aliases.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=[
            "--aliases",
            str(ALIASES_DATA_PATH / "hierarchical_aliases_scoped.json"),
        ],
    )


def test_main_jsonschema_multiple_types_with_object(output_file: Path) -> None:
    """Test multiple types in array including object with properties generates Union type."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "multiple_types_with_object.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_jsonschema_type_alias_with_circular_ref_to_class_msgspec(min_version: str, output_file: Path) -> None:
    """Test TypeAlias with circular reference to class generates quoted forward refs."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_alias_with_circular_ref_to_class.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="type_alias_with_circular_ref_to_class_msgspec.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--target-python-version",
            min_version,
        ],
    )


def test_main_jsonschema_enum_object_values(output_file: Path) -> None:
    """Test that enum with object values uses title/name/const for member names (issue #1620)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "enum_object_values.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


def test_main_jsonschema_collapse_root_models_empty_union(output_file: Path) -> None:
    """Test that collapse-root-models with empty union fallback generates Any instead of invalid Union syntax."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_empty_union.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models"],
    )


def test_main_jsonschema_collapse_root_models_with_optional(output_file: Path) -> None:
    """Test that collapse-root-models correctly preserves Optional import when needed."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_with_optional.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models"],
    )


def test_main_jsonschema_collapse_root_models_nested_reference(output_file: Path) -> None:
    """Ensure nested references inside root models still get imported when collapsing."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_nested_reference.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models"],
    )


def test_main_jsonschema_file_url_ref(tmp_path: Path) -> None:
    """Test that file:// URL $ref is resolved correctly."""
    pet_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"],
    }
    pet_file = tmp_path / "pet.json"
    pet_file.write_text(json.dumps(pet_schema))

    main_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"pet": {"$ref": pet_file.as_uri()}},
    }
    main_file = tmp_path / "main.json"
    main_file.write_text(json.dumps(main_schema))

    expected = (
        "# generated by datamodel-codegen:\n"
        "#   filename:  main.json\n\n"
        "from __future__ import annotations\n\n"
        "from typing import Optional\n\n"
        "from pydantic import BaseModel\n\n\n"
        "class Pet(BaseModel):\n"
        "    name: str\n"
        "    age: Optional[int] = None\n\n\n"
        "class Model(BaseModel):\n"
        "    pet: Optional[Pet] = None\n"
    )
    run_main_and_assert(
        input_path=main_file,
        output_path=tmp_path / "output.py",
        input_file_type="jsonschema",
        expected_output=expected,
        ignore_whitespace=True,
        extra_args=["--disable-timestamp"],
    )


def test_main_jsonschema_file_url_ref_percent_encoded(tmp_path: Path) -> None:
    """Test that file:// URL with percent-encoded path is resolved correctly."""
    dir_with_space = tmp_path / "my schemas"
    dir_with_space.mkdir()

    pet_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    pet_file = dir_with_space / "pet.json"
    pet_file.write_text(json.dumps(pet_schema))

    main_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"pet": {"$ref": pet_file.as_uri()}},
    }
    main_file = tmp_path / "main.json"
    main_file.write_text(json.dumps(main_schema))

    expected = (
        "# generated by datamodel-codegen:\n"
        "#   filename:  main.json\n\n"
        "from __future__ import annotations\n\n"
        "from typing import Optional\n\n"
        "from pydantic import BaseModel\n\n\n"
        "class Pet(BaseModel):\n"
        "    name: Optional[str] = None\n\n\n"
        "class Model(BaseModel):\n"
        "    pet: Optional[Pet] = None\n"
    )
    run_main_and_assert(
        input_path=main_file,
        output_path=tmp_path / "output.py",
        input_file_type="jsonschema",
        expected_output=expected,
        ignore_whitespace=True,
        extra_args=["--disable-timestamp"],
    )


@pytest.mark.benchmark
def test_main_jsonschema_root_model_default_value(output_file: Path) -> None:
    """Test RootModel default values are wrapped with type constructors."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_default_value.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_model_default_value.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--set-default-enum-member",
        ],
    )


@pytest.mark.benchmark
def test_main_jsonschema_root_model_default_value_no_annotated(output_file: Path) -> None:
    """Test RootModel default values without --use-annotated flag."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_default_value.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_model_default_value_no_annotated.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--set-default-enum-member",
        ],
    )


@pytest.mark.benchmark
def test_main_jsonschema_root_model_default_value_branches(output_file: Path) -> None:
    """Test RootModel default value branches."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_default_value_branches.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_model_default_value_branches.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
        ],
    )


@pytest.mark.benchmark
def test_main_jsonschema_root_model_default_value_non_root(output_file: Path) -> None:
    """Test that non-RootModel references are not wrapped."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_default_value_non_root.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_model_default_value_non_root.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
        ],
    )


@pytest.mark.benchmark
def test_main_jsonschema_extras_in_oneof(output_file: Path) -> None:
    """Test that extras are preserved in oneOf/anyOf structures (Issue #2403)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extras_in_oneof.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="extras_in_oneof.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--field-include-all-keys",
        ],
    )


def test_main_jsonschema_ref_with_additional_keywords(output_dir: Path) -> None:
    """Test that $ref combined with additional keywords merges properties (Issue #2330)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "ref_with_additional_keywords",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "ref_with_additional_keywords",
        input_file_type="jsonschema",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_jsonschema_reserved_field_name_typed_dict(output_file: Path) -> None:
    """Test that 'schema' field is not renamed in TypedDict (Issue #1833)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reserved_field_name_schema.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="reserved_field_name_schema_typed_dict.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--target-python-version",
            "3.11",
        ],
    )


@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_jsonschema_reserved_field_name_dataclass(output_file: Path) -> None:
    """Test that 'schema' field is not renamed in dataclass (Issue #1833)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reserved_field_name_schema.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="reserved_field_name_schema_dataclass.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--target-python-version",
            "3.11",
        ],
    )


@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_jsonschema_reserved_field_name_pydantic(output_file: Path) -> None:
    """Test that 'schema' field is renamed to 'schema_' with alias in Pydantic (Issue #1833)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reserved_field_name_schema.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="reserved_field_name_schema_pydantic.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.11",
        ],
    )


@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_bundled_schema_with_id_local_file(output_file: Path) -> None:
    """Test bundled schema with $id using local file input (Issue #1798)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "bundled_schema_with_id.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="bundled_schema_with_id.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_bundled_schema_with_id_url(mocker: MockerFixture, output_file: Path) -> None:
    """Test bundled schema with $id using URL input produces same output as local file."""
    schema_path = JSON_SCHEMA_DATA_PATH / "bundled_schema_with_id.json"

    mock_response = mocker.Mock()
    mock_response.text = schema_path.read_text()

    httpx_get_mock = mocker.patch(
        "httpx.get",
        return_value=mock_response,
    )

    run_main_url_and_assert(
        url="https://cdn.example.com/schemas/bundled_schema_with_id.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="bundled_schema_with_id.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
        transform=lambda s: s.replace(
            "#   filename:  https://cdn.example.com/schemas/bundled_schema_with_id.json",
            "#   filename:  bundled_schema_with_id.json",
        ),
    )

    httpx_get_mock.assert_called_once_with(
        "https://cdn.example.com/schemas/bundled_schema_with_id.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=None,
    )


@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_use_frozen_field_pydantic_v2(output_file: Path) -> None:
    """Test --use-frozen-field with Pydantic v2 generates Field(frozen=True) for readOnly fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_frozen_field.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_frozen_field_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-frozen-field",
        ],
    )


@pytest.mark.benchmark
def test_main_use_frozen_field_pydantic_v1(output_file: Path) -> None:
    """Test --use-frozen-field with Pydantic v1 generates Field(allow_mutation=False) for readOnly fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_frozen_field.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_frozen_field_v1.py",
        extra_args=[
            "--output-model-type",
            "pydantic.BaseModel",
            "--use-frozen-field",
        ],
    )


@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_use_frozen_field_no_readonly(output_file: Path) -> None:
    """Test --use-frozen-field with no readOnly fields produces no frozen fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "user.json",  # Has no readOnly fields
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_frozen_field_no_readonly.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-frozen-field",
        ],
    )


@pytest.mark.benchmark
def test_main_use_frozen_field_dataclass(output_file: Path) -> None:
    """Test --use-frozen-field with dataclass silently ignores (no error, no frozen)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_frozen_field.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_frozen_field_dataclass.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--use-frozen-field",
        ],
    )
