"""Tests for --external-ref-mapping feature."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator.__main__ import Exit, main
from datamodel_code_generator.config import GenerateConfig
from tests.main.conftest import OPEN_API_DATA_PATH, run_main_and_assert
from tests.main.openapi.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

EXTERNAL_REF_DATA_PATH = OPEN_API_DATA_PATH / "external_ref_mapping"


@pytest.mark.cli_doc(
    options=["--external-ref-mapping"],
    option_description="""Map external `$ref` files to Python packages.

Use `--external-ref-mapping FILE_PATH=PYTHON_PACKAGE` to import referenced models from an existing package,
instead of generating duplicate classes from external schema files.
""",
    input_schema="openapi/external_ref_mapping/api.yaml",
    cli_args=["--input-file-type", "openapi", "--external-ref-mapping", "common.yaml=mypackage.shared.models"],
    golden_output="main/openapi/external_ref_mapping.py",
)
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


def test_external_ref_mapping_nested_relative_ref(output_file: Path) -> None:
    """Mappings work for refs that are relative to nested external files."""
    run_main_and_assert(
        input_path=EXTERNAL_REF_DATA_PATH / "api_nested.yaml",
        output_path=output_file,
        input_file_type="openapi",
        extra_args=[
            "--external-ref-mapping",
            "common.yaml=mypackage.shared.models",
        ],
        assert_func=assert_file_content,
        expected_file="external_ref_mapping_nested.py",
    )


def test_external_ref_mapping_normalizes_imported_class_name(tmp_path: Path) -> None:
    """Mapped refs normalize schema keys to generated Python class names."""
    common_schema = tmp_path / "common.yaml"
    common_schema.write_text(
        """\
openapi: "3.0.3"
info:
  title: Common
  version: "1.0.0"
paths: {}
components:
  schemas:
    user-name:
      type: object
      properties:
        id:
          type: integer
      required:
        - id
"""
    )
    api_schema = tmp_path / "api.yaml"
    api_schema.write_text(
        """\
openapi: "3.0.3"
info:
  title: API
  version: "1.0.0"
paths: {}
components:
  schemas:
    UserResponse:
      type: object
      properties:
        user:
          $ref: "common.yaml#/components/schemas/user-name"
      required:
        - user
"""
    )
    output_file = tmp_path / "output.py"
    generate(
        input_=api_schema,
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        external_ref_mapping={"common.yaml": "mypackage.shared.models"},
    )
    content = output_file.read_text()
    assert "from mypackage.shared.models import UserName" in content
    assert "class UserName(" not in content


def test_external_ref_mapping_file_uri(tmp_path: Path) -> None:
    """Mappings accept file URI keys and refs."""
    common_schema = tmp_path / "common.yaml"
    common_schema.write_text(
        """\
openapi: "3.0.3"
info:
  title: Common
  version: "1.0.0"
paths: {}
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
      required:
        - id
"""
    )
    common_uri = common_schema.resolve().as_uri()
    api_schema = tmp_path / "api.yaml"
    api_schema.write_text(
        f"""\
openapi: "3.0.3"
info:
  title: API
  version: "1.0.0"
paths: {{}}
components:
  schemas:
    UserResponse:
      type: object
      properties:
        user:
          $ref: "{common_uri}#/components/schemas/User"
      required:
        - user
"""
    )
    output_file = tmp_path / "output.py"
    generate(
        input_=api_schema,
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        external_ref_mapping={common_uri: "mypackage.shared.models"},
    )
    content = output_file.read_text()
    assert "from mypackage.shared.models import User" in content
    assert "class User(" not in content


def test_external_ref_mapping_absolute_path_ref(tmp_path: Path) -> None:
    """Mappings match absolute-path refs to external schemas."""
    common_schema = tmp_path / "common.yaml"
    common_schema.write_text(
        """\
openapi: "3.0.3"
info:
  title: Common
  version: "1.0.0"
paths: {}
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
      required:
        - id
"""
    )
    absolute_ref = common_schema.resolve().as_posix()
    api_schema = tmp_path / "api.yaml"
    api_schema.write_text(
        f"""\
openapi: "3.0.3"
info:
  title: API
  version: "1.0.0"
paths: {{}}
components:
  schemas:
    UserResponse:
      type: object
      properties:
        user:
          $ref: "{absolute_ref}#/components/schemas/User"
      required:
        - user
"""
    )
    output_file = tmp_path / "output.py"
    generate(
        input_=api_schema,
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        external_ref_mapping={str(common_schema.resolve()): "mypackage.shared.models"},
    )
    content = output_file.read_text()
    assert "from mypackage.shared.models import User" in content
    assert "class User(" not in content


def test_external_ref_mapping_local_ref_unchanged(tmp_path: Path) -> None:
    """Local refs remain unchanged when external mapping is configured."""
    api_schema = tmp_path / "api.yaml"
    api_schema.write_text(
        """\
openapi: "3.0.3"
info:
  title: API
  version: "1.0.0"
paths: {}
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
      required:
        - id
    UserResponse:
      type: object
      properties:
        user:
          $ref: "#/components/schemas/User"
      required:
        - user
"""
    )
    output_file = tmp_path / "output.py"
    generate(
        input_=api_schema,
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        external_ref_mapping={"common.yaml": "mypackage.shared.models"},
    )
    content = output_file.read_text()
    assert "class User(" in content
    assert "class UserResponse(" in content
    assert "from mypackage.shared.models import" not in content


def test_external_ref_mapping_ref_without_fragment_errors(tmp_path: Path) -> None:
    """Refs without a fragment remain unsupported and fail clearly."""
    api_schema = tmp_path / "api.yaml"
    api_schema.write_text(
        """\
openapi: "3.0.3"
info:
  title: API
  version: "1.0.0"
paths: {}
components:
  schemas:
    UserResponse:
      type: object
      properties:
        user:
          $ref: "common.yaml"
      required:
        - user
"""
    )
    common_schema = tmp_path / "common.yaml"
    common_schema.write_text(
        """\
openapi: "3.0.3"
info:
  title: Common
  version: "1.0.0"
paths: {}
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
      required:
        - id
"""
    )
    output_file = tmp_path / "output.py"
    with pytest.raises(Exception, match="A Parser can not resolve classes"):
        generate(
            input_=api_schema,
            input_file_type=InputFileType.OpenAPI,
            output=output_file,
            external_ref_mapping={"common.yaml": "mypackage.shared.models"},
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
    with pytest.raises(SystemExit) as exc_info:
        main([
            "--input",
            str(EXTERNAL_REF_DATA_PATH / "api.yaml"),
            "--input-file-type",
            "openapi",
            "--external-ref-mapping",
            "no-equals-sign",
        ])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "Invalid --external-ref-mapping format" in captured.err


def test_external_ref_mapping_invalid_format_in_pyproject(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid pyproject external-ref-mapping format returns Exit.ERROR."""
    (tmp_path / "pyproject.toml").write_text(
        """\
[tool.datamodel-codegen]
external-ref-mapping = ["no-equals-sign"]
"""
    )
    monkeypatch.chdir(tmp_path)
    return_code = main([
        "--input",
        str(EXTERNAL_REF_DATA_PATH / "api.yaml"),
        "--output",
        str(tmp_path / "output.py"),
        "--input-file-type",
        "openapi",
    ])
    assert return_code == Exit.ERROR
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
