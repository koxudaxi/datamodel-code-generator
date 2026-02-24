"""Tests for --external-ref-mapping feature."""

from __future__ import annotations

from pathlib import Path

import pytest

from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator.__main__ import Exit, main
from datamodel_code_generator.config import GenerateConfig
from tests.main.conftest import OPEN_API_DATA_PATH, run_main_and_assert
from tests.main.openapi.conftest import assert_file_content

EXTERNAL_REF_DATA_PATH = OPEN_API_DATA_PATH / "external_ref_mapping"


def test_external_ref_mapping_basic(output_file: Path) -> None:
    """External refs produce imports, not class definitions."""
    run_main_and_assert(
        input_path=EXTERNAL_REF_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type="openapi",
        extra_args=[
            "--external-ref-mapping",
            "common.yaml=mypackage.shared.models",
        ],
        assert_func=assert_file_content,
        expected_file="external_ref_mapping.py",
    )


def test_external_ref_mapping_no_duplicate_classes(tmp_path: Path) -> None:
    """When mapping is active, the external file's classes should not be generated."""
    output_file = tmp_path / "output.py"
    generate(
        input_=EXTERNAL_REF_DATA_PATH / "api.yaml",
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        external_ref_mapping={"common.yaml": "mypackage.shared.models"},
    )
    content = output_file.read_text()
    # User and Error should NOT be defined as classes — only imported
    assert "class User(" not in content
    assert "class Error(" not in content
    assert "from mypackage.shared.models import" in content


def test_external_ref_mapping_without_flag_generates_classes(tmp_path: Path) -> None:
    """Without the flag, external refs generate classes (regression check)."""
    output_file = tmp_path / "output.py"
    generate(
        input_=EXTERNAL_REF_DATA_PATH / "api.yaml",
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
    )
    content = output_file.read_text()
    # Without mapping, classes should be generated inline
    assert "class User(" in content
    assert "class Error(" in content


def test_external_ref_mapping_invalid_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Invalid format (no equals sign) produces a clear error."""
    exit_code = main([
        "--input",
        str(EXTERNAL_REF_DATA_PATH / "api.yaml"),
        "--input-file-type",
        "openapi",
        "--external-ref-mapping",
        "no-equals-sign",
    ])
    assert exit_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "Invalid --external-ref-mapping format" in captured.err


def test_external_ref_mapping_programmatic_api(tmp_path: Path) -> None:
    """Test using GenerateConfig with external_ref_mapping."""
    output_file = tmp_path / "output.py"
    config = GenerateConfig(
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        external_ref_mapping={"common.yaml": "mypackage.shared.models"},
    )
    generate(
        input_=EXTERNAL_REF_DATA_PATH / "api.yaml",
        config=config,
    )
    content = output_file.read_text()
    assert "class User(" not in content
    assert "from mypackage.shared.models import" in content
