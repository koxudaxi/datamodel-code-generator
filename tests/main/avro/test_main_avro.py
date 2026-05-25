"""Tests for Avro schema code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import Error, InputFileType, generate, infer_input_type
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.format import PythonVersion, is_supported_in_black
from tests.main.avro.conftest import assert_avro_snippets
from tests.main.conftest import AVRO_DATA_PATH, CURRENT_PYTHON_VERSION, get_current_version_args, run_main_and_assert

if TYPE_CHECKING:
    from pathlib import Path

_CURRENT_PY_VERSION = PythonVersion(CURRENT_PYTHON_VERSION)
_SKIP_BLACK = pytest.mark.skipif(
    not is_supported_in_black(_CURRENT_PY_VERSION),
    reason=f"Installed black doesn't support Python {CURRENT_PYTHON_VERSION}",
)


@_SKIP_BLACK
def test_main_avro_constructs(output_file: Path) -> None:
    """Generate models for Avro primitive, complex, named, union, default, and logical types."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "constructs.avsc",
        output_path=output_file,
        input_file_type="avro",
        assert_func=assert_avro_snippets,
        expected_file="constructs.py",
        extra_args=get_current_version_args("--use-field-description"),
        force_exec_validation=True,
    )


@_SKIP_BLACK
def test_main_avro_infer_input_file_type(output_file: Path) -> None:
    """Infer Avro schema input and generate a model."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "constructs.avsc",
        output_path=output_file,
        assert_func=assert_avro_snippets,
        expected_file="constructs.py",
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
        assert_func=assert_avro_snippets,
        expected_file="namespace_collisions.py",
        extra_args=get_current_version_args(),
        force_exec_validation=True,
    )


@_SKIP_BLACK
def test_main_avro_official_spec_long_list(output_file: Path) -> None:
    """Generate the recursive LongList record from the Apache Avro 1.12.0 specification."""
    run_main_and_assert(
        input_path=AVRO_DATA_PATH / "official_long_list.avsc",
        output_path=output_file,
        input_file_type="avro",
        assert_func=assert_avro_snippets,
        expected_file="official_long_list.py",
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


def test_avro_dict_input_error() -> None:
    """Reject Mapping input for Avro so file/text parsing remains explicit."""
    with pytest.raises(Error, match="Dict input is not supported for avro"):
        generate({"type": "record", "name": "User", "fields": []}, input_file_type=InputFileType.Avro)


def test_infer_input_type_avro_union() -> None:
    """Infer top-level Avro union schemas."""
    assert infer_input_type('["null", "string"]') == InputFileType.Avro
