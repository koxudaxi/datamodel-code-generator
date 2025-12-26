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
from datamodel_code_generator.model import base as model_base
from tests.conftest import assert_directory_content, freeze_time
from tests.main.conftest import (
    ALIASES_DATA_PATH,
    BLACK_PY313_SKIP,
    DATA_PATH,
    EXPECTED_MAIN_PATH,
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
@pytest.mark.cli_doc(
    options=["--keep-model-order"],
    input_schema="jsonschema/inheritance_forward_ref.json",
    cli_args=["--keep-model-order"],
    golden_output="jsonschema/inheritance_forward_ref_keep_model_order.py",
    related_options=["--collapse-root-models"],
)
def test_main_inheritance_forward_ref_keep_model_order(output_file: Path, tmp_path: Path) -> None:
    """Keep model definition order as specified in schema.

    The `--keep-model-order` flag preserves the original definition order from the schema
    instead of reordering models based on dependencies. This is useful when the order
    of model definitions matters for documentation or readability.
    """
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


@pytest.mark.benchmark
def test_main_type_alias_cycle_keep_model_order(output_file: Path) -> None:
    """Test TypeAlias cycle ordering with keep_model_order."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_alias_cycle.json",
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


@pytest.mark.cli_doc(
    options=["--disable-future-imports"],
    input_schema="jsonschema/keep_model_order_field_references.json",
    cli_args=["--disable-future-imports", "--target-python-version", "3.10"],
    golden_output="main/jsonschema/keep_model_order_field_references.py",
)
@pytest.mark.benchmark
def test_main_keep_model_order_field_references(output_file: Path) -> None:
    """Prevent automatic addition of __future__ imports in generated code.

    The --disable-future-imports option stops the generator from adding
    'from __future__ import annotations' to the output. This is useful when
    you need compatibility with tools or environments that don't support
    postponed evaluation of annotations (PEP 563).

    **Python 3.13+ Deprecation Warning:** When using `from __future__ import annotations`
    with older versions of Pydantic v1 (before 1.10.18), Python 3.13 may raise
    deprecation warnings related to `typing._eval_type()`. To avoid these warnings:

    - Upgrade to Pydantic v1 >= 1.10.18 or Pydantic v2 (recommended)
    - Use this `--disable-future-imports` flag as a workaround
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "keep_model_order_field_references.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=[
            "--keep-model-order",
            "--disable-future-imports",
            "--target-python-version",
            "3.10",
        ],
    )


@pytest.mark.parametrize(
    ("target_python_version", "keep_model_order", "disable_future_imports"),
    [
        ("3.10", False, False),
        ("3.10", False, True),
        ("3.10", True, False),
        ("3.10", True, True),
        ("3.11", True, False),
        ("3.11", True, True),
        ("3.12", True, False),
        ("3.12", True, True),
        ("3.13", True, False),
        ("3.13", True, True),
        ("3.14", True, False),
        ("3.14", True, True),
    ],
)
def test_main_keep_model_order_matrix_keep_model_order_field_references(
    output_file: Path,
    target_python_version: str,
    keep_model_order: bool,
    disable_future_imports: bool,
) -> None:
    """E2E matrix for keep_model_order vs deferred annotations.

    When deferred annotations are enabled (default), field references should not
    force reordering (to avoid meaningless churn). When disabled, ordering must
    satisfy runtime dependency requirements.
    """
    target_version = PythonVersion(target_python_version)
    if not is_supported_in_black(target_version):
        pytest.skip(f"Installed black ({black.__version__}) doesn't support Python {target_python_version}")

    args = [
        "--input",
        str(JSON_SCHEMA_DATA_PATH / "keep_model_order_field_references.json"),
        "--output",
        str(output_file),
        "--input-file-type",
        "jsonschema",
        "--target-python-version",
        target_python_version,
        "--formatters",
        "isort",
    ]
    if keep_model_order:
        args.append("--keep-model-order")
    if disable_future_imports:
        args.append("--disable-future-imports")

    run_main_with_args(args)
    code = output_file.read_text(encoding="utf-8")
    compile(code, str(output_file), "exec")

    if not keep_model_order:
        return

    metadata_index = code.index("class Metadata")
    description_type_index = code.index("class DescriptionType")
    use_deferred_annotations_for_target = target_version.has_native_deferred_annotations or not disable_future_imports
    if use_deferred_annotations_for_target:
        assert description_type_index < metadata_index
    else:
        assert metadata_index < description_type_index

    # For targets without native deferred annotations, validate runtime safety
    # under the current interpreter by executing the generated module.
    if not target_version.has_native_deferred_annotations:
        exec(compile(code, str(output_file), "exec"), {})


@pytest.mark.cli_doc(
    options=["--target-python-version"],
    input_schema="jsonschema/pydantic_v2_model_rebuild_inheritance.json",
    cli_args=["--output-model-type", "pydantic_v2.BaseModel", "--keep-model-order", "--target-python-version", "3.10"],
    golden_output="jsonschema/pydantic_v2_model_rebuild_inheritance.py",
)
@pytest.mark.benchmark
def test_main_pydantic_v2_model_rebuild_inheritance(output_file: Path) -> None:
    """Target Python version for generated code syntax and imports.

    The `--target-python-version` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pydantic_v2_model_rebuild_inheritance.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--keep-model-order",
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
            "--output-model-type",
            "pydantic.BaseModel",
            "--dataclass-arguments",
            '{"slots": true, "order": true}',
        ],
    )


@pytest.mark.cli_doc(
    options=["--keyword-only"],
    input_schema="jsonschema/person.json",
    cli_args=["--output-model-type", "dataclasses.dataclass", "--frozen-dataclasses", "--keyword-only"],
    golden_output="main/jsonschema/general_dataclass_frozen_kw_only.py",
    related_options=["--frozen-dataclasses", "--output-model-type"],
)
def test_main_jsonschema_dataclass_frozen_keyword_only(output_file: Path) -> None:
    """Generate dataclass fields as keyword-only arguments.

    The `--keyword-only` flag generates all dataclass fields as keyword-only,
    requiring explicit parameter names when instantiating models. Combined with
    `--frozen-dataclasses`, creates immutable models with keyword-only constructors.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="general_dataclass_frozen_kw_only.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--frozen-dataclasses",
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
@pytest.mark.cli_doc(
    options=["--output-model-type"],
    input_schema="jsonschema/null_and_array.json",
    cli_args=["--output-model-type", "pydantic.BaseModel"],
    model_outputs={
        "pydantic_v1": "main/jsonschema/null_and_array.py",
        "pydantic_v2": "main/jsonschema/null_and_array_v2.py",
    },
    primary=True,
)
def test_main_null_and_array(output_model: str, expected_output: str, output_file: Path) -> None:
    """Select the output model type (Pydantic v1/v2, dataclasses, TypedDict, msgspec).

    The `--output-model-type` flag specifies which Python data model framework to use
    for the generated code. Supported values include `pydantic.BaseModel`,
    `pydantic_v2.BaseModel`, `dataclasses.dataclass`, `typing.TypedDict`, and
    `msgspec.Struct`.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "null_and_array.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model],
    )


@pytest.mark.cli_doc(
    options=["--use-default"],
    input_schema="jsonschema/use_default_with_const.json",
    cli_args=["--output-model-type", "pydantic_v2.BaseModel", "--use-default"],
    golden_output="jsonschema/use_default_with_const.py",
    related_options=["--strict-nullable"],
)
def test_use_default_pydantic_v2_with_json_schema_const(output_file: Path) -> None:
    """Use default values from schema in generated models.

    The `--use-default` flag allows required fields with default values to be generated
    with their defaults, making them optional to provide when instantiating the model.

    !!! warning "Fields with defaults become nullable"
        When using `--use-default`, fields with default values are generated as nullable
        types (e.g., `str | None` instead of `str`), even if the schema does not allow
        null values.

        If you want fields to strictly follow the schema's type definition (non-nullable),
        use `--strict-nullable` together with `--use-default`.

    !!! note "Future behavior change"
        In a future major version, the default behavior of `--use-default` may change to
        generate non-nullable types that match the schema definition (equivalent to using
        `--strict-nullable`). If you rely on the current nullable behavior, consider
        explicitly handling this in your code.
    """
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
    extra_args = [a for a in [option, "--output-model-type", output_model] if a]
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "complicated_enum.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=extra_args,
    )


@pytest.mark.cli_doc(
    options=["--set-default-enum-member"],
    input_schema="jsonschema/duplicate_enum.json",
    cli_args=["--reuse-model", "--set-default-enum-member"],
    golden_output="jsonschema/json_reuse_enum_default_member.py",
)
@pytest.mark.benchmark
def test_main_json_reuse_enum_default_member(output_file: Path) -> None:
    """Set the first enum member as the default value for enum fields.

    The `--set-default-enum-member` flag configures the code generation behavior.
    """
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


@pytest.mark.cli_doc(
    options=["--class-name"],
    input_schema="jsonschema/invalid_model_name.json",
    cli_args=["--class-name", "ValidModelName"],
    golden_output="main/jsonschema/invalid_model_name.py",
)
def test_main_invalid_model_name(output_file: Path) -> None:
    """Override the auto-generated class name with a custom name.

    The --class-name option allows you to specify a custom class name for the
    generated model. This is useful when the schema title is invalid as a Python
    class name (e.g., starts with a number) or when you want to use a different
    naming convention than what's in the schema.
    """
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
            timeout=30.0,
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
            timeout=30.0,
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
            timeout=30.0,
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


@pytest.mark.cli_doc(
    options=["--snake-case-field"],
    input_schema="jsonschema/invalid_enum_name.json",
    cli_args=["--snake-case-field"],
    golden_output="jsonschema/invalid_enum_name_snake_case_field.py",
    related_options=["--capitalize-enum-members"],
)
def test_main_invalid_enum_name_snake_case_field(output_file: Path) -> None:
    """Convert field names to snake_case format.

    The `--snake-case-field` flag converts camelCase or PascalCase field names
    to snake_case format in the generated Python code, following Python naming
    conventions (PEP 8).
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "invalid_enum_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--snake-case-field"],
    )


@pytest.mark.cli_doc(
    options=["--reuse-model"],
    input_schema="jsonschema/duplicate_enum.json",
    cli_args=["--reuse-model"],
    golden_output="jsonschema/json_reuse_enum.py",
    related_options=["--collapse-root-models"],
)
def test_main_json_reuse_enum(output_file: Path) -> None:
    """Reuse identical model definitions instead of generating duplicates.

    The `--reuse-model` flag detects identical enum or model definitions
    across the schema and generates a single shared definition, reducing
    code duplication in the output.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "duplicate_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--reuse-model"],
    )


@pytest.mark.cli_doc(
    options=["--capitalize-enum-members"],
    input_schema="jsonschema/many_case_enum.json",
    cli_args=["--capitalize-enum-members"],
    golden_output="jsonschema/json_capitalise_enum_members.py",
    related_options=["--snake-case-field"],
    aliases=["--capitalise-enum-members"],
)
def test_main_json_capitalise_enum_members(output_file: Path) -> None:
    """Capitalize enum member names to UPPER_CASE format.

    The `--capitalize-enum-members` flag converts enum member names to
    UPPER_CASE format (e.g., `active` becomes `ACTIVE`), following Python
    naming conventions for constants.
    """
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


@pytest.mark.cli_doc(
    options=["--use-generic-container-types"],
    input_schema="jsonschema/root_model_with_additional_properties.json",
    cli_args=["--use-generic-container-types"],
    golden_output="jsonschema/root_model_with_additional_properties_use_generic_container_types.py",
    related_options=["--use-standard-collections"],
)
def test_main_root_model_with_additional_properties_use_generic_container_types(output_file: Path) -> None:
    """Use typing.Dict/List instead of dict/list for container types.

    The `--use-generic-container-types` flag generates typing module generic
    containers (Dict, List, etc.) instead of built-in types. This is useful for
    Python 3.8 compatibility or when explicit typing imports are preferred.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_with_additional_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--use-generic-container-types"],
    )


@pytest.mark.cli_doc(
    options=["--use-standard-collections"],
    input_schema="jsonschema/root_model_with_additional_properties.json",
    cli_args=["--use-standard-collections"],
    golden_output="jsonschema/root_model_with_additional_properties_use_standard_collections.py",
    related_options=["--use-generic-container-types"],
)
def test_main_root_model_with_additional_properties_use_standard_collections(output_file: Path) -> None:
    """Use built-in dict/list instead of typing.Dict/List.

    The `--use-standard-collections` flag generates built-in container types
    (dict, list) instead of typing module equivalents. This produces cleaner
    code for Python 3.10+ where built-in types support subscripting.
    """
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


@pytest.mark.cli_doc(
    options=["--original-field-name-delimiter"],
    input_schema="jsonschema/space_field_enum.json",
    cli_args=["--snake-case-field", "--original-field-name-delimiter", " "],
    golden_output="main/jsonschema/space_field_enum_snake_case_field.py",
)
def test_main_space_field_enum_snake_case_field(output_file: Path) -> None:
    """Specify delimiter for original field names when using snake-case conversion.

    The `--original-field-name-delimiter` option works with `--snake-case-field` to specify
    the delimiter used in original field names. This is useful when field names contain
    delimiters like spaces or hyphens that should be treated as word boundaries during
    snake_case conversion.
    """
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


@LEGACY_BLACK_SKIP
@pytest.mark.cli_doc(
    options=["--disable-timestamp"],
    input_schema="jsonschema/pattern.json",
    cli_args=["--disable-timestamp"],
    golden_output="jsonschema/pattern.py",
)
def test_main_jsonschema_pattern(output_file: Path) -> None:
    """Disable timestamp in generated file header for reproducible output.

    The `--disable-timestamp` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern.py",
        extra_args=["--disable-timestamp"],
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


def test_main_generate_pydantic_v2_dataclass(tmp_path: Path) -> None:
    """Test generation with pydantic_v2.dataclass output model."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "simple_string.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "generate_pydantic_v2_dataclass.py")


def test_main_generate_pydantic_v2_dataclass_with_config(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with ConfigDict from additionalProperties."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "pydantic_v2_dataclass_config.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_config.py")


def test_main_generate_pydantic_v2_dataclass_additional_props_true(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with additionalProperties: true."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "pydantic_v2_dataclass_additional_props_true.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_additional_props_true.py")


def test_main_generate_pydantic_v2_dataclass_unevaluated_props_true(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with unevaluatedProperties: true."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "unevaluated_properties_true.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "unevaluated_properties_true_dataclass.py")


def test_main_generate_pydantic_v2_base_model_unevaluated_props(tmp_path: Path) -> None:
    """Test pydantic_v2.BaseModel with unevaluatedProperties: false."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "unevaluated_properties.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )

    assert_file_content(output_file, "unevaluated_properties_pydantic_v2.py")


def test_main_generate_pydantic_v2_base_model_unevaluated_props_true(tmp_path: Path) -> None:
    """Test pydantic_v2.BaseModel with unevaluatedProperties: true."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "unevaluated_properties_true.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )

    assert_file_content(output_file, "unevaluated_properties_true_pydantic_v2.py")


def test_main_generate_pydantic_v2_dataclass_unevaluated_props_false(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with unevaluatedProperties: false."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "unevaluated_properties.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "unevaluated_properties_dataclass.py")


def test_main_generate_pydantic_v2_dataclass_use_attribute_docstrings(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with use_attribute_docstrings."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "simple_string.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
        use_attribute_docstrings=True,
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_use_attribute_docstrings.py")


def test_main_generate_pydantic_v2_dataclass_extra_allow(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with extra='allow'."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "simple_string.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
        extra_fields="allow",
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_extra_allow.py")


def test_main_generate_pydantic_v2_dataclass_extra_forbid(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with extra='forbid'."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "simple_string.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
        extra_fields="forbid",
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_extra_forbid.py")


def test_main_generate_pydantic_v2_dataclass_extra_ignore(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with extra='ignore'."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "simple_string.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
        extra_fields="ignore",
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_extra_ignore.py")


def test_main_generate_pydantic_v2_dataclass_nested(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with nested models."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "pydantic_v2_dataclass_nested.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_nested.py")


def test_main_generate_pydantic_v2_dataclass_constraints(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with field constraints."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "pydantic_v2_dataclass_constraints.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_constraints.py")


def test_main_generate_pydantic_v2_dataclass_nested_frozen(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with nested models and frozen=True."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "pydantic_v2_dataclass_nested.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
        frozen_dataclasses=True,
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_nested_frozen.py")


def test_main_generate_pydantic_v2_dataclass_field(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with Field constraints and defaults."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "pydantic_v2_dataclass_field.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_field.py")


def test_main_generate_pydantic_v2_dataclass_enum(tmp_path: Path) -> None:
    """Test pydantic_v2.dataclass with enum types."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "pydantic_v2_dataclass_enum.json").relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2Dataclass,
    )

    assert_file_content(output_file, "pydantic_v2_dataclass_enum.py")


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


def test_main_generate_custom_class_name_generator_keep_underscores(tmp_path: Path) -> None:
    """Test custom_class_name_generator preserves underscores in class names (Issue #1315)."""
    output_file: Path = tmp_path / "output.py"
    input_ = (JSON_SCHEMA_DATA_PATH / "underscore_title.json").relative_to(Path.cwd())
    assert not input_.is_absolute()

    def keep_underscores(name: str) -> str:
        return name

    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        custom_class_name_generator=keep_underscores,
    )

    assert_file_content(output_file, "underscore_title.py")


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
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/relative/animal/pet/pet.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/relative/animal/fur.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/friends.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/food.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/machine/robot.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/drink/coffee.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/drink/tea.json",
                headers=None,
                verify=True,
                follow_redirects=True,
                params=None,
                timeout=30.0,
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
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/relative/animal/pet/pet.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/relative/animal/fur.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/friends.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/food.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/machine/robot.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/drink/coffee.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
                timeout=30.0,
            ),
            call(
                "https://example.com/external_files_in_directory/definitions/drink/tea.json",
                headers=headers_requests,
                verify=bool(not http_ignore_tls),
                follow_redirects=True,
                params=query_parameters_requests,
                timeout=30.0,
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


@pytest.mark.cli_doc(
    options=["--strict-types"],
    input_schema="jsonschema/strict_types.json",
    cli_args=["--strict-types", "str", "bytes", "int", "float", "bool"],
    golden_output="main/jsonschema/strict_types_all.py",
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
def test_main_strict_types_all(output_file: Path) -> None:
    """Enable strict type validation for specified Python types.

    The --strict-types option enforces stricter type checking by preventing implicit
    type coercion for the specified types (str, bytes, int, float, bool). This
    generates StrictStr, StrictBytes, StrictInt, StrictFloat, and StrictBool types
    in Pydantic models, ensuring values match exactly without automatic conversion.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "strict_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--strict-types", "str", "bytes", "int", "float", "bool"],
    )


@pytest.mark.cli_doc(
    options=["--field-constraints"],
    input_schema="jsonschema/strict_types.json",
    cli_args=["--strict-types", "str", "bytes", "int", "float", "bool", "--field-constraints"],
    golden_output="jsonschema/strict_types_all_field_constraints.py",
    related_options=["--strict-types"],
)
def test_main_strict_types_all_with_field_constraints(output_file: Path) -> None:
    """Generate Field() with validation constraints from schema.

    The `--field-constraints` flag generates Pydantic Field() declarations with
    validation constraints (min/max length, pattern, minimum/maximum values, etc.)
    extracted from the JSON Schema, enabling runtime validation.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "strict_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="strict_types_all_field_constraints.py",
        extra_args=["--strict-types", "str", "bytes", "int", "float", "bool", "--field-constraints"],
    )


def test_main_hostname_field_constraints_pydantic_v2(output_file: Path) -> None:
    """Test hostname format uses Field(pattern=) instead of constr with --field-constraints."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "hostname_field_constraints.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="hostname_field_constraints_pydantic_v2.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--field-constraints"],
    )


def test_main_hostname_field_constraints_pydantic_v1(output_file: Path) -> None:
    """Test hostname format uses Field(regex=) instead of constr with --field-constraints for v1."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "hostname_field_constraints.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="hostname_field_constraints_pydantic_v1.py",
        extra_args=["--output-model-type", "pydantic.BaseModel", "--field-constraints"],
    )


def test_main_hostname_field_constraints_strict_pydantic_v1(output_file: Path) -> None:
    """Test hostname format uses StrictStr with --field-constraints and --strict-types."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "hostname_field_constraints.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="hostname_field_constraints_strict_pydantic_v1.py",
        extra_args=["--output-model-type", "pydantic.BaseModel", "--field-constraints", "--strict-types", "str"],
    )


def test_main_hostname_root_type_pydantic_v2(output_file: Path) -> None:
    """Test hostname format in root type uses Field(pattern=) with --field-constraints."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "hostname_root_type.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="hostname_root_type_pydantic_v2.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--field-constraints"],
    )


def test_main_hostname_multiple_types_pydantic_v2(output_file: Path) -> None:
    """Test hostname format with multiple types uses Field(pattern=) with --field-constraints."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "hostname_multiple_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="hostname_multiple_types_pydantic_v2.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--field-constraints"],
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


@pytest.mark.cli_doc(
    options=["--special-field-name-prefix"],
    input_schema="jsonschema/special_enum.json",
    cli_args=["--special-field-name-prefix", "special"],
    golden_output="jsonschema/special_enum_special_field_name_prefix.py",
)
def test_main_jsonschema_special_enum_special_field_name_prefix(output_file: Path) -> None:
    """Prefix to add to special field names (like reserved keywords).

    The `--special-field-name-prefix` flag configures the code generation behavior.
    """
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


@pytest.mark.cli_doc(
    options=["--remove-special-field-name-prefix"],
    input_schema="jsonschema/special_prefix_model.json",
    cli_args=["--remove-special-field-name-prefix"],
    golden_output="jsonschema/special_model_remove_special_field_name_prefix.py",
)
def test_main_jsonschema_special_model_remove_special_field_name_prefix(output_file: Path) -> None:
    """Remove the special prefix from field names.

    The `--remove-special-field-name-prefix` flag configures the code generation behavior.
    """
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
@pytest.mark.cli_doc(
    options=["--use-specialized-enum"],
    input_schema="jsonschema/subclass_enum.json",
    cli_args=["--target-python-version", "3.11", "--use-specialized-enum"],
    golden_output="jsonschema/enum_specialized.py",
    related_options=["--no-use-specialized-enum", "--use-subclass-enum"],
)
def test_main_jsonschema_specialized_enums(output_file: Path) -> None:
    """Generate StrEnum/IntEnum for string/integer enums (Python 3.11+).

    The `--use-specialized-enum` flag generates specialized enum types:
    - `StrEnum` for string enums
    - `IntEnum` for integer enums

    This is the default behavior for Python 3.11+ targets.
    """
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
@pytest.mark.cli_doc(
    options=["--no-use-specialized-enum"],
    input_schema="jsonschema/subclass_enum.json",
    cli_args=["--target-python-version", "3.11", "--no-use-specialized-enum"],
    golden_output="jsonschema/enum_specialized_disable.py",
    related_options=["--use-specialized-enum", "--use-subclass-enum"],
)
def test_main_jsonschema_specialized_enums_disabled(output_file: Path) -> None:
    """Disable specialized enum generation (StrEnum/IntEnum).

    The `--no-use-specialized-enum` flag disables specialized enum types,
    generating standard `Enum` classes instead of `StrEnum`/`IntEnum`.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "subclass_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="enum_specialized_disable.py",
        extra_args=["--target-python-version", "3.11", "--no-use-specialized-enum"],
    )


@pytest.mark.cli_doc(
    options=["--empty-enum-field-name"],
    input_schema="jsonschema/special_enum.json",
    cli_args=["--empty-enum-field-name", "empty"],
    golden_output="jsonschema/special_enum_empty_enum_field_name.py",
)
def test_main_jsonschema_special_enum_empty_enum_field_name(output_file: Path) -> None:
    """Name for empty string enum field values.

    The `--empty-enum-field-name` flag configures the code generation behavior.
    """
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
@pytest.mark.cli_doc(
    options=["--union-mode"],
    input_schema="jsonschema/combine_any_of_object.json",
    cli_args=["--union-mode", "left_to_right", "--output-model-type", "pydantic_v2.BaseModel"],
    golden_output="jsonschema/combine_any_of_object_left_to_right.py",
)
def test_main_jsonschema_combine_any_of_object(
    union_mode: str | None, output_model: str, expected_output: str, output_file: Path
) -> None:
    """Union mode for combining anyOf/oneOf schemas (smart or left_to_right).

    The `--union-mode` flag configures the code generation behavior.
    """
    extra_args = ["--output-model-type", output_model]
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
        (["--output-model-type", "pydantic_v2.BaseModel"], "jsonschema_root_model_ordering.py"),
        (
            ["--output-model-type", "pydantic_v2.BaseModel", "--keep-model-order"],
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


@pytest.mark.cli_doc(
    options=["--field-include-all-keys"],
    input_schema="jsonschema/person.json",
    cli_args=["--field-include-all-keys"],
    golden_output="jsonschema/general.py",
)
@pytest.mark.benchmark
def test_main_jsonschema_field_include_all_keys(output_file: Path) -> None:
    """Include all schema keys in Field() json_schema_extra.

    The `--field-include-all-keys` flag configures the code generation behavior.
    """
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
@pytest.mark.cli_doc(
    options=["--field-extra-keys-without-x-prefix"],
    input_schema="jsonschema/extras.json",
    cli_args=["--field-include-all-keys", "--field-extra-keys-without-x-prefix", "x-repr"],
    model_outputs={
        "pydantic_v1": "main/jsonschema/field_extras_field_include_all_keys.py",
        "pydantic_v2": "main/jsonschema/field_extras_field_include_all_keys_v2.py",
    },
)
def test_main_jsonschema_field_extras_field_include_all_keys(
    output_model: str, expected_output: str, output_file: Path
) -> None:
    """Include schema extension keys in Field() without requiring 'x-' prefix.

    The --field-extra-keys-without-x-prefix option allows you to specify custom
    schema extension keys that should be included in Pydantic Field() extras without
    the 'x-' prefix requirement. For example, 'x-repr' in the schema becomes 'repr'
    in Field(). This is useful for custom schema extensions and vendor-specific metadata.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extras.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--output-model-type",
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
@pytest.mark.cli_doc(
    options=["--field-extra-keys"],
    input_schema="jsonschema/extras.json",
    cli_args=["--field-extra-keys", "key2", "--field-extra-keys-without-x-prefix", "x-repr"],
    model_outputs={
        "pydantic_v1": "main/jsonschema/field_extras_field_extra_keys.py",
        "pydantic_v2": "main/jsonschema/field_extras_field_extra_keys_v2.py",
    },
)
def test_main_jsonschema_field_extras_field_extra_keys(
    output_model: str, expected_output: str, output_file: Path
) -> None:
    """Include specific extra keys in Field() definitions.

    The `--field-extra-keys` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extras.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--output-model-type",
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
        extra_args=["--output-model-type", output_model],
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


@pytest.mark.cli_doc(
    options=["--base-class-map"],
    input_schema="jsonschema/base_class_map.json",
    cli_args=[
        "--base-class-map",
        '{"Person": "custom.bases.PersonBase", "Animal": "custom.bases.AnimalBase"}',
    ],
    golden_output="base_class_map.py",
    related_options=["--base-class"],
)
def test_main_jsonschema_base_class_map(output_file: Path) -> None:
    """Test --base-class-map option for model-specific base classes."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "base_class_map.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="base_class_map.py",
        extra_args=[
            "--base-class-map",
            '{"Person": "custom.bases.PersonBase", "Animal": "custom.bases.AnimalBase"}',
        ],
    )


def test_long_description(output_file: Path) -> None:
    """Test long description handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "long_description.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
    )


@pytest.mark.cli_doc(
    options=["--wrap-string-literal"],
    input_schema="jsonschema/long_description.json",
    cli_args=["--wrap-string-literal"],
    golden_output="jsonschema/long_description_wrap_string_literal.py",
)
def test_long_description_wrap_string_literal(output_file: Path) -> None:
    """Wrap long string literals across multiple lines.

    The `--wrap-string-literal` flag breaks long string literals (like descriptions)
    across multiple lines for better readability, instead of having very long
    single-line strings in the generated code.
    """
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


@LEGACY_BLACK_SKIP
def test_jsonschema_titles(output_file: Path) -> None:
    """Test JSON Schema title handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "titles.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="titles.py",
    )


@LEGACY_BLACK_SKIP
@pytest.mark.cli_doc(
    options=["--use-title-as-name"],
    input_schema="jsonschema/titles.json",
    cli_args=["--use-title-as-name"],
    golden_output="jsonschema/titles_use_title_as_name.py",
    related_options=["--class-name"],
)
def test_jsonschema_titles_use_title_as_name(output_file: Path) -> None:
    """Use schema title as the generated class name.

    The `--use-title-as-name` flag uses the `title` property from the schema
    as the class name instead of deriving it from the property name or path.
    This is useful when schemas have descriptive titles that should be preserved.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "titles.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="titles_use_title_as_name.py",
        extra_args=["--use-title-as-name"],
    )


@LEGACY_BLACK_SKIP
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


@pytest.mark.parametrize(
    ("extra_args", "expected_suffix"),
    [
        (["--treat-dot-as-module"], "treat_dot_as_module"),
        (None, "treat_dot_not_as_module"),
        (["--no-treat-dot-as-module"], "treat_dot_not_as_module"),
    ],
)
def test_treat_dot_as_module(extra_args: list[str] | None, expected_suffix: str, output_dir: Path) -> None:
    """Test dot notation as module separator."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "treat_dot_as_module",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / expected_suffix,
        extra_args=extra_args,
    )


@pytest.mark.cli_doc(
    options=["--treat-dot-as-module"],
    input_schema="jsonschema/treat_dot_as_module_single",
    cli_args=["--treat-dot-as-module"],
    golden_output="jsonschema/treat_dot_as_module_single/",
)
def test_treat_dot_as_module_single_file(output_dir: Path) -> None:
    """Treat dots in schema names as module separators.

    The `--treat-dot-as-module` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "treat_dot_as_module_single",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "treat_dot_as_module_single",
        extra_args=["--treat-dot-as-module"],
    )


@pytest.mark.cli_doc(
    options=["--no-treat-dot-as-module"],
    input_schema="jsonschema/treat_dot_as_module_single",
    cli_args=["--no-treat-dot-as-module"],
    golden_output="jsonschema/treat_dot_as_module_single_no_treat/",
    primary=True,
)
def test_no_treat_dot_as_module_single_file(output_dir: Path) -> None:
    """Keep dots in schema names as underscores for flat output.

    The `--no-treat-dot-as-module` flag prevents splitting dotted schema names.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "treat_dot_as_module_single",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "treat_dot_as_module_single_no_treat",
        extra_args=["--no-treat-dot-as-module"],
    )


@pytest.mark.parametrize(
    ("extra_args", "expected_suffix"),
    [
        (["--treat-dot-as-module"], "treat_dot_single"),
        (None, "no_treat_dot_single"),
        (["--no-treat-dot-as-module"], "no_treat_dot_single"),
    ],
)
def test_treat_dot_as_module_version_style(
    extra_args: list[str] | None, expected_suffix: str, output_dir: Path
) -> None:
    """Test dotted version-style schema names (e.g., v0.0.39.job.json)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "no_treat_dot_single",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / expected_suffix,
        extra_args=extra_args,
    )


@pytest.mark.parametrize(
    ("extra_args", "expected_suffix"),
    [
        (["--treat-dot-as-module"], "treat_dot_complex_treat"),
        (None, "treat_dot_complex_no_treat"),
        (["--no-treat-dot-as-module"], "treat_dot_complex_no_treat"),
    ],
)
def test_treat_dot_as_module_complex_refs(extra_args: list[str] | None, expected_suffix: str, output_dir: Path) -> None:
    """Test dotted schema names with cross-file references."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "treat_dot_complex",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / expected_suffix,
        extra_args=extra_args,
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


def test_main_jsonschema_unevaluated_properties(output_file: Path) -> None:
    """Test unevaluatedProperties: false generates extra='forbid'."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "unevaluated_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="unevaluated_properties.py",
    )


def test_main_jsonschema_unevaluated_properties_true(output_file: Path) -> None:
    """Test unevaluatedProperties: true generates extra='allow'."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "unevaluated_properties_true.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="unevaluated_properties_true.py",
    )


def test_main_jsonschema_unevaluated_properties_schema(output_file: Path) -> None:
    """Test unevaluatedProperties as JsonSchemaObject triggers traversal."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "unevaluated_properties_schema.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="unevaluated_properties_schema.py",
    )


def test_main_jsonschema_unevaluated_properties_multiple_types(output_file: Path) -> None:
    """Test unevaluatedProperties with multiple types triggers _set_schema_metadata."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "unevaluated_properties_multiple_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="unevaluated_properties_multiple_types.py",
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


@pytest.mark.cli_doc(
    options=["--enum-field-as-literal"],
    input_schema="jsonschema/oneof_const_enum_nested.yaml",
    cli_args=["--enum-field-as-literal", "all"],
    golden_output="main/jsonschema/oneof_const_enum_nested_literal.py",
)
def test_main_jsonschema_oneof_const_enum_nested_literal(output_file: Path) -> None:
    """Generate Literal types instead of Enums for fields with enumerated values.

    The --enum-field-as-literal option replaces Enum classes with Literal types for
    fields that have a fixed set of allowed values. Use 'all' to convert all enum
    fields, or 'one' to only convert enums with a single value. This produces more
    concise type hints and avoids creating Enum classes when not needed.
    """
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


@pytest.mark.cli_doc(
    options=["--disable-warnings"],
    input_schema="jsonschema/all_of_with_object.json",
    cli_args=["--disable-warnings"],
    golden_output="main/jsonschema/all_of_with_object.py",
)
@pytest.mark.filterwarnings("error")
def test_main_disable_warnings(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Suppress warning messages during code generation.

    The --disable-warnings option silences all warning messages that the generator
    might emit during processing (e.g., about unsupported features, ambiguous schemas,
    or potential issues). Useful for clean output in CI/CD pipelines.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_of_with_object.json",
        output_path=output_file,
        capsys=capsys,
        assert_no_stderr=True,
        input_file_type="jsonschema",
        extra_args=["--disable-warnings"],
    )


@LEGACY_BLACK_SKIP
def test_main_jsonschema_pattern_properties_by_reference(output_file: Path) -> None:
    """Test pattern properties by reference."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern_properties_by_reference.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern_properties_by_reference.py",
    )


def test_main_jsonschema_copy_deep_pattern_properties(output_file: Path) -> None:
    """Test copy_deep properly preserves dict_key from patternProperties during allOf inheritance."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "copy_deep_pattern_properties.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="copy_deep_pattern_properties.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_jsonschema_pattern_properties_boolean(output_file: Path) -> None:
    """Test patternProperties with boolean values (true/false) as allowed in JSON Schema 2020-12."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern_properties_boolean.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern_properties_boolean.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_pattern_properties_merge(output_file: Path) -> None:
    """Test merging multiple patternProperties with same value type into single regex pattern."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern_properties_merge.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern_properties_merge.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_pattern_properties_all_false(output_file: Path) -> None:
    """Test patternProperties with all false values are ignored."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pattern_properties_all_false.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="pattern_properties_all_false.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_pattern(output_file: Path) -> None:
    """Test propertyNames with pattern constraint generates dict with constr key."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_pattern.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_pattern.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_enum(output_file: Path) -> None:
    """Test propertyNames with enum constraint generates dict with Literal key."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_enum.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_min_max_length(output_file: Path) -> None:
    """Test propertyNames with minLength/maxLength constraints generates dict with constr key."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_min_max_length.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_min_max_length.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_no_additional(output_file: Path) -> None:
    """Test propertyNames without additionalProperties generates dict with Any value type."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_no_additional.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_no_additional.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_nested(output_file: Path) -> None:
    """Test propertyNames in nested object property."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_nested.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_nested.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_enum_integers(output_file: Path) -> None:
    """Test propertyNames with enum of integers only falls back to str key."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_enum_integers.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_enum_integers.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_allof_ref(output_file: Path) -> None:
    """Test propertyNames in allOf with $ref."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_allof_ref.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_allof_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_ref_enum(output_file: Path) -> None:
    """Test propertyNames with $ref to enum definition uses enum type as dict key."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_ref_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_ref_enum.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_jsonschema_property_names_anyof_ref(output_file: Path) -> None:
    """Test propertyNames with anyOf containing $refs uses union of enum types as dict key."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "property_names_anyof_ref.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="property_names_anyof_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
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
            "3.10",
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


@pytest.mark.cli_doc(
    options=["--use-double-quotes"],
    input_schema="jsonschema/all_of_any_of_base_class_ref.json",
    cli_args=["--use-double-quotes"],
    golden_output="main/jsonschema/all_of_any_of_base_class_ref.py",
)
def test_main_all_of_any_of_base_class_ref(output_file: Path) -> None:
    """Use double quotes for string literals in generated code.

    The --use-double-quotes option formats all string literals in the generated
    Python code with double quotes instead of the default single quotes. This
    helps maintain consistency with codebases that prefer double-quote formatting.
    """
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


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support Python version 3.11",
)
def test_main_typed_dict_enum_field_as_literal_none(output_file: Path) -> None:
    """Test TypedDict with enum_field_as_literal=none."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "enum_literal_typed_dict.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="typed_dict_enum_literal_none.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--enum-field-as-literal",
            "none",
            "--target-python-version",
            "3.11",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support Python version 3.11",
)
def test_main_typed_dict_enum_field_as_literal_one(output_file: Path) -> None:
    """Test TypedDict with enum_field_as_literal=one."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "enum_literal_typed_dict.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="typed_dict_enum_literal_one.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--enum-field-as-literal",
            "one",
            "--target-python-version",
            "3.11",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support Python version 3.11",
)
def test_main_typed_dict_enum_field_as_literal_all(output_file: Path) -> None:
    """Test TypedDict with enum_field_as_literal=all."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "enum_literal_typed_dict.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="typed_dict_enum_literal_all.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--enum-field-as-literal",
            "all",
            "--target-python-version",
            "3.11",
        ],
    )


@pytest.mark.cli_doc(
    options=["--enum-field-as-literal-map"],
    input_schema="jsonschema/enum_field_as_literal_map.json",
    cli_args=["--enum-field-as-literal-map", '{"status": "literal"}'],
    golden_output="jsonschema/enum_field_as_literal_map.py",
)
def test_main_enum_field_as_literal_map(output_file: Path) -> None:
    """Test --enum-field-as-literal-map for per-field enum/literal control."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "enum_field_as_literal_map.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="enum_field_as_literal_map.py",
        extra_args=[
            "--enum-field-as-literal-map",
            '{"status": "literal"}',
        ],
    )


def test_main_enum_field_as_literal_map_override_global(output_file: Path) -> None:
    """Test --enum-field-as-literal-map overrides global --enum-field-as-literal."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "enum_field_as_literal_map.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="enum_field_as_literal_map_override.py",
        extra_args=[
            "--enum-field-as-literal",
            "all",
            "--enum-field-as-literal-map",
            '{"priority": "enum"}',
        ],
    )


def test_main_x_enum_field_as_literal(output_file: Path) -> None:
    """Test x-enum-field-as-literal schema extension for per-field control."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "x_enum_field_as_literal.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="x_enum_field_as_literal.py",
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
        extra_args=["--output-model-type", output_model, "--target-python-version", min_version],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "prefix_items.py",
        ),
        (
            "msgspec.Struct",
            "prefix_items_msgspec.py",
        ),
    ],
)
@freeze_time("2019-07-26")
@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 24,
    reason="Installed black doesn't support the new style",
)
def test_main_jsonschema_prefix_items(
    output_model: str, expected_output: str, min_version: str, output_file: Path
) -> None:
    """Test prefix items handling."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "prefix_items.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model, "--target-python-version", min_version],
    )


@freeze_time("2019-07-26")
@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 24,
    reason="Installed black doesn't support the new style",
)
def test_main_jsonschema_prefix_items_no_tuple(min_version: str, output_file: Path) -> None:
    """Test prefix items with minItems != maxItems falls back to list."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "prefix_items_no_tuple.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="prefix_items_no_tuple.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--target-python-version", min_version],
    )


@freeze_time("2019-07-26")
@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 24,
    reason="Installed black doesn't support the new style",
)
@pytest.mark.cli_doc(
    options=["--use-tuple-for-fixed-items"],
    input_schema="jsonschema/items_array_tuple.json",
    cli_args=["--use-tuple-for-fixed-items"],
    golden_output="jsonschema/items_array_tuple.py",
)
def test_main_jsonschema_items_array_tuple(min_version: str, output_file: Path) -> None:
    """Generate tuple types for arrays with items array syntax.

    When `--use-tuple-for-fixed-items` is enabled and an array has `items` as an array
    with `minItems == maxItems == len(items)`, generate a tuple type instead of a list.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "items_array_tuple.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="items_array_tuple.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            min_version,
            "--use-tuple-for-fixed-items",
        ],
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
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--target-python-version", min_version],
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
        extra_args=["--output-model-type", output_model, "--target-python-version", min_version],
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
            "--target-python-version",
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
        extra_args=["--output-model-type", output_model, "--target-python-version", min_version],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "time_delta_pydantic_v2.py",
        ),
        (
            "msgspec.Struct",
            "time_delta_msgspec.py",
        ),
    ],
)
def test_main_jsonschema_time_delta(
    output_model: str, expected_output: str, min_version: str, output_file: Path
) -> None:
    """Test time-delta type handling for number format."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "time_delta.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model, "--target-python-version", min_version],
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


def test_main_jsonschema_field_has_same_name_rename_type(output_file: Path) -> None:
    """Test field type collision with rename-type strategy."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "field_has_same_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="field_has_same_name_rename_type.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--field-type-collision-strategy",
            "rename-type",
        ],
    )


@pytest.mark.cli_doc(
    options=["--field-type-collision-strategy"],
    input_schema="jsonschema/field_has_same_name.json",
    cli_args=[
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--field-type-collision-strategy",
        "rename-type",
    ],
    golden_output="jsonschema/field_has_same_name_rename_type.py",
)
def test_main_jsonschema_field_has_same_name_rename_type_cli_doc(output_file: Path) -> None:
    """Rename type class instead of field when names collide (Pydantic v2 only).

    The `--field-type-collision-strategy` flag controls how field name and type name
    collisions are resolved. With `rename-type`, the type class is renamed with a suffix
    to preserve the original field name, instead of renaming the field and adding an alias.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "field_has_same_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="field_has_same_name_rename_type.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--field-type-collision-strategy",
            "rename-type",
        ],
    )


def test_main_jsonschema_field_type_collision_rename_type_double(output_file: Path) -> None:
    """Test field type collision with rename-type strategy when schema has existing _1 suffix."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "field_type_collision_rename_type_double.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="field_type_collision_rename_type_double.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--field-type-collision-strategy",
            "rename-type",
        ],
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
        "from pydantic import BaseModel\n\n"
        "class FooBar(BaseModel):\n    value: str | None = None\n\n"
        "class BazQux(BaseModel):\n    value: int | None = None\n\n"
        "class Baz0qux(BaseModel):\n    value: int | None = None\n\n"
        "class Foo1bar(BaseModel):\n    value: str | None = None\n\n"
        "class Model(BaseModel):\n    foo_bar: Foo1bar | None = None\n    baz_qux: Baz0qux | None = None\n"
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
        "from pydantic import BaseModel\n\n"
        "class FooBar(BaseModel):\n    value: str | None = None\n\n"
        "class BazQux(BaseModel):\n    value: int | None = None\n\n"
        "class SpaceKey(BaseModel):\n    value: bool | None = None\n\n"
        "class Baz7Equx(BaseModel):\n    value: int | None = None\n\n"
        "class Foo2Fbar(BaseModel):\n    value: str | None = None\n\n"
        "class Space20key(BaseModel):\n    value: bool | None = None\n\n"
        "class Model(BaseModel):\n    foo_bar: Foo2Fbar | None = None\n"
        "    baz_qux: Baz7Equx | None = None\n"
        "    space_key: Space20key | None = None\n"
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


@pytest.mark.cli_doc(
    options=["--use-generic-base-class"],
    input_schema="jsonschema/extra_fields.json",
    cli_args=["--extra-fields", "forbid", "--output-model-type", "pydantic_v2.BaseModel", "--use-generic-base-class"],
    golden_output="jsonschema/use_generic_base_class.py",
)
def test_main_use_generic_base_class(output_file: Path) -> None:
    """Generate a shared base class with model configuration to avoid repetition (DRY)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extra_fields.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class.py",
        extra_args=[
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_populate_by_name(output_file: Path) -> None:
    """Test --use-generic-base-class with --allow-population-by-field-name."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_populate_by_name.py",
        extra_args=[
            "--allow-population-by-field-name",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_target_pydantic_v2_11(output_file: Path) -> None:
    """Test --use-generic-base-class with --target-pydantic-version 2.11."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_target_pydantic_v2_11.py",
        extra_args=[
            "--allow-population-by-field-name",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
            "--target-pydantic-version",
            "2.11",
        ],
    )


def test_main_allof_list_any_inheritance(output_file: Path) -> None:
    """Test allOf with List[Any] type inheritance from parent."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "allof_list_any_inheritance.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="allof_list_any_inheritance.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_use_generic_base_class_allow_extra(output_file: Path) -> None:
    """Test --use-generic-base-class with --allow-extra-fields."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_allow_extra.py",
        extra_args=[
            "--allow-extra-fields",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_frozen(output_file: Path) -> None:
    """Test --use-generic-base-class with --enable-faux-immutability."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_frozen.py",
        extra_args=[
            "--enable-faux-immutability",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_attr_docstrings(output_file: Path) -> None:
    """Test --use-generic-base-class with --use-attribute-docstrings."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_attr_docstrings.py",
        extra_args=[
            "--use-attribute-docstrings",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_dataclass(output_file: Path) -> None:
    """Test --use-generic-base-class with dataclasses (no effect)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_dataclass.py",
        extra_args=[
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "dataclasses.dataclass",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_enum_only(output_file: Path) -> None:
    """Test --use-generic-base-class with enum-only schema (no ProjectBaseModel)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_enum_only.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_enum_only.py",
        extra_args=[
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_with_inheritance(output_file: Path) -> None:
    """Test --use-generic-base-class preserves schema inheritance (allOf)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_with_inheritance.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_with_inheritance.py",
        extra_args=[
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_module_split(output_dir: Path) -> None:
    """Test --use-generic-base-class with module split mode (cross-module inheritance)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_with_inheritance.json",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=[
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
            "--module-split-mode",
            "single",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "jsonschema" / "use_generic_base_class_module_split",
    )


def test_main_use_generic_base_class_deep_inheritance(output_dir: Path) -> None:
    """Test --use-generic-base-class with deep inheritance chain across modules."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_deep_inheritance.json",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=[
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
            "--module-split-mode",
            "single",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "jsonschema" / "use_generic_base_class_deep_inheritance",
    )


def test_main_use_generic_base_class_multi_root(output_dir: Path) -> None:
    """Test --use-generic-base-class with multiple independent inheritance trees."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_multi_root.json",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=[
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
            "--module-split-mode",
            "single",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "jsonschema" / "use_generic_base_class_multi_root",
    )


def test_main_use_generic_base_class_circular(output_dir: Path) -> None:
    """Test --use-generic-base-class with circular references (uses _internal.py pattern)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_circular.json",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=[
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-base-class",
            "--module-split-mode",
            "single",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "jsonschema" / "use_generic_base_class_circular",
    )


def test_main_use_generic_base_class_msgspec(output_file: Path) -> None:
    """Test --use-generic-base-class with msgspec.Struct."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_msgspec.py",
        extra_args=[
            "--allow-population-by-field-name",
            "--enable-faux-immutability",
            "--output-model-type",
            "msgspec.Struct",
            "--use-generic-base-class",
        ],
    )


def test_main_use_generic_base_class_msgspec_forbid(output_file: Path) -> None:
    """Test --use-generic-base-class with msgspec.Struct and --extra-fields forbid."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_generic_base_class_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_generic_base_class_msgspec_forbid.py",
        extra_args=[
            "--enable-faux-immutability",
            "--extra-fields",
            "forbid",
            "--output-model-type",
            "msgspec.Struct",
            "--use-generic-base-class",
        ],
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


@pytest.mark.cli_doc(
    options=["--use-type-alias"],
    input_schema="jsonschema/type_alias.json",
    cli_args=["--use-type-alias"],
    golden_output="jsonschema/type_alias.py",
)
def test_main_jsonschema_type_alias(output_file: Path) -> None:
    """Generate TypeAlias for root models instead of wrapper classes.

    The `--use-type-alias` flag configures the code generation behavior.
    """
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


@pytest.mark.cli_doc(
    options=["--use-field-description"],
    input_schema="jsonschema/type_alias.json",
    cli_args=["--use-type-alias", "--use-field-description"],
    golden_output="jsonschema/type_alias_with_field_description.py",
)
def test_main_jsonschema_type_alias_with_field_description(output_file: Path) -> None:
    """Include schema descriptions as Field docstrings.

    The `--use-field-description` flag extracts the `description` property from
    schema fields and includes them as docstrings or Field descriptions in the
    generated models, preserving documentation from the original schema.
    """
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


@pytest.mark.cli_doc(
    options=["--type-mappings"],
    input_schema="jsonschema/type_mappings.json",
    cli_args=["--output-model-type", "pydantic_v2.BaseModel", "--type-mappings", "binary=string"],
    golden_output="jsonschema/type_mappings.py",
)
def test_main_jsonschema_type_mappings(output_file: Path) -> None:
    """Override default type mappings for schema formats.

    The `--type-mappings` flag configures the code generation behavior.
    """
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


@pytest.mark.cli_doc(
    options=["--reuse-scope"],
    input_schema="jsonschema/reuse_scope_tree",
    cli_args=["--reuse-model", "--reuse-scope", "tree"],
    golden_output="jsonschema/reuse_scope_tree",
)
def test_main_jsonschema_reuse_scope_tree(output_dir: Path) -> None:
    """Scope for model reuse detection (root or tree).

    The `--reuse-scope` flag configures the code generation behavior.
    """
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


def test_main_jsonschema_reuse_scope_tree_dataclass_frozen(output_dir: Path) -> None:
    """Test --reuse-scope=tree with frozen dataclasses preserves frozen in inherited models."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree_dataclass",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "reuse_scope_tree_dataclass_frozen",
        input_file_type="jsonschema",
        extra_args=[
            "--reuse-model",
            "--reuse-scope",
            "tree",
            "--output-model-type",
            "dataclasses.dataclass",
            "--frozen-dataclasses",
        ],
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


@pytest.mark.cli_doc(
    options=["--aliases"],
    input_schema="jsonschema/hierarchical_aliases.json",
    cli_args=["--aliases", "aliases/hierarchical_aliases_scoped.json"],
    golden_output="jsonschema/jsonschema_hierarchical_aliases_scoped.py",
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


@pytest.mark.cli_doc(
    options=["--collapse-root-models"],
    input_schema="jsonschema/collapse_root_models_empty_union.json",
    cli_args=["--collapse-root-models"],
    golden_output="main/jsonschema/jsonschema_collapse_root_models_empty_union.py",
)
def test_main_jsonschema_collapse_root_models_empty_union(output_file: Path) -> None:
    """Inline root model definitions instead of creating separate wrapper classes.

    The --collapse-root-models option simplifies generated code by collapsing
    root-level models (top-level type aliases) directly into their usage sites.
    This eliminates unnecessary wrapper classes and produces more concise output,
    especially useful when schemas define simple root types or type aliases.
    """
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


@pytest.mark.cli_doc(
    options=["--collapse-root-models-name-strategy"],
    input_schema="jsonschema/collapse_root_models_name_strategy_child.json",
    cli_args=["--collapse-root-models", "--collapse-root-models-name-strategy", "child"],
    golden_output="main/jsonschema/jsonschema_collapse_root_models_name_strategy_child.py",
    related_options=["--collapse-root-models"],
)
def test_main_jsonschema_collapse_root_models_name_strategy_child(output_file: Path) -> None:
    """Select which name to keep when collapsing root models with object references.

    The --collapse-root-models-name-strategy option controls naming when collapsing
    root models. 'child' keeps the inner model's name, 'parent' uses the wrapper's name.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_child.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models", "--collapse-root-models-name-strategy", "child"],
    )


def test_main_jsonschema_collapse_root_models_name_strategy_parent(output_file: Path) -> None:
    """Test collapse-root-models with parent name strategy uses wrapper's name for inner model."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_parent.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models", "--collapse-root-models-name-strategy", "parent"],
    )


def test_main_jsonschema_collapse_root_models_name_strategy_requires_collapse_root_models(
    output_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that --collapse-root-models-name-strategy requires --collapse-root-models."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_parent.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--collapse-root-models-name-strategy", "parent"],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="--collapse-root-models-name-strategy requires --collapse-root-models",
    )


def test_main_jsonschema_collapse_root_models_name_strategy_multiple_wrappers(output_file: Path) -> None:
    """Test that parent strategy warns and skips when inner model has multiple wrappers."""
    with pytest.warns(UserWarning, match="Cannot apply 'parent' strategy.*multiple root models"):
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_multiple_wrappers.json",
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            extra_args=["--collapse-root-models", "--collapse-root-models-name-strategy", "parent"],
        )


def test_main_jsonschema_collapse_root_models_name_strategy_direct_refs(output_file: Path) -> None:
    """Test that parent strategy warns and skips when inner model has direct references."""
    with pytest.warns(UserWarning, match="Cannot apply 'parent' strategy.*directly referenced"):
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_direct_refs.json",
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            extra_args=["--collapse-root-models", "--collapse-root-models-name-strategy", "parent"],
        )


def test_main_jsonschema_collapse_root_models_name_strategy_with_inheritance(output_file: Path) -> None:
    """Test collapse-root-models with parent strategy when inner model has derived classes."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_with_inheritance.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models", "--collapse-root-models-name-strategy", "parent"],
    )


@pytest.mark.parametrize("output_model", ["pydantic.BaseModel", "pydantic_v2.BaseModel"])
def test_main_jsonschema_collapse_root_models_name_strategy_nested_wrappers_child(
    output_model: str, output_file: Path
) -> None:
    """Test nested wrappers with child strategy - all wrappers collapsed."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_nested_wrappers.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="jsonschema_collapse_root_models_name_strategy_nested_wrappers_child.py",
        extra_args=[
            "--collapse-root-models",
            "--collapse-root-models-name-strategy",
            "child",
            "--output-model-type",
            output_model,
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_file"),
    [
        ("pydantic.BaseModel", "jsonschema_collapse_root_models_name_strategy_nested_wrappers_parent.py"),
        ("pydantic_v2.BaseModel", "jsonschema_collapse_root_models_name_strategy_nested_wrappers_parent_v2.py"),
    ],
)
def test_main_jsonschema_collapse_root_models_name_strategy_nested_wrappers_parent(
    output_model: str, expected_file: str, output_file: Path
) -> None:
    """Test nested wrappers with parent strategy - partial collapse due to multiple refs."""
    with pytest.warns(UserWarning, match="Cannot apply 'parent' strategy.*multiple root models"):
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_nested_wrappers.json",
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=expected_file,
            extra_args=[
                "--collapse-root-models",
                "--collapse-root-models-name-strategy",
                "parent",
                "--output-model-type",
                output_model,
            ],
        )


@pytest.mark.parametrize("output_model", ["pydantic.BaseModel", "pydantic_v2.BaseModel"])
def test_main_jsonschema_collapse_root_models_name_strategy_complex_child(output_model: str, output_file: Path) -> None:
    """Test complex schema with multiple wrappers and inheritance using child strategy."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_complex.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="jsonschema_collapse_root_models_name_strategy_complex_child.py",
        extra_args=[
            "--collapse-root-models",
            "--collapse-root-models-name-strategy",
            "child",
            "--output-model-type",
            output_model,
        ],
    )


@pytest.mark.parametrize("output_model", ["pydantic.BaseModel", "pydantic_v2.BaseModel"])
def test_main_jsonschema_collapse_root_models_name_strategy_complex_parent(
    output_model: str, output_file: Path
) -> None:
    """Test complex schema with multiple wrappers and inheritance using parent strategy."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "collapse_root_models_name_strategy_complex.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="jsonschema_collapse_root_models_name_strategy_complex_parent.py",
        extra_args=[
            "--collapse-root-models",
            "--collapse-root-models-name-strategy",
            "parent",
            "--output-model-type",
            output_model,
        ],
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
        "from pydantic import BaseModel\n\n\n"
        "class Pet(BaseModel):\n"
        "    name: str\n"
        "    age: int | None = None\n\n\n"
        "class Model(BaseModel):\n"
        "    pet: Pet | None = None\n"
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
        "from pydantic import BaseModel\n\n\n"
        "class Pet(BaseModel):\n"
        "    name: str | None = None\n\n\n"
        "class Model(BaseModel):\n"
        "    pet: Pet | None = None\n"
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


@pytest.mark.parametrize(
    ("output_model", "expected_file"),
    [
        ("typing.TypedDict", "reserved_field_name_schema_typed_dict.py"),
        ("dataclasses.dataclass", "reserved_field_name_schema_dataclass.py"),
        ("pydantic_v2.BaseModel", "reserved_field_name_schema_pydantic.py"),
    ],
)
@pytest.mark.cli_doc(
    options=["--output-model-type"],
    input_schema="jsonschema/reserved_field_name_schema.json",
    cli_args=["--target-python-version", "3.11"],
    model_outputs={
        "typeddict": "main/jsonschema/reserved_field_name_schema_typed_dict.py",
        "dataclass": "main/jsonschema/reserved_field_name_schema_dataclass.py",
        "pydantic_v2": "main/jsonschema/reserved_field_name_schema_pydantic.py",
    },
)
@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_jsonschema_reserved_field_name(output_model: str, expected_file: str, output_file: Path) -> None:
    """Test reserved field name handling across model types (Issue #1833).

    This demonstrates how 'schema' field is handled:
    - TypedDict: not renamed (schema is not reserved)
    - dataclass: not renamed (schema is not reserved)
    - Pydantic: renamed to 'schema_' with alias (BaseModel.schema conflicts)
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "reserved_field_name_schema.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_file,
        extra_args=[
            "--output-model-type",
            output_model,
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
        timeout=30.0,
    )


@pytest.mark.parametrize(
    ("output_model", "expected_file"),
    [
        ("pydantic.BaseModel", "use_frozen_field_v1.py"),
        ("pydantic_v2.BaseModel", "use_frozen_field_v2.py"),
        ("dataclasses.dataclass", "use_frozen_field_dataclass.py"),
    ],
)
@pytest.mark.cli_doc(
    options=["--use-frozen-field"],
    input_schema="jsonschema/use_frozen_field.json",
    cli_args=["--use-frozen-field"],
    model_outputs={
        "pydantic_v1": "main/jsonschema/use_frozen_field_v1.py",
        "pydantic_v2": "main/jsonschema/use_frozen_field_v2.py",
        "dataclass": "main/jsonschema/use_frozen_field_dataclass.py",
    },
)
@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_use_frozen_field(output_model: str, expected_file: str, output_file: Path) -> None:
    """Generate frozen (immutable) field definitions for readOnly properties.

    The `--use-frozen-field` flag generates frozen field definitions:
    - Pydantic v1: `Field(allow_mutation=False)`
    - Pydantic v2: `Field(frozen=True)`
    - Dataclasses: silently ignored (no frozen fields generated)
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_frozen_field.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_file,
        extra_args=["--output-model-type", output_model, "--use-frozen-field"],
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
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--use-frozen-field"],
    )


@pytest.mark.parametrize(
    ("target_python_version", "expected_file"),
    [
        pytest.param("3.13", "use_frozen_field_typed_dict.py", marks=BLACK_PY313_SKIP),
        ("3.11", "use_frozen_field_typed_dict_py311.py"),
        ("3.10", "use_frozen_field_typed_dict_py310.py"),
    ],
)
@pytest.mark.cli_doc(
    options=["--use-frozen-field"],
    input_schema="jsonschema/use_frozen_field.json",
    cli_args=["--output-model-type", "typing.TypedDict", "--use-frozen-field"],
    model_outputs={
        "typeddict": "main/jsonschema/use_frozen_field_typed_dict.py",
    },
)
@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_use_frozen_field_typed_dict(target_python_version: str, expected_file: str, output_file: Path) -> None:
    """Generate ReadOnly type hints for readOnly properties in TypedDict.

    The `--use-frozen-field` flag generates ReadOnly type hints for TypedDict:
    - Python 3.13+: uses `typing.ReadOnly`
    - Python 3.11-3.12: uses `typing_extensions.ReadOnly`
    - Python 3.10: uses `typing_extensions.ReadOnly` and `typing_extensions.NotRequired`
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_frozen_field.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_file,
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--use-frozen-field",
            "--target-python-version",
            target_python_version,
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_file"),
    [
        ("dataclasses.dataclass", "default_factory_nested_model_dataclass.py"),
        ("pydantic_v2.BaseModel", "default_factory_nested_model_pydantic_v2.py"),
        ("msgspec.Struct", "default_factory_nested_model_msgspec.py"),
    ],
)
@pytest.mark.cli_doc(
    options=["--use-default-factory-for-optional-nested-models"],
    input_schema="jsonschema/default_factory_nested_model.json",
    cli_args=["--use-default-factory-for-optional-nested-models"],
    model_outputs={
        "dataclass": "main/jsonschema/default_factory_nested_model_dataclass.py",
        "pydantic_v2": "main/jsonschema/default_factory_nested_model_pydantic_v2.py",
        "msgspec": "main/jsonschema/default_factory_nested_model_msgspec.py",
    },
)
@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_use_default_factory_for_optional_nested_models(
    output_model: str, expected_file: str, output_file: Path
) -> None:
    """Generate default_factory for optional nested model fields.

    The `--use-default-factory-for-optional-nested-models` flag generates default_factory
    for optional nested model fields instead of None default:
    - Dataclasses: `field: Model | None = field(default_factory=Model)`
    - Pydantic: `field: Model | None = Field(default_factory=Model)`
    - msgspec: `field: Model | UnsetType = field(default_factory=Model)`
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "default_factory_nested_model.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_file,
        extra_args=[
            "--output-model-type",
            output_model,
            "--use-default-factory-for-optional-nested-models",
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_file"),
    [
        ("dataclasses.dataclass", "default_factory_nested_model_with_dict_dataclass.py"),
        ("pydantic_v2.BaseModel", "default_factory_nested_model_with_dict_pydantic_v2.py"),
        ("msgspec.Struct", "default_factory_nested_model_with_dict_msgspec.py"),
    ],
)
@pytest.mark.benchmark
@LEGACY_BLACK_SKIP
def test_main_use_default_factory_for_optional_nested_models_with_dict(
    output_model: str, expected_file: str, output_file: Path
) -> None:
    """Test --use-default-factory-for-optional-nested-models with dict union skips dict types."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "default_factory_nested_model_with_dict.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_file,
        extra_args=[
            "--output-model-type",
            output_model,
            "--use-default-factory-for-optional-nested-models",
        ],
    )


@pytest.mark.benchmark
def test_main_field_name_shadows_class_name(output_file: Path) -> None:
    """Test field name shadowing class name is renamed with alias for Pydantic v2."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "field_name_shadows_class_name.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.cli_doc(
    options=["--allof-merge-mode"],
    input_schema="jsonschema/allof_root_model_constraints.json",
    cli_args=["--allof-merge-mode", "constraints"],
    golden_output="main/jsonschema/allof_root_model_constraints_merge.py",
    comparison_output="main/jsonschema/allof_root_model_constraints.py",
)
@pytest.mark.benchmark
def test_main_allof_root_model_constraints_merge(output_file: Path) -> None:
    """Merge constraints from root model references in allOf schemas.

    The `--allof-merge-mode constraints` merges only constraint properties
    (minLength, maximum, etc.) from parent schemas referenced in allOf.
    This ensures child schemas inherit validation constraints while keeping
    other properties separate.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "allof_root_model_constraints.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="allof_root_model_constraints_merge.py",
        extra_args=["--allof-merge-mode", "constraints"],
    )


@pytest.mark.benchmark
def test_main_allof_root_model_constraints_none(output_file: Path) -> None:
    """Test allOf with root model reference without merging (issue #1901)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "allof_root_model_constraints.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="allof_root_model_constraints.py",
        extra_args=["--allof-merge-mode", "none"],
    )


@pytest.mark.benchmark
def test_main_allof_root_model_constraints_merge_pydantic_v2(output_file: Path) -> None:
    """Test allOf with root model constraints in Pydantic v2 (issue #2232).

    When merging pattern constraints that use lookaround assertions,
    the generated RootModel should use the base type in the generic
    (e.g., RootModel[str]) rather than the constrained type
    (e.g., RootModel[constr(pattern=...)]) to avoid regex evaluation
    before model_config with regex_engine='python-re' is processed.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "allof_root_model_constraints.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="allof_root_model_constraints_merge_pydantic_v2.py",
        extra_args=[
            "--allof-merge-mode",
            "constraints",
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
def test_main_nested_lookaround_array_pydantic_v2(output_file: Path) -> None:
    """Test nested lookaround pattern detection in array items (issue #2232).

    When array items have patterns with lookaround assertions, the lookaround
    should be detected in nested types and regex_engine='python-re' should be
    added. The RootModel generic should use the base type (list[str]) rather
    than the constrained type (list[constr(pattern=...)]).
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_lookaround_array.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="nested_lookaround_array_pydantic_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
def test_main_lookaround_anyof_nullable_pydantic_v2(output_file: Path) -> None:
    """Test lookaround pattern with anyOf null for union/optional path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "lookaround_anyof_nullable.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="lookaround_anyof_nullable_pydantic_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@LEGACY_BLACK_SKIP
@pytest.mark.benchmark
def test_main_lookaround_mixed_constraints_pydantic_v2(output_file: Path) -> None:
    """Test lookaround pattern with union of constr and conint to test base_type_hint fallback for non-constr types."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "lookaround_mixed_constraints.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="lookaround_mixed_constraints_pydantic_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
def test_main_lookaround_dict_pydantic_v2(output_file: Path) -> None:
    """Test lookaround pattern in dict values for base_type_hint dict path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "lookaround_dict.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="lookaround_dict_pydantic_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
def test_main_lookaround_union_types_pydantic_v2(output_file: Path) -> None:
    """Test lookaround pattern in union for base_type_hint union path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "lookaround_union_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="lookaround_union_types_pydantic_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
def test_main_nested_lookaround_array_generic_container(output_file: Path) -> None:
    """Test lookaround pattern with --use-generic-container-types for Sequence path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_lookaround_array.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="nested_lookaround_array_generic_container.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-container-types",
        ],
    )


@pytest.mark.benchmark
def test_main_lookaround_dict_generic_container(output_file: Path) -> None:
    """Test lookaround dict pattern with --use-generic-container-types for Mapping path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "lookaround_dict.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="lookaround_dict_generic_container.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-generic-container-types",
        ],
    )


@pytest.mark.benchmark
def test_main_nested_lookaround_array_standard_collections(output_file: Path) -> None:
    """Test lookaround pattern with --use-standard-collections for list path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_lookaround_array.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="nested_lookaround_array_standard_collections.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-standard-collections",
        ],
    )


@pytest.mark.benchmark
def test_main_lookaround_dict_standard_collections(output_file: Path) -> None:
    """Test lookaround dict pattern with --use-standard-collections for dict path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "lookaround_dict.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="lookaround_dict_standard_collections.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-standard-collections",
        ],
    )


@pytest.mark.benchmark
def test_main_lookaround_dict_key_pydantic_v2(output_file: Path) -> None:
    """Test lookaround pattern on dict key for dict_key.all_data_types path."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "lookaround_dict_key.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="lookaround_dict_key_pydantic_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
def test_main_nullable_array_items_strict_nullable(output_file: Path) -> None:
    """Test nullable array items with strict-nullable flag (issue #1815)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nullable_array_items.yaml",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="nullable_array_items_strict_nullable.py",
        extra_args=[
            "--strict-nullable",
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
def test_main_builtin_field_names(output_file: Path) -> None:
    """Test that builtin type names as field names don't break code generation (issue #2431).

    When a field has a name that matches a Python builtin (int, float, bool, str),
    the generated code should still use the builtin type directly without aliasing,
    since builtin types don't require imports.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "builtin_field_names.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="builtin_field_names.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.benchmark
def test_main_root_model_config_populate_by_name(output_file: Path) -> None:
    """Test that RootModel subclasses don't get populate_by_name config (issue #2483).

    The populate_by_name config is meaningless for RootModel because it only has
    a single 'root' field. Only BaseModel subclasses should have this config.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_config.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_model_config_populate_by_name.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--allow-population-by-field-name",
        ],
    )


@pytest.mark.benchmark
def test_main_root_model_config_frozen(output_file: Path) -> None:
    """Test that RootModel subclasses DO get frozen config (issue #2483).

    Unlike populate_by_name, the frozen config is meaningful for RootModel
    because it prevents mutation of the root value. Both BaseModel and RootModel
    subclasses should have this config when --enable-faux-immutability is used.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_config.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_model_config_frozen.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--enable-faux-immutability",
        ],
    )


@pytest.mark.cli_doc(
    options=["--naming-strategy"],
    input_schema="jsonschema/naming_strategy/input.json",
    cli_args=["--naming-strategy", "parent-prefixed"],
    golden_output="main/jsonschema/naming_strategy/parent_prefixed/output.py",
    related_options=["--duplicate-name-suffix", "--parent-scoped-naming"],
)
@freeze_time("2019-07-26")
def test_main_naming_strategy_parent_prefixed(output_file: Path) -> None:
    """Use parent-prefixed naming strategy for duplicate model names.

    The `--naming-strategy parent-prefixed` flag prefixes model names with their
    parent model name when duplicates occur. For example, if both `Order` and
    `Cart` have an inline `Item` definition, they become `OrderItem` and `CartItem`.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "input.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/parent_prefixed/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--naming-strategy",
            "parent-prefixed",
        ],
    )


@freeze_time("2019-07-26")
def test_main_naming_strategy_full_path(output_file: Path) -> None:
    """Use full-path naming strategy for duplicate model names.

    The `--naming-strategy full-path` flag uses the full schema path
    to generate unique names by concatenating ancestor names.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "input.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/full_path/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--naming-strategy",
            "full-path",
        ],
    )


@pytest.mark.cli_doc(
    options=["--duplicate-name-suffix"],
    input_schema="jsonschema/naming_strategy/input.json",
    cli_args=["--duplicate-name-suffix", '{"model": "Schema"}'],
    golden_output="main/jsonschema/naming_strategy/duplicate_name_suffix/output.py",
    related_options=["--naming-strategy"],
)
@freeze_time("2019-07-26")
def test_main_duplicate_name_suffix(output_file: Path) -> None:
    """Customize suffix for duplicate model names.

    The `--duplicate-name-suffix` flag allows specifying custom suffixes for
    resolving duplicate names by type. The value is a JSON mapping where keys
    are type names ('model', 'enum', 'default') and values are suffix strings.
    For example, `{"model": "Schema"}` changes `Item1` to `ItemSchema`.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "input.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/duplicate_name_suffix/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--duplicate-name-suffix",
            '{"model": "Schema"}',
        ],
    )


@freeze_time("2019-07-26")
def test_main_naming_strategy_complex_numbered(output_file: Path) -> None:
    """Test numbered strategy with complex nested schema and multiple duplicates.

    Tests deeply nested structures (Company > employees > employee > address)
    and multiple models with same name (4 different Address definitions).
    Expected: Address, Address1, Address2, Address3.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "complex_input.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/complex_numbered/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@freeze_time("2019-07-26")
def test_main_naming_strategy_complex_parent_prefixed(output_file: Path) -> None:
    """Test parent-prefixed strategy with complex nested schema.

    Tests deeply nested structures where each Address gets a unique name
    based on its parent hierarchy.
    Expected: ModelCompanyAddress, ModelCompanyEmployeeAddress,
    ModelCustomerAddress, ModelWarehouseAddress.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "complex_input.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/complex_parent_prefixed/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--naming-strategy",
            "parent-prefixed",
        ],
    )


@freeze_time("2019-07-26")
def test_main_naming_strategy_complex_duplicate_suffix(output_file: Path) -> None:
    """Test duplicate-name-suffix with complex schema having multiple duplicates.

    Tests that custom suffix is applied consistently across multiple duplicates.
    Expected: Address, AddressSchema, AddressSchema1, AddressSchema2.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "complex_input.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/complex_duplicate_suffix/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--duplicate-name-suffix",
            '{"model": "Schema"}',
        ],
    )


@freeze_time("2019-07-26")
@pytest.mark.cli_doc(
    options=["--naming-strategy"],
    input_schema="jsonschema/naming_strategy/primary_first_input.json",
    cli_args=["--naming-strategy", "primary-first"],
    golden_output="jsonschema/naming_strategy/complex_primary_first/output.py",
)
def test_main_naming_strategy_primary_first(output_file: Path) -> None:
    """Test primary-first strategy keeps clean names for primary definitions.

    Primary definitions (directly under #/definitions/, #/components/schemas/, #/$defs/)
    keep their clean names. Inline/nested definitions get numeric suffixes.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "primary_first_input.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/complex_primary_first/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--naming-strategy",
            "primary-first",
        ],
    )


@freeze_time("2019-07-26")
def test_main_naming_strategy_primary_first_multi_file(output_file: Path) -> None:
    """Test primary-first strategy with multiple files having same-named definitions.

    When multiple JSON schema files have definitions with the same name,
    the primary input file's definition should keep the clean name,
    while external references get numeric suffixes.

    This fixes GitHub issue #1300.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "primary_first_multi_file" / "main.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/primary_first_multi_file/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--naming-strategy",
            "primary-first",
        ],
    )


def test_main_duplicate_name_suffix_invalid_json(output_file: Path) -> None:
    """Test that invalid JSON in --duplicate-name-suffix raises an error."""
    run_main_with_args(
        [
            "--input",
            str(JSON_SCHEMA_DATA_PATH / "naming_strategy" / "input.json"),
            "--output",
            str(output_file),
            "--duplicate-name-suffix",
            "invalid json",
        ],
        expected_exit=Exit.ERROR,
    )


@freeze_time("2019-07-26")
def test_main_parent_scoped_naming_backward_compat(output_file: Path) -> None:
    """Test --parent-scoped-naming backward compatibility (deprecated flag)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "input.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="naming_strategy/parent_prefixed/output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--parent-scoped-naming",
        ],
    )


@pytest.mark.cli_doc(
    options=["--use-root-model-type-alias"],
    input_schema="jsonschema/root_model_type_alias.json",
    cli_args=["--use-root-model-type-alias", "--output-model-type", "pydantic_v2.BaseModel"],
    golden_output="jsonschema/root_model_type_alias.py",
)
def test_main_use_root_model_type_alias(output_file: Path) -> None:
    """Generate RootModel as type alias format for better mypy support (issue #1903)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "root_model_type_alias.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="root_model_type_alias.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-root-model-type-alias",
            "--target-python-version",
            "3.10",
        ],
    )


def test_main_jsonschema_schema_id(
    capsys: pytest.CaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that $id is exposed as schema_id in custom templates (issue #2098)."""
    model_base._get_environment.cache_clear()
    model_base._get_template_with_custom_dir.cache_clear()
    monkeypatch.chdir(tmp_path)
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / "schema_id.json",
            output_path=None,
            expected_stdout_path=EXPECTED_JSON_SCHEMA_PATH / "schema_id.py",
            capsys=capsys,
            input_file_type=None,
            extra_args=[
                "--custom-template-dir",
                str(DATA_PATH / "templates_schema_id"),
                "--output-model-type",
                "pydantic_v2.BaseModel",
            ],
        )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "model_extras_v2.py",
        ),
    ],
)
@pytest.mark.cli_doc(
    options=["--model-extra-keys"],
    input_schema="jsonschema/model_extras.json",
    cli_args=["--model-extra-keys", "x-custom-metadata"],
    model_outputs={
        "pydantic_v2": "main/jsonschema/model_extras_v2.py",
    },
)
def test_main_jsonschema_model_extras(output_model: str, expected_output: str, output_file: Path) -> None:
    """Add model-level schema extensions to ConfigDict json_schema_extra.

    The `--model-extra-keys` flag adds specified x-* extensions from the schema
    to the model's ConfigDict json_schema_extra.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "model_extras.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--output-model-type",
            output_model,
            "--model-extra-keys",
            "x-custom-metadata",
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "model_extras_without_x_prefix_v2.py",
        ),
    ],
)
@pytest.mark.cli_doc(
    options=["--model-extra-keys-without-x-prefix"],
    input_schema="jsonschema/model_extras.json",
    cli_args=["--model-extra-keys-without-x-prefix", "x-custom-metadata", "x-version"],
    model_outputs={
        "pydantic_v2": "main/jsonschema/model_extras_without_x_prefix_v2.py",
    },
)
def test_main_jsonschema_model_extras_without_x_prefix(
    output_model: str, expected_output: str, output_file: Path
) -> None:
    """Strip x- prefix from model-level schema extensions and add to ConfigDict json_schema_extra.

    The `--model-extra-keys-without-x-prefix` flag adds specified x-* extensions
    from the schema to the model's ConfigDict json_schema_extra with the x- prefix stripped.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "model_extras.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--output-model-type",
            output_model,
            "--model-extra-keys-without-x-prefix",
            "x-custom-metadata",
            "x-version",
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic_v2.BaseModel",
            "model_extras_no_match_v2.py",
        ),
    ],
)
def test_main_jsonschema_model_extras_no_match(output_model: str, expected_output: str, output_file: Path) -> None:
    """No json_schema_extra when specified model-extra-keys don't match schema extensions.

    When the specified key doesn't exist in the schema's x-* extensions,
    no json_schema_extra is added to ConfigDict.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "model_extras.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--output-model-type",
            output_model,
            "--model-extra-keys",
            "x-nonexistent",
        ],
    )


def test_main_jsonschema_non_dict_files_in_directory(output_dir: Path) -> None:
    """Test that non-dict files (lists, empty files) are skipped with warnings."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "non_dict_files",
        output_path=output_dir,
        expected_directory=EXPECTED_JSON_SCHEMA_PATH / "non_dict_files",
        input_file_type="jsonschema",
    )


def test_main_jsonschema_ref_to_json_list_file() -> None:
    """Test that $ref to a JSON file containing a list raises TypeError."""
    with pytest.raises(TypeError, match="Expected dict, got list"):
        generate(
            input_=JSON_SCHEMA_DATA_PATH / "ref_to_json_list" / "main.json",
            input_file_type=InputFileType.JsonSchema,
        )
