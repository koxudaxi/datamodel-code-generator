"""Regression coverage for external JSON Schema references."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_output
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, run_main_and_assert
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH, assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_main_jsonschema_nested_external_definitions_collapse_root_models(output_file: Path) -> None:
    """Resolve nested external definitions once while collapsing their root models."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "nested_external_defs" / "root.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="nested_external_defs.py",
        extra_args=["--disable-timestamp", "--target-python-version", "3.10", "--collapse-root-models"],
        force_exec_validation=True,
    )


def test_main_jsonschema_directory_external_ref_is_wrapped(
    capsys: pytest.CaptureFixture[str],
    output_file: Path,
) -> None:
    """Report a directory external reference as a generator error."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_ref_errors" / "directory.json",
        output_path=output_file,
        input_file_type="jsonschema",
        expected_exit=Exit.ERROR,
    )
    assert_output(capsys.readouterr().err, EXPECTED_JSON_SCHEMA_PATH / "directory_external_ref.txt")
