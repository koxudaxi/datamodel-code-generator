"""Regression coverage for external JSON Schema anchors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_output
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, run_main_and_assert
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH, assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_main_jsonschema_external_anchor_with_legacy_shorthand(output_file: Path) -> None:
    """Resolve external anchors without regressing legacy shorthand JSON pointers."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_anchor" / "root.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="external_anchor.py",
        extra_args=["--disable-timestamp", "--target-python-version", "3.10"],
        force_exec_validation=True,
    )


def test_main_jsonschema_malformed_external_ref_is_wrapped(
    capsys: pytest.CaptureFixture[str], output_file: Path
) -> None:
    """Report malformed external references as generator errors."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_ref_errors" / "malformed.json",
        output_path=output_file,
        input_file_type="jsonschema",
        expected_exit=Exit.ERROR,
    )
    assert_output(capsys.readouterr().err, EXPECTED_JSON_SCHEMA_PATH / "malformed_external_ref.txt")
