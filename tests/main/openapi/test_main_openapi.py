"""Tests for OpenAPI/Swagger input file code generation."""

from __future__ import annotations

import contextlib
import json
import platform
import re
import warnings
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, call

import black
import pydantic
import pytest
from packaging import version

from datamodel_code_generator import (
    MIN_VERSION,
    DataModelType,
    InputFileType,
    OpenAPIScope,
    PythonVersionMin,
    chdir,
    generate,
    get_version,
    inferred_message,
)
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.model import base as model_base
from tests.conftest import assert_directory_content, freeze_time
from tests.main.conftest import (
    BLACK_PY313_SKIP,
    BLACK_PY314_SKIP,
    DATA_PATH,
    LEGACY_BLACK_SKIP,
    MSGSPEC_LEGACY_BLACK_SKIP,
    OPEN_API_DATA_PATH,
    TIMESTAMP,
    run_main_and_assert,
    run_main_url_and_assert,
)
from tests.main.openapi.conftest import EXPECTED_OPENAPI_PATH, assert_file_content

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.benchmark
def test_main(output_file: Path) -> None:
    """Test OpenAPI file code generation."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="general.py",
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum(output_file: Path) -> None:
    """Test OpenAPI generation with discriminator enum."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="discriminator/enum.py",
        extra_args=["--target-python-version", "3.10", "--output-model-type", "pydantic_v2.BaseModel"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--use-enum-values-in-discriminator"],
    input_schema="openapi/discriminator_enum.yaml",
    cli_args=["--use-enum-values-in-discriminator", "--output-model-type", "pydantic_v2.BaseModel"],
    golden_output="openapi/discriminator/enum_use_enum_values.py",
)
def test_main_openapi_discriminator_enum_use_enum_values(output_file: Path) -> None:
    """Use enum values in discriminator mappings for union types.

    The `--use-enum-values-in-discriminator` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="discriminator/enum_use_enum_values.py",
        extra_args=[
            "--target-python-version",
            "3.10",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-enum-values-in-discriminator",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum_use_enum_values_sanitized(output_file: Path) -> None:
    """Enum values requiring sanitization are rendered as enum members in discriminator."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "discriminator_enum_sanitized.yaml",
            output_path=output_file,
            input_file_type="openapi",
            assert_func=assert_file_content,
            expected_file="discriminator/enum_use_enum_values_sanitized.py",
            extra_args=[
                "--target-python-version",
                "3.10",
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--use-enum-values-in-discriminator",
            ],
        )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum_duplicate(output_file: Path) -> None:
    """Test OpenAPI generation with duplicate discriminator enum."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum_duplicate.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "enum_duplicate.py",
        extra_args=["--target-python-version", "3.10", "--output-model-type", "pydantic_v2.BaseModel"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum_single_value(output_file: Path) -> None:
    """Single-value enum discriminator with allOf inheritance."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum_single_value.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "enum_single_value.py",
        extra_args=["--target-python-version", "3.10", "--output-model-type", "pydantic_v2.BaseModel"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum_single_value_use_enum(output_file: Path) -> None:
    """Single-value enum with allOf + --use-enum-values-in-discriminator."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum_single_value.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "enum_single_value_use_enum.py",
        extra_args=[
            "--target-python-version",
            "3.10",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-enum-values-in-discriminator",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum_single_value_anyof(output_file: Path) -> None:
    """Single-value enum discriminator with anyOf - uses enum value, not model name."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum_single_value_anyof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "enum_single_value_anyof.py",
        extra_args=["--target-python-version", "3.10", "--output-model-type", "pydantic_v2.BaseModel"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum_single_value_anyof_use_enum(output_file: Path) -> None:
    """Single-value enum with anyOf + --use-enum-values-in-discriminator."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum_single_value_anyof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "enum_single_value_anyof_use_enum.py",
        extra_args=[
            "--target-python-version",
            "3.10",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-enum-values-in-discriminator",
        ],
    )


def test_main_openapi_discriminator_with_properties(output_file: Path) -> None:
    """Test OpenAPI generation with discriminator properties."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_with_properties.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "with_properties.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_discriminator_allof(output_file: Path) -> None:
    """Test OpenAPI generation with allOf discriminator polymorphism."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_allof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "allof.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--snake-case-field",
            "--use-annotated",
            "--use-union-operator",
            "--collapse-root-models",
        ],
    )


def test_main_openapi_discriminator_allof_no_subtypes(output_file: Path) -> None:
    """Test OpenAPI generation with discriminator but no allOf subtypes.

    This tests the edge case where a schema has a discriminator but nothing
    inherits from it using allOf.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_allof_no_subtypes.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "allof_no_subtypes.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_openapi_discriminator_short_mapping_names(output_file: Path) -> None:
    """Test OpenAPI generation with discriminator using short mapping names.

    Per OpenAPI spec, mapping values can be short names like "FooItem" instead
    of full refs like "#/components/schemas/FooItem". This tests that short
    names are normalized correctly.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_short_mapping_names.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "short_mapping_names.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_openapi_discriminator_no_mapping(output_file: Path) -> None:
    """Test OpenAPI generation with discriminator without mapping.

    This tests the case where a discriminator has only propertyName but no mapping.
    The subtypes are discovered via allOf inheritance.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_no_mapping.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "no_mapping.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_openapi_discriminator_no_mapping_no_subtypes(output_file: Path) -> None:
    """Test OpenAPI generation with discriminator without mapping and no allOf subtypes.

    This tests the edge case where a discriminator has no mapping and no schemas
    inherit from it using allOf.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_no_mapping_no_subtypes.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "no_mapping_no_subtypes.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_openapi_allof_with_oneof_ref(output_file: Path) -> None:
    """Test OpenAPI generation with allOf referencing a oneOf schema.

    This tests the case where allOf combines a $ref to a schema with oneOf/discriminator
    and additional properties. Regression test for issue #1763.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_oneof_ref.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "allof_with_oneof_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_openapi_allof_with_anyof_ref(output_file: Path) -> None:
    """Test OpenAPI generation with allOf referencing an anyOf schema.

    This tests the case where allOf combines a $ref to a schema with anyOf
    and additional properties.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_anyof_ref.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "allof_with_anyof_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_pydantic_basemodel(output_file: Path) -> None:
    """Test OpenAPI generation with Pydantic BaseModel output."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="general.py",
        extra_args=["--output-model-type", "pydantic.BaseModel"],
    )


@pytest.mark.cli_doc(
    options=["--base-class"],
    input_schema="openapi/api.yaml",
    cli_args=["--base-class", "custom_module.Base"],
    golden_output="openapi/base_class.py",
)
def test_main_base_class(output_file: Path) -> None:
    """Specify a custom base class for generated models.

    The `--base-class` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="base_class.py",
        extra_args=["--base-class", "custom_module.Base"],
        copy_files=[(DATA_PATH / "pyproject.toml", output_file.parent / "pyproject.toml")],
    )


def test_target_python_version(output_file: Path) -> None:
    """Test OpenAPI generation with target Python version."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--target-python-version", f"3.{MIN_VERSION}"],
    )


@BLACK_PY313_SKIP
def test_target_python_version_313_has_future_annotations(output_file: Path) -> None:
    """Test that Python 3.13 target includes future annotations import."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=output_file,
            input_file_type=None,
            assert_func=assert_file_content,
            extra_args=["--target-python-version", "3.13"],
        )


@BLACK_PY314_SKIP
def test_target_python_version_314_no_future_annotations(output_file: Path) -> None:
    """Test that Python 3.14 target omits future annotations import (PEP 649)."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=output_file,
            input_file_type=None,
            assert_func=assert_file_content,
            extra_args=["--target-python-version", "3.14"],
        )


@pytest.mark.benchmark
def test_main_modular(output_dir: Path) -> None:
    """Test main function on modular file."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "modular.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "modular",
        )


def test_main_modular_reuse_model(output_dir: Path) -> None:
    """Test main function on modular file."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "modular.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "modular_reuse_model",
            extra_args=["--reuse-model"],
        )


def test_main_modular_no_file(tmp_path: Path) -> None:
    """Test main function on modular file with no output name."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=tmp_path / "output.py",
        input_file_type=None,
        expected_exit=Exit.ERROR,
    )


def test_main_modular_filename(output_file: Path) -> None:
    """Test main function on modular file with filename."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_file,
        input_file_type=None,
        expected_exit=Exit.ERROR,
    )


def test_main_openapi_no_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test main function on non-modular file with no output name."""
    monkeypatch.chdir(tmp_path)

    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=None,
            expected_stdout_path=EXPECTED_OPENAPI_PATH / "no_file.py",
            capsys=capsys,
            expected_stderr=inferred_message.format("openapi") + "\n",
        )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "extra_template_data_config.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "extra_template_data_config_pydantic_v2.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--extra-template-data"],
    input_schema="openapi/api.yaml",
    cli_args=["--extra-template-data", "openapi/extra_data.json"],
    model_outputs={
        "pydantic_v1": "openapi/extra_template_data_config.py",
        "pydantic_v2": "openapi/extra_template_data_config_pydantic_v2.py",
    },
)
def test_main_openapi_extra_template_data_config(
    capsys: pytest.CaptureFixture,
    output_model: str,
    expected_output: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass custom template variables from JSON file for code generation.

    The `--extra-template-data` flag allows you to provide additional variables
    (from a JSON file) that can be used in custom templates to configure generated
    model settings like Config classes, enabling customization beyond standard options.
    """
    monkeypatch.chdir(tmp_path)
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=None,
            expected_stdout_path=EXPECTED_OPENAPI_PATH / expected_output,
            capsys=capsys,
            input_file_type=None,
            extra_args=[
                "--extra-template-data",
                str(OPEN_API_DATA_PATH / "extra_data.json"),
                "--output-model-type",
                output_model,
            ],
            expected_stderr=inferred_message.format("openapi") + "\n",
        )


def test_main_custom_template_dir_old_style(
    capsys: pytest.CaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test main function with custom template directory."""
    monkeypatch.chdir(tmp_path)
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=None,
            expected_stdout_path=EXPECTED_OPENAPI_PATH / "custom_template_dir.py",
            capsys=capsys,
            input_file_type=None,
            extra_args=[
                "--custom-template-dir",
                str(DATA_PATH / "templates_old_style"),
                "--extra-template-data",
                str(OPEN_API_DATA_PATH / "extra_data.json"),
            ],
            expected_stderr=inferred_message.format("openapi") + "\n",
        )


@pytest.mark.cli_doc(
    options=["--custom-template-dir"],
    input_schema="openapi/api.yaml",
    cli_args=["--custom-template-dir", "templates", "--extra-template-data", "openapi/extra_data.json"],
    golden_output="openapi/custom_template_dir.py",
)
def test_main_openapi_custom_template_dir(
    capsys: pytest.CaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use custom Jinja2 templates for model generation.

    The `--custom-template-dir` option allows you to specify a directory containing custom Jinja2 templates
    to override the default templates used for generating data models. This enables full customization of
    the generated code structure and formatting. Use with `--extra-template-data` to pass additional data
    to the templates.
    """
    monkeypatch.chdir(tmp_path)
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=None,
            expected_stdout_path=EXPECTED_OPENAPI_PATH / "custom_template_dir.py",
            capsys=capsys,
            input_file_type=None,
            extra_args=[
                "--custom-template-dir",
                str(DATA_PATH / "templates"),
                "--extra-template-data",
                str(OPEN_API_DATA_PATH / "extra_data.json"),
            ],
            expected_stderr=inferred_message.format("openapi") + "\n",
        )


def test_main_openapi_schema_extensions(
    capsys: pytest.CaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that schema extensions (x-* fields) are passed to custom templates."""
    model_base._get_environment.cache_clear()
    model_base._get_template_with_custom_dir.cache_clear()
    monkeypatch.chdir(tmp_path)
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "schema_extensions.yaml",
            output_path=None,
            expected_stdout_path=EXPECTED_OPENAPI_PATH / "schema_extensions.py",
            capsys=capsys,
            input_file_type=None,
            extra_args=[
                "--custom-template-dir",
                str(DATA_PATH / "templates_extensions"),
                "--output-model-type",
                "pydantic_v2.BaseModel",
            ],
            expected_stderr=inferred_message.format("openapi") + "\n",
        )


@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
def test_pyproject(tmp_path: Path) -> None:
    """Test code generation using pyproject.toml configuration."""
    if platform.system() == "Windows":

        def get_path(path: str) -> str:
            return str(path).replace("\\", "\\\\")

    else:

        def get_path(path: str) -> str:
            return str(path)

    output_file: Path = tmp_path / "output.py"
    pyproject_toml_path = Path(DATA_PATH) / "project" / "pyproject.toml"
    pyproject_toml = (
        pyproject_toml_path.read_text()
        .replace("INPUT_PATH", get_path(OPEN_API_DATA_PATH / "api.yaml"))
        .replace("OUTPUT_PATH", get_path(output_file))
        .replace("ALIASES_PATH", get_path(OPEN_API_DATA_PATH / "empty_aliases.json"))
        .replace(
            "EXTRA_TEMPLATE_DATA_PATH",
            get_path(OPEN_API_DATA_PATH / "empty_data.json"),
        )
        .replace("CUSTOM_TEMPLATE_DIR_PATH", get_path(tmp_path))
    )
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=output_file,
            input_file_type=None,
            assert_func=assert_file_content,
        )


def test_pyproject_not_found(tmp_path: Path) -> None:
    """Test code generation when pyproject.toml is not found."""
    output_file: Path = tmp_path / "output.py"
    with chdir(tmp_path):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=output_file,
            input_file_type=None,
            assert_func=assert_file_content,
        )


def test_stdin(monkeypatch: pytest.MonkeyPatch, output_file: Path) -> None:
    """Test OpenAPI code generation from stdin input."""
    run_main_and_assert(
        stdin_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        monkeypatch=monkeypatch,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="general.py",
        transform=lambda s: s.replace("#   filename:  <stdin>", "#   filename:  api.yaml"),
    )


@pytest.mark.cli_doc(
    options=["--validation"],
    input_schema="openapi/api.yaml",
    cli_args=["--validation"],
    golden_output="openapi/general.py",
)
def test_validation(mocker: MockerFixture, output_file: Path) -> None:
    """Enable validation constraints (deprecated, use --field-constraints).

    The `--validation` flag configures the code generation behavior.
    """
    mock_prance = mocker.patch("prance.BaseParser")
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="general.py",
        extra_args=["--validation"],
    )
    mock_prance.assert_called_once()


def test_validation_failed(mocker: MockerFixture, output_file: Path) -> None:
    """Test OpenAPI code generation with validation failure."""
    mock_prance = mocker.patch("prance.BaseParser", side_effect=Exception("error"))
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "invalid.yaml",
        output_path=output_file,
        input_file_type="openapi",
        expected_exit=Exit.ERROR,
        extra_args=["--validation"],
    )
    mock_prance.assert_called_once()


@pytest.mark.parametrize(
    ("output_model", "expected_output", "args"),
    [
        ("pydantic.BaseModel", "with_field_constraints.py", []),
        (
            "pydantic.BaseModel",
            "with_field_constraints_use_unique_items_as_set.py",
            ["--use-unique-items-as-set"],
        ),
        ("pydantic_v2.BaseModel", "with_field_constraints_pydantic_v2.py", []),
        (
            "pydantic_v2.BaseModel",
            "with_field_constraints_pydantic_v2_use_generic_container_types.py",
            ["--use-generic-container-types"],
        ),
        (
            "pydantic_v2.BaseModel",
            "with_field_constraints_pydantic_v2_use_generic_container_types_set.py",
            ["--use-generic-container-types", "--use-unique-items-as-set"],
        ),
        (
            "pydantic_v2.BaseModel",
            "with_field_constraints_pydantic_v2_use_standard_collections.py",
            [
                "--use-standard-collections",
            ],
        ),
        (
            "pydantic_v2.BaseModel",
            "with_field_constraints_pydantic_v2_use_standard_collections_set.py",
            ["--use-standard-collections", "--use-unique-items-as-set"],
        ),
    ],
)
@pytest.mark.cli_doc(
    options=["--use-unique-items-as-set"],
    input_schema="openapi/api_constrained.yaml",
    cli_args=["--use-unique-items-as-set", "--field-constraints"],
    golden_output="openapi/with_field_constraints_use_unique_items_as_set.py",
)
def test_main_with_field_constraints(
    output_model: str, expected_output: str, args: list[str], output_file: Path
) -> None:
    """Generate set types for arrays with uniqueItems constraint.

    The `--use-unique-items-as-set` flag generates Python set types instead of
    list types for JSON Schema arrays that have the uniqueItems constraint set
    to true, enforcing uniqueness at the type level.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_constrained.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--field-constraints", "--output-model-type", output_model, *args],
    )


@pytest.mark.cli_doc(
    options=["--field-constraints"],
    input_schema="openapi/api_constrained.yaml",
    cli_args=["--field-constraints"],
    model_outputs={
        "pydantic_v1": "main/openapi/with_field_constraints.py",
        "pydantic_v2": "main/openapi/with_field_constraints_pydantic_v2.py",
    },
    primary=True,
)
def test_main_field_constraints_model_outputs(output_file: Path) -> None:
    """Generate Field() with validation constraints from schema.

    The `--field-constraints` flag generates Pydantic Field() definitions with
    validation constraints (min/max length, pattern, etc.) from the schema.
    Output differs between Pydantic v1 and v2 due to API changes.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_constrained.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="with_field_constraints.py",
        extra_args=["--field-constraints"],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "without_field_constraints.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "without_field_constraints_pydantic_v2.py",
        ),
    ],
)
def test_main_without_field_constraints(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test OpenAPI generation without field constraints."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_constrained.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "with_aliases.py",
        ),
        pytest.param(
            "msgspec.Struct",
            "with_aliases_msgspec.py",
            marks=LEGACY_BLACK_SKIP,
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--aliases"],
    input_schema="openapi/api.yaml",
    cli_args=["--aliases", "openapi/aliases.json", "--target-python-version", "3.10"],
    model_outputs={
        "pydantic_v1": "openapi/with_aliases.py",
        "msgspec": "openapi/with_aliases_msgspec.py",
    },
    primary=True,
)
def test_main_with_aliases(output_model: str, expected_output: str, output_file: Path) -> None:
    """Apply custom field and class name aliases from JSON file.

    The `--aliases` option allows renaming fields and classes via a JSON mapping file,
    providing fine-grained control over generated names independent of schema definitions.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--aliases",
            str(OPEN_API_DATA_PATH / "aliases.json"),
            "--target-python-version",
            "3.10",
            "--output-model-type",
            output_model,
        ],
    )


def test_main_with_bad_aliases(output_file: Path) -> None:
    """Test OpenAPI generation with invalid aliases file."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        expected_exit=Exit.ERROR,
        extra_args=["--aliases", str(OPEN_API_DATA_PATH / "not.json")],
    )


def test_main_with_more_bad_aliases(output_file: Path) -> None:
    """Test OpenAPI generation with malformed aliases file."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        expected_exit=Exit.ERROR,
        extra_args=["--aliases", str(OPEN_API_DATA_PATH / "list.json")],
    )


def test_main_with_bad_extra_data(output_file: Path) -> None:
    """Test OpenAPI generation with invalid extra template data file."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        expected_exit=Exit.ERROR,
        extra_args=["--extra-template-data", str(OPEN_API_DATA_PATH / "not.json")],
    )


@pytest.mark.benchmark
def test_main_with_snake_case_field(output_file: Path) -> None:
    """Test OpenAPI generation with snake case field naming."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--snake-case-field"],
    )


@pytest.mark.benchmark
@pytest.mark.cli_doc(
    options=["--strip-default-none"],
    input_schema="openapi/api.yaml",
    cli_args=["--strip-default-none"],
    golden_output="openapi/with_strip_default_none.py",
)
def test_main_with_strip_default_none(output_file: Path) -> None:
    """Remove fields with None as default value from generated models.

    The `--strip-default-none` option removes fields that have None as their default value from the
    generated models. This results in cleaner model definitions by excluding optional fields that
    default to None.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--strip-default-none"],
    )


def test_disable_timestamp(output_file: Path) -> None:
    """Test OpenAPI generation with timestamp disabled."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--disable-timestamp"],
    )


@pytest.mark.cli_doc(
    options=["--enable-version-header"],
    input_schema="openapi/api.yaml",
    cli_args=["--enable-version-header"],
    golden_output="openapi/enable_version_header.py",
)
def test_enable_version_header(output_file: Path) -> None:
    """Include tool version information in file header.

    The `--enable-version-header` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="enable_version_header.py",
        extra_args=["--enable-version-header"],
        transform=lambda s: s.replace(f"#   version:   {get_version()}", "#   version:   0.0.0"),
    )


@pytest.mark.cli_doc(
    options=["--enable-command-header"],
    input_schema="openapi/api.yaml",
    cli_args=["--enable-command-header"],
    golden_output="openapi/enable_command_header.py",
)
def test_enable_command_header(output_file: Path) -> None:
    """Include command-line options in file header for reproducibility.

    The `--enable-command-header` flag adds the full command-line used to generate
    the file to the header, making it easy to reproduce the generation.
    """

    def normalize_command(s: str) -> str:
        # Replace the actual command line with a placeholder for consistent testing
        return re.sub(r"#   command:   datamodel-codegen .*", "#   command:   datamodel-codegen [COMMAND]", s)

    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="enable_command_header.py",
        extra_args=["--enable-command-header"],
        transform=normalize_command,
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "allow_population_by_field_name.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "allow_population_by_field_name_pydantic_v2.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--allow-population-by-field-name"],
    input_schema="openapi/api.yaml",
    cli_args=["--allow-population-by-field-name"],
    model_outputs={
        "pydantic_v1": "openapi/allow_population_by_field_name.py",
        "pydantic_v2": "openapi/allow_population_by_field_name_pydantic_v2.py",
    },
)
def test_allow_population_by_field_name(output_model: str, expected_output: str, output_file: Path) -> None:
    """Allow Pydantic model population by field name (not just alias).

    The `--allow-population-by-field-name` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--allow-population-by-field-name", "--output-model-type", output_model],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "allow_extra_fields.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "allow_extra_fields_pydantic_v2.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--allow-extra-fields"],
    input_schema="openapi/api.yaml",
    cli_args=["--allow-extra-fields"],
    model_outputs={
        "pydantic_v1": "openapi/allow_extra_fields.py",
        "pydantic_v2": "openapi/allow_extra_fields_pydantic_v2.py",
    },
)
def test_allow_extra_fields(output_model: str, expected_output: str, output_file: Path) -> None:
    """Allow extra fields in generated Pydantic models (extra='allow').

    The `--allow-extra-fields` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--allow-extra-fields", "--output-model-type", output_model],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "enable_faux_immutability.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "enable_faux_immutability_pydantic_v2.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--enable-faux-immutability"],
    input_schema="openapi/api.yaml",
    cli_args=["--enable-faux-immutability"],
    model_outputs={
        "pydantic_v1": "openapi/enable_faux_immutability.py",
        "pydantic_v2": "openapi/enable_faux_immutability_pydantic_v2.py",
    },
)
def test_enable_faux_immutability(output_model: str, expected_output: str, output_file: Path) -> None:
    """Enable faux immutability in Pydantic v1 models (allow_mutation=False).

    The `--enable-faux-immutability` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--enable-faux-immutability", "--output-model-type", output_model],
    )


@pytest.mark.benchmark
def test_use_default(output_file: Path) -> None:
    """Test OpenAPI generation with use default option."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--use-default"],
    )


@pytest.mark.cli_doc(
    options=["--force-optional"],
    input_schema="openapi/api.yaml",
    cli_args=["--force-optional"],
    golden_output="openapi/force_optional.py",
)
@pytest.mark.benchmark
def test_force_optional(output_file: Path) -> None:
    """Force all fields to be Optional regardless of required status.

    The `--force-optional` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--force-optional"],
    )


def test_main_with_exclusive(output_file: Path) -> None:
    """Test OpenAPI generation with exclusive keywords."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "exclusive.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
    )


def test_main_subclass_enum(output_file: Path) -> None:
    """Test OpenAPI generation with subclass enum."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "subclass_enum.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support the old style",
)
def test_main_specialized_enum(output_file: Path) -> None:
    """Test OpenAPI generation with specialized enum."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "subclass_enum.json",
        output_path=output_file,
        input_file_type=None,
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
    input_schema="openapi/subclass_enum.json",
    cli_args=["--target-python-version", "3.11", "--no-use-specialized-enum"],
    golden_output="openapi/subclass_enum.py",
    related_options=["--use-specialized-enum", "--target-python-version"],
)
def test_main_specialized_enums_disabled(output_file: Path) -> None:
    """Disable specialized Enum classes for Python 3.11+ code generation.

    The `--no-use-specialized-enum` flag prevents the generator from using
    specialized Enum classes (StrEnum, IntEnum) when generating code for
    Python 3.11+, falling back to standard Enum classes instead.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "subclass_enum.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="subclass_enum.py",
        extra_args=["--target-python-version", "3.11", "--no-use-specialized-enum"],
    )


def test_main_use_standard_collections(output_dir: Path) -> None:
    """Test OpenAPI generation with standard collections."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "modular.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "use_standard_collections",
            extra_args=["--use-standard-collections"],
        )


@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
def test_main_use_generic_container_types(output_dir: Path) -> None:
    """Test OpenAPI generation with generic container types."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "modular.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "use_generic_container_types",
            extra_args=["--use-generic-container-types"],
        )


@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.benchmark
def test_main_use_generic_container_types_standard_collections(
    output_dir: Path,
) -> None:
    """Test OpenAPI generation with generic container types and standard collections."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "modular.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "use_generic_container_types_standard_collections",
            extra_args=["--use-generic-container-types", "--use-standard-collections"],
        )


def test_main_original_field_name_delimiter_without_snake_case_field(
    capsys: pytest.CaptureFixture, output_file: Path
) -> None:
    """Test OpenAPI generation with original field name delimiter error."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_file,
        input_file_type=None,
        expected_exit=Exit.ERROR,
        extra_args=["--original-field-name-delimiter", "-"],
        capsys=capsys,
        expected_stderr_contains="`--original-field-name-delimiter` can not be used without `--snake-case-field`.",
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output", "date_type"),
    [
        ("pydantic.BaseModel", "datetime.py", "AwareDatetime"),
        ("pydantic_v2.BaseModel", "datetime_pydantic_v2.py", "AwareDatetime"),
        ("pydantic_v2.BaseModel", "datetime_pydantic_v2_datetime.py", "datetime"),
        ("pydantic_v2.BaseModel", "datetime_pydantic_v2_past_datetime.py", "PastDatetime"),
        ("pydantic_v2.BaseModel", "datetime_pydantic_v2_future_datetime.py", "FutureDatetime"),
        ("dataclasses.dataclass", "datetime_dataclass.py", "datetime"),
        ("msgspec.Struct", "datetime_msgspec.py", "datetime"),
    ],
)
@pytest.mark.cli_doc(
    options=["--output-datetime-class"],
    input_schema="openapi/datetime.yaml",
    cli_args=["--output-datetime-class", "AwareDatetime"],
    golden_output="openapi/datetime_pydantic_v2.py",
)
def test_main_openapi_aware_datetime(
    output_model: str, expected_output: str, date_type: str, output_file: Path
) -> None:
    """Specify datetime class type for date-time schema fields.

    The `--output-datetime-class` flag controls which datetime type to use for fields
    with date-time format. Options include 'AwareDatetime' for timezone-aware datetimes
    or 'datetime' for standard Python datetime objects.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "datetime.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-datetime-class", date_type, "--output-model-type", output_model],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "datetime.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "datetime_pydantic_v2.py",
        ),
    ],
)
def test_main_openapi_datetime(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test OpenAPI generation with datetime types."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "datetime.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model],
    )


@pytest.mark.parametrize(
    ("date_class", "expected_output"),
    [
        ("PastDate", "date_class_past_date.py"),
        ("FutureDate", "date_class_future_date.py"),
    ],
)
@pytest.mark.cli_doc(
    options=["--output-date-class"],
    input_schema="openapi/date_class.yaml",
    cli_args=["--output-date-class", "PastDate"],
    golden_output="openapi/date_class_past_date.py",
)
@freeze_time(TIMESTAMP)
def test_main_openapi_date_class(date_class: str, expected_output: str, output_file: Path) -> None:
    """Specify date class type for date schema fields.

    The `--output-date-class` flag controls which date type to use for fields
    with date format. Options include 'PastDate' for past dates only
    or 'FutureDate' for future dates only. This is a Pydantic v2 only feature.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "date_class.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-date-class", date_class, "--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_models_not_found(capsys: pytest.CaptureFixture, output_file: Path) -> None:
    """Test OpenAPI generation with models not found error."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "no_components.yaml",
        output_path=output_file,
        input_file_type="openapi",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Models not found in the input data",
    )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse("1.9.0"),
    reason="Require Pydantic version 1.9.0 or later ",
)
@pytest.mark.cli_doc(
    options=["--enum-field-as-literal"],
    input_schema="openapi/enum_models.yaml",
    cli_args=["--enum-field-as-literal", "one"],
    golden_output="openapi/enum_models/one.py",
)
def test_main_openapi_enum_models_as_literal_one(min_version: str, output_file: Path) -> None:
    """Convert single-member enums to Literal types in OpenAPI schemas.

    The `--enum-field-as-literal one` flag converts enums with a single member
    to Literal type annotations while keeping multi-member enums as Enum classes.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "enum_models.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="enum_models/one.py",
        extra_args=["--enum-field-as-literal", "one", "--target-python-version", min_version],
    )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse("1.9.0"),
    reason="Require Pydantic version 1.9.0 or later ",
)
@pytest.mark.cli_doc(
    options=["--use-one-literal-as-default"],
    input_schema="openapi/enum_models.yaml",
    cli_args=["--use-one-literal-as-default", "--enum-field-as-literal", "one"],
    golden_output="openapi/enum_models/one_literal_as_default.py",
)
def test_main_openapi_use_one_literal_as_default(min_version: str, output_file: Path) -> None:
    """Use single literal value as default when enum has only one option.

    The `--use-one-literal-as-default` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "enum_models.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "enum_models" / "one_literal_as_default.py",
        extra_args=[
            "--enum-field-as-literal",
            "one",
            "--target-python-version",
            min_version,
            "--use-one-literal-as-default",
        ],
    )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse("1.9.0"),
    reason="Require Pydantic version 1.9.0 or later ",
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_enum_models_as_literal_all(min_version: str, output_file: Path) -> None:
    """Test OpenAPI generation with all enum models as literal."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "enum_models.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="enum_models/all.py",
        extra_args=["--enum-field-as-literal", "all", "--target-python-version", min_version],
    )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse("1.9.0"),
    reason="Require Pydantic version 1.9.0 or later ",
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_enum_models_as_literal(output_file: Path) -> None:
    """Test OpenAPI generation with enum models as literal."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "enum_models.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "enum_models" / "as_literal.py",
        extra_args=["--enum-field-as-literal", "all", "--target-python-version", f"3.{MIN_VERSION}"],
    )


@pytest.mark.benchmark
def test_main_openapi_all_of_required(output_file: Path) -> None:
    """Test OpenAPI generation with allOf required fields."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_required.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_required.py",
    )


@pytest.mark.benchmark
def test_main_openapi_nullable(output_file: Path) -> None:
    """Test OpenAPI generation with nullable types."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="nullable.py",
    )


@pytest.mark.cli_doc(
    options=["--strict-nullable"],
    input_schema="openapi/nullable.yaml",
    cli_args=["--strict-nullable"],
    golden_output="openapi/nullable_strict_nullable.py",
    related_options=["--use-default"],
)
def test_main_openapi_nullable_strict_nullable(output_file: Path) -> None:
    """Treat default field as a non-nullable field.

    The `--strict-nullable` flag ensures that fields with default values are generated
    with their exact schema type (non-nullable), rather than being made nullable.

    This is particularly useful when combined with `--use-default` to generate models
    where optional fields have defaults but cannot accept `None` values.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="nullable_strict_nullable.py",
        extra_args=["--strict-nullable"],
    )


def test_main_openapi_ref_nullable_strict_nullable(output_file: Path) -> None:
    """Test that nullable attribute from $ref schema is propagated."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "ref_nullable.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="ref_nullable_strict_nullable.py",
        extra_args=["--strict-nullable", "--use-union-operator"],
    )


@LEGACY_BLACK_SKIP
@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "general.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "pydantic_v2.py",
        ),
        (
            "msgspec.Struct",
            "msgspec_pattern.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_pattern(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test OpenAPI generation with pattern validation."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "pattern.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=f"pattern/{expected_output}",
        extra_args=["--target-python-version", "3.10", "--output-model-type", output_model],
        transform=lambda s: s.replace("pattern.yaml", "pattern.json"),
    )


@pytest.mark.parametrize(
    ("expected_output", "args"),
    [
        ("pattern_with_lookaround_pydantic_v2.py", []),
        (
            "pattern_with_lookaround_pydantic_v2_field_constraints.py",
            ["--field-constraints"],
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] < "22",
    reason="Installed black doesn't support Python version 3.10",
)
def test_main_openapi_pattern_with_lookaround_pydantic_v2(
    expected_output: str, args: list[str], output_file: Path
) -> None:
    """Test OpenAPI generation with pattern lookaround for Pydantic v2."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "pattern_lookaround.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--target-python-version", "3.10", "--output-model-type", "pydantic_v2.BaseModel", *args],
    )


def test_main_generate_custom_class_name_generator_modular(
    tmp_path: Path,
) -> None:
    """Test OpenAPI generation with custom class name generator in modular mode."""
    output_path = tmp_path / "model"
    main_modular_custom_class_name_dir = EXPECTED_OPENAPI_PATH / "modular_custom_class_name"

    def custom_class_name_generator(name: str) -> str:
        return f"Custom{name[0].upper() + name[1:]}"

    with freeze_time(TIMESTAMP):
        input_ = (OPEN_API_DATA_PATH / "modular.yaml").relative_to(Path.cwd())
        assert not input_.is_absolute()
        generate(
            input_=input_,
            input_file_type=InputFileType.OpenAPI,
            output=output_path,
            custom_class_name_generator=custom_class_name_generator,
        )

        assert_directory_content(output_path, main_modular_custom_class_name_dir)


def test_main_http_openapi(mocker: MockerFixture, output_file: Path) -> None:
    """Test OpenAPI code generation from HTTP URL."""

    def get_mock_response(path: str) -> Mock:
        mock = mocker.Mock()
        mock.text = (OPEN_API_DATA_PATH / path).read_text()
        return mock

    httpx_get_mock = mocker.patch(
        "httpx.get",
        side_effect=[
            get_mock_response("refs.yaml"),
            get_mock_response("definitions.yaml"),
        ],
    )

    run_main_url_and_assert(
        url="https://example.com/refs.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="http_refs.py",
    )
    httpx_get_mock.assert_has_calls([
        call(
            "https://example.com/refs.yaml",
            headers=None,
            verify=True,
            follow_redirects=True,
            params=None,
            timeout=30.0,
        ),
        call(
            "https://teamdigitale.github.io/openapi/0.0.6/definitions.yaml",
            headers=None,
            verify=True,
            follow_redirects=True,
            params=None,
            timeout=30.0,
        ),
    ])


@pytest.mark.cli_doc(
    options=["--disable-appending-item-suffix"],
    input_schema="openapi/api_constrained.yaml",
    cli_args=["--disable-appending-item-suffix", "--field-constraints"],
    golden_output="openapi/disable_appending_item_suffix.py",
)
def test_main_disable_appending_item_suffix(output_file: Path) -> None:
    """Disable appending 'Item' suffix to array item types.

    The `--disable-appending-item-suffix` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_constrained.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--field-constraints", "--disable-appending-item-suffix"],
    )


@pytest.mark.cli_doc(
    options=["--openapi-scopes"],
    input_schema="openapi/body_and_parameters.yaml",
    cli_args=["--openapi-scopes", "paths", "schemas"],
    golden_output="openapi/body_and_parameters/general.py",
)
def test_main_openapi_body_and_parameters(output_file: Path) -> None:
    """Specify OpenAPI scopes to generate (schemas, paths, parameters).

    The `--openapi-scopes` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "body_and_parameters.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "body_and_parameters" / "general.py",
        extra_args=["--openapi-scopes", "paths", "schemas"],
    )


def test_main_openapi_body_and_parameters_remote_ref(mocker: MockerFixture, output_file: Path) -> None:
    """Test OpenAPI generation with body and parameters remote reference."""
    input_path = OPEN_API_DATA_PATH / "body_and_parameters_remote_ref.yaml"
    person_response = mocker.Mock()
    person_response.text = input_path.read_text()
    httpx_get_mock = mocker.patch("httpx.get", side_effect=[person_response])

    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "body_and_parameters" / "remote_ref.py",
        extra_args=["--openapi-scopes", "paths", "schemas"],
    )
    httpx_get_mock.assert_has_calls([
        call(
            "https://schema.example",
            headers=None,
            verify=True,
            follow_redirects=True,
            params=None,
            timeout=30.0,
        ),
    ])


def test_main_openapi_body_and_parameters_only_paths(output_file: Path) -> None:
    """Test OpenAPI generation with only paths scope."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "body_and_parameters.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "body_and_parameters" / "only_paths.py",
        extra_args=["--openapi-scopes", "paths"],
    )


def test_main_openapi_body_and_parameters_only_schemas(output_file: Path) -> None:
    """Test OpenAPI generation with only schemas scope."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "body_and_parameters.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "body_and_parameters" / "only_schemas.py",
        extra_args=["--openapi-scopes", "schemas"],
    )


def test_main_openapi_content_in_parameters(output_file: Path) -> None:
    """Test OpenAPI generation with content in parameters."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "content_in_parameters.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="content_in_parameters.py",
    )


def test_main_openapi_oas_response_reference(output_file: Path) -> None:
    """Test OpenAPI generation with OAS response reference."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "oas_response_reference.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="oas_response_reference.py",
        extra_args=["--openapi-scopes", "paths", "schemas"],
    )


def test_main_openapi_json_pointer(output_file: Path) -> None:
    """Test OpenAPI generation with JSON pointer references."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "json_pointer.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="json_pointer.py",
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        ("pydantic.BaseModel", "use_annotated_with_field_constraints.py"),
        (
            "pydantic_v2.BaseModel",
            "use_annotated_with_field_constraints_pydantic_v2.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--use-annotated"],
    input_schema="openapi/api_constrained.yaml",
    cli_args=["--field-constraints", "--use-annotated"],
    golden_output="openapi/use_annotated_with_field_constraints.py",
    related_options=["--field-constraints"],
)
def test_main_use_annotated_with_field_constraints(
    output_model: str, expected_output: str, min_version: str, output_file: Path
) -> None:
    """Use typing.Annotated for field constraints in OpenAPI schemas.

    The `--use-annotated` flag wraps field types with `typing.Annotated` to
    include constraint metadata, enabling runtime validation frameworks to
    access constraints directly from type annotations.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_constrained.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=[
            "--field-constraints",
            "--use-annotated",
            "--target-python-version",
            min_version,
            "--output-model-type",
            output_model,
        ],
    )


def test_main_nested_enum(output_file: Path) -> None:
    """Test OpenAPI generation with nested enum."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nested_enum.json",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
    )


def test_openapi_special_yaml_keywords(mocker: MockerFixture, output_file: Path) -> None:
    """Test OpenAPI generation with special YAML keywords."""
    mock_prance = mocker.patch("prance.BaseParser")
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "special_yaml_keywords.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="special_yaml_keywords.py",
        extra_args=["--validation"],
    )
    mock_prance.assert_called_once()


@pytest.mark.skipif(
    black.__version__.split(".")[0] < "22",
    reason="Installed black doesn't support Python version 3.10",
)
def test_main_openapi_nullable_use_union_operator(output_file: Path) -> None:
    """Test OpenAPI generation with nullable using union operator."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="nullable_strict_nullable_use_union_operator.py",
        extra_args=["--use-union-operator", "--strict-nullable"],
    )


def test_external_relative_ref(tmp_path: Path) -> None:
    """Test OpenAPI generation with external relative references."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "external_relative_ref" / "model_b",
        output_path=tmp_path,
        expected_directory=EXPECTED_OPENAPI_PATH / "external_relative_ref",
    )


def test_paths_external_ref(output_file: Path) -> None:
    """Test OpenAPI generation with external refs in paths without components/schemas."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "paths_external_ref" / "openapi.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="paths_external_ref.py",
        extra_args=["--openapi-scopes", "paths"],
    )


def test_paths_ref_with_external_schema(output_file: Path) -> None:
    """Test OpenAPI generation with $ref to external path file containing relative schema refs."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "paths_ref_with_external_schema" / "openapi.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="paths_ref_with_external_schema.py",
        extra_args=["--openapi-scopes", "schemas", "paths"],
    )


@LEGACY_BLACK_SKIP
@pytest.mark.benchmark
@pytest.mark.cli_doc(
    options=["--collapse-root-models"],
    input_schema="openapi/not_real_string.json",
    cli_args=["--collapse-root-models"],
    golden_output="openapi/not_real_string_collapse_root_models.py",
)
def test_main_collapse_root_models(output_file: Path) -> None:
    """Inline root model definitions into their referencing locations.

    The `--collapse-root-models` flag collapses root model definitions by
    inlining their types directly where they are referenced, reducing the
    number of generated classes.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "not_real_string.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models"],
    )


def test_main_collapse_root_models_field_constraints(output_file: Path) -> None:
    """Test OpenAPI generation with collapsed root models and field constraints."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "not_real_string.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models", "--field-constraints"],
    )


def test_main_collapse_root_models_with_references_to_flat_types(output_file: Path) -> None:
    """Test OpenAPI generation with collapsed root models referencing flat types."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "flat_type.jsonschema",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models"],
    )


def test_main_openapi_max_items_enum(output_file: Path) -> None:
    """Test OpenAPI generation with max items enum."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "max_items_enum.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="max_items_enum.py",
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "const.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "const_pydantic_v2.py",
        ),
    ],
)
def test_main_openapi_const(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test OpenAPI generation with const values."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "const.json",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "const_field.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "const_field_pydantic_v2.py",
        ),
        (
            "msgspec.Struct",
            "const_field_msgspec.py",
        ),
        (
            "typing.TypedDict",
            "const_field_typed_dict.py",
        ),
        (
            "dataclasses.dataclass",
            "const_field_dataclass.py",
        ),
    ],
)
@pytest.mark.cli_doc(
    options=["--collapse-root-models"],
    input_schema="openapi/const.yaml",
    cli_args=["--collapse-root-models"],
    model_outputs={
        "pydantic_v1": "openapi/const_field.py",
        "pydantic_v2": "openapi/const_field_pydantic_v2.py",
        "msgspec": "openapi/const_field_msgspec.py",
        "typeddict": "openapi/const_field_typed_dict.py",
        "dataclass": "openapi/const_field_dataclass.py",
    },
    comparison_output="openapi/const_baseline.py",
    primary=True,
)
def test_main_openapi_const_field(output_model: str, expected_output: str, output_file: Path) -> None:
    """Inline root model definitions instead of creating separate wrapper classes.

    The `--collapse-root-models` option generates simpler output by inlining root models
    directly instead of creating separate wrapper types. This shows how different output
    model types (Pydantic v1/v2, dataclass, TypedDict, msgspec) handle const fields.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "const.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model, "--collapse-root-models"],
    )


def test_main_openapi_complex_reference(output_file: Path) -> None:
    """Test OpenAPI generation with complex references."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "complex_reference.json",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="complex_reference.py",
    )


def test_main_openapi_reference_to_object_properties(output_file: Path) -> None:
    """Test OpenAPI generation with reference to object properties."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "reference_to_object_properties.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="reference_to_object_properties.py",
    )


def test_main_openapi_reference_to_object_properties_collapse_root_models(output_file: Path) -> None:
    """Test OpenAPI generation with reference to object properties and collapsed root models."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "reference_to_object_properties.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="reference_to_object_properties_collapse_root_models.py",
        extra_args=["--collapse-root-models"],
    )


def test_main_openapi_override_required_all_of_field(output_file: Path) -> None:
    """Test OpenAPI generation with override required allOf field."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "override_required_all_of.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="override_required_all_of.py",
        extra_args=["--collapse-root-models"],
    )


def test_main_openapi_allof_with_required_inherited_fields(output_file: Path) -> None:
    """Test OpenAPI generation with allOf where required includes inherited fields."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_required_inherited_fields.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_with_required_inherited_fields.py",
    )


def test_main_openapi_allof_with_required_inherited_fields_force_optional(output_file: Path) -> None:
    """Test OpenAPI generation with allOf and --force-optional flag."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_required_inherited_fields.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_with_required_inherited_fields_force_optional.py",
        extra_args=["--force-optional"],
    )


def test_main_openapi_allof_with_required_inherited_nested_object(output_file: Path) -> None:
    """Test OpenAPI generation with allOf where required includes inherited nested object fields."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_required_inherited_nested_object.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_with_required_inherited_nested_object.py",
    )


def test_main_openapi_allof_with_required_inherited_complex_allof(output_file: Path) -> None:
    """Test OpenAPI generation with allOf where required includes complex allOf fields."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_required_inherited_complex_allof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_with_required_inherited_complex_allof.py",
    )


def test_main_openapi_allof_with_required_inherited_comprehensive(output_file: Path) -> None:
    """Test OpenAPI generation with allOf covering all type inheritance scenarios."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_required_inherited_comprehensive.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_with_required_inherited_comprehensive.py",
    )


def test_main_openapi_allof_partial_override_inherited_types(output_file: Path) -> None:
    """Test OpenAPI allOf partial overrides inherit parent field types."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_partial_override_inherited_types.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_partial_override_inherited_types.py",
    )


def test_main_openapi_allof_partial_override_array_items(output_file: Path) -> None:
    """Test OpenAPI allOf partial overrides inherit parent array item types."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_partial_override_array_items.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_partial_override_array_items.py",
    )


def test_main_openapi_allof_partial_override_array_items_no_parent(output_file: Path) -> None:
    """Test OpenAPI allOf with array field not present in parent schema."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_partial_override_array_items_no_parent.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_partial_override_array_items_no_parent.py",
    )


def test_main_openapi_allof_partial_override_non_array_field(output_file: Path) -> None:
    """Test OpenAPI allOf partial override with non-array fields for coverage."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_partial_override_non_array_field.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_partial_override_non_array_field.py",
    )


def test_main_openapi_allof_partial_override_nested_array_items(output_file: Path) -> None:
    """Test OpenAPI allOf partial override with nested arrays for coverage."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_partial_override_nested_array_items.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_partial_override_nested_array_items.py",
    )


def test_main_openapi_allof_partial_override_deeply_nested_array(output_file: Path) -> None:
    """Test OpenAPI allOf partial override with 3-level nested arrays for while loop coverage."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_partial_override_deeply_nested_array.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_partial_override_deeply_nested_array.py",
    )


def test_main_openapi_allof_partial_override_simple_list_any(output_file: Path) -> None:
    """Test OpenAPI allOf partial override with simple List[Any] - while loop NOT entered."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_partial_override_simple_list_any.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_partial_override_simple_list_any.py",
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        ("pydantic.BaseModel", "allof_partial_override_unique_items.py"),
        ("pydantic_v2.BaseModel", "allof_partial_override_unique_items_pydantic_v2.py"),
    ],
)
def test_main_openapi_allof_partial_override_unique_items(
    output_model: str, expected_output: str, output_file: Path
) -> None:
    """Test OpenAPI allOf partial override inherits uniqueItems from parent."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_partial_override_unique_items.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--use-unique-items-as-set", "--output-model-type", output_model],
    )


@pytest.mark.cli_doc(
    options=["--allof-merge-mode"],
    input_schema="openapi/allof_materialize_defaults.yaml",
    cli_args=["--allof-merge-mode", "all"],
    golden_output="main/openapi/allof_materialize_defaults.py",
)
def test_main_openapi_allof_merge_mode_all(output_file: Path) -> None:
    """Merge all properties from parent schemas in allOf.

    The `--allof-merge-mode` flag controls how parent schema properties are merged
    in allOf compositions. With `all` mode, constraints plus annotations (default,
    examples) are merged from parent properties. This ensures child schemas inherit
    all metadata from parents.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_materialize_defaults.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_materialize_defaults.py",
        extra_args=["--allof-merge-mode", "all"],
    )


@pytest.mark.cli_doc(
    options=["--allof-merge-mode"],
    input_schema="openapi/allof_merge_mode_none.yaml",
    cli_args=["--allof-merge-mode", "none"],
    golden_output="main/openapi/allof_merge_mode_none.py",
    comparison_output="main/openapi/allof_materialize_defaults.py",
)
def test_main_openapi_allof_merge_mode_none(output_file: Path) -> None:
    """Disable property merging from parent schemas in allOf.

    With `none` mode, no fields are merged from parent properties. This is useful
    when you want child schemas to define all their own constraints without inheriting
    from parents.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_merge_mode_none.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_merge_mode_none.py",
        extra_args=["--allof-merge-mode", "none"],
    )


def test_main_openapi_allof_property_bool_schema(output_file: Path) -> None:
    """Test OpenAPI allOf with bool property schema (e.g., `allowed: true`)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_property_bool_schema.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_property_bool_schema.py",
    )


def test_main_openapi_allof_parent_no_properties(output_file: Path) -> None:
    """Test OpenAPI allOf with parent schema having no properties."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_parent_no_properties.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_parent_no_properties.py",
    )


def test_main_openapi_allof_parent_bool_property(output_file: Path) -> None:
    """Test OpenAPI allOf with parent having bool property schema (true/false)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_parent_bool_property.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_parent_bool_property.py",
    )


def test_main_openapi_allof_multiple_parents_same_property(output_file: Path) -> None:
    """Test OpenAPI allOf with multiple parents having the same property."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_multiple_parents_same_property.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_multiple_parents_same_property.py",
    )


def test_main_openapi_allof_with_required_inherited_edge_cases(output_file: Path) -> None:
    """Test OpenAPI generation with allOf edge cases for branch coverage."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_required_inherited_edge_cases.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="allof_with_required_inherited_edge_cases.py",
    )


@LEGACY_BLACK_SKIP
def test_main_openapi_allof_with_required_inherited_coverage(output_file: Path) -> None:
    """Test OpenAPI generation with allOf coverage for edge case branches."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "allof_with_required_inherited_coverage.yaml",
            output_path=output_file,
            input_file_type="openapi",
            assert_func=assert_file_content,
            expected_file="allof_with_required_inherited_coverage.py",
        )
        # Verify the warning was raised for $ref combined with constraints
        assert any("allOf combines $ref" in str(warning.message) for warning in w)


def test_main_use_default_kwarg(output_file: Path) -> None:
    """Test OpenAPI generation with use default kwarg."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        extra_args=["--use-default-kwarg"],
    )


@pytest.mark.parametrize(
    ("input_", "output"),
    [
        (
            "discriminator.yaml",
            "general.py",
        ),
        (
            "discriminator_without_mapping.yaml",
            "without_mapping.py",
        ),
    ],
)
def test_main_openapi_discriminator(input_: str, output: str, output_file: Path) -> None:
    """Test OpenAPI generation with discriminator."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / input_,
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / output,
    )


@freeze_time("2023-07-27")
@pytest.mark.parametrize(
    ("kind", "option", "expected"),
    [
        (
            "anyOf",
            "--collapse-root-models",
            "in_array_collapse_root_models.py",
        ),
        (
            "oneOf",
            "--collapse-root-models",
            "in_array_collapse_root_models.py",
        ),
        ("anyOf", None, "in_array.py"),
        ("oneOf", None, "in_array.py"),
    ],
)
def test_main_openapi_discriminator_in_array(kind: str, option: str | None, expected: str, output_file: Path) -> None:
    """Test OpenAPI generation with discriminator in array."""
    input_file = f"discriminator_in_array_{kind.lower()}.yaml"
    extra_args = [option] if option else []
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / input_file,
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=f"discriminator/{expected}",
        extra_args=extra_args,
        transform=lambda s: s.replace(input_file, "discriminator_in_array.yaml"),
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "default_object",
        ),
        (
            "pydantic_v2.BaseModel",
            "pydantic_v2_default_object",
        ),
        (
            "msgspec.Struct",
            "msgspec_default_object",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_default_object(output_model: str, expected_output: str, tmp_path: Path) -> None:
    """Test OpenAPI generation with default object values."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "default_object.yaml",
        output_path=tmp_path,
        expected_directory=EXPECTED_OPENAPI_PATH / expected_output,
        input_file_type="openapi",
        extra_args=["--output-model-type", output_model, "--target-python-version", "3.10"],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "union_default_object.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "pydantic_v2_union_default_object.py",
        ),
        (
            "msgspec.Struct",
            "msgspec_union_default_object.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_union_default_object(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test OpenAPI generation with Union type default object values."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "union_default_object.yaml",
        output_path=output_file,
        expected_file=EXPECTED_OPENAPI_PATH / expected_output,
        input_file_type="openapi",
        extra_args=[
            "--output-model-type",
            output_model,
            "--target-python-version",
            "3.10",
            "--openapi-scopes",
            "schemas",
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "empty_dict_default.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "pydantic_v2_empty_dict_default.py",
        ),
        (
            "msgspec.Struct",
            "msgspec_empty_dict_default.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_empty_dict_default(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test OpenAPI generation with empty dict default values."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "empty_dict_default.yaml",
        output_path=output_file,
        expected_file=EXPECTED_OPENAPI_PATH / expected_output,
        input_file_type="openapi",
        extra_args=[
            "--output-model-type",
            output_model,
            "--target-python-version",
            "3.10",
            "--openapi-scopes",
            "schemas",
        ],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "empty_list_default.py",
        ),
        (
            "pydantic_v2.BaseModel",
            "pydantic_v2_empty_list_default.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_empty_list_default(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test OpenAPI generation with empty list default values."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "empty_list_default.yaml",
        output_path=output_file,
        expected_file=EXPECTED_OPENAPI_PATH / expected_output,
        input_file_type="openapi",
        extra_args=[
            "--output-model-type",
            output_model,
            "--target-python-version",
            "3.10",
            "--openapi-scopes",
            "schemas",
        ],
    )


def test_main_dataclass(output_file: Path) -> None:
    """Test OpenAPI generation with dataclass output."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "dataclasses.dataclass"],
    )


def test_main_dataclass_base_class(output_file: Path) -> None:
    """Test OpenAPI generation with dataclass base class."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "dataclasses.dataclass", "--base-class", "custom_base.Base"],
    )


def test_main_openapi_reference_same_hierarchy_directory(tmp_path: Path) -> None:
    """Test OpenAPI generation with reference in same hierarchy directory."""
    output_file: Path = tmp_path / "output.py"
    with chdir(OPEN_API_DATA_PATH / "reference_same_hierarchy_directory"):
        run_main_and_assert(
            input_path=Path("./public/entities.yaml"),
            output_path=output_file,
            input_file_type="openapi",
            assert_func=assert_file_content,
            expected_file="reference_same_hierarchy_directory.py",
        )


def test_main_multiple_required_any_of(output_file: Path) -> None:
    """Test OpenAPI generation with multiple required anyOf."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "multiple_required_any_of.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--collapse-root-models"],
    )


def test_main_openapi_max_min(output_file: Path) -> None:
    """Test OpenAPI generation with max and min constraints."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "max_min_number.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="max_min_number.py",
    )


@pytest.mark.cli_doc(
    options=["--use-operation-id-as-name"],
    input_schema="openapi/api.yaml",
    cli_args=["--use-operation-id-as-name", "--openapi-scopes", "paths", "schemas", "parameters"],
    golden_output="openapi/use_operation_id_as_name.py",
)
def test_main_openapi_use_operation_id_as_name(output_file: Path) -> None:
    """Use OpenAPI operationId as the generated function/class name.

    The `--use-operation-id-as-name` flag configures the code generation behavior.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="use_operation_id_as_name.py",
        extra_args=["--use-operation-id-as-name", "--openapi-scopes", "paths", "schemas", "parameters"],
    )


def test_main_openapi_use_operation_id_as_name_not_found_operation_id(
    capsys: pytest.CaptureFixture, output_file: Path
) -> None:
    """Test OpenAPI generation with operation ID as name when ID not found."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "body_and_parameters.yaml",
        output_path=output_file,
        input_file_type="openapi",
        expected_exit=Exit.ERROR,
        extra_args=["--use-operation-id-as-name", "--openapi-scopes", "paths", "schemas", "parameters"],
        capsys=capsys,
        expected_stderr_contains="All operations must have an operationId when --use_operation_id_as_name is set.",
    )


def test_main_unsorted_optional_fields(output_file: Path) -> None:
    """Test OpenAPI generation with unsorted optional fields."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "unsorted_optional_fields.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "dataclasses.dataclass"],
    )


def test_main_typed_dict(output_file: Path) -> None:
    """Test OpenAPI generation with TypedDict output."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


def test_main_typed_dict_py(min_version: str, output_file: Path) -> None:
    """Test OpenAPI generation with TypedDict for specific Python version."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "typing.TypedDict", "--target-python-version", min_version],
    )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.3.0"),
    reason="Require Black version 23.3.0 or later ",
)
def test_main_modular_typed_dict(output_dir: Path) -> None:
    """Test main function on modular file."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "modular.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "modular_typed_dict",
            extra_args=["--output-model-type", "typing.TypedDict", "--target-python-version", "3.11"],
        )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.3.0"),
    reason="Require Black version 23.3.0 or later ",
)
def test_main_typed_dict_nullable(output_file: Path) -> None:
    """Test OpenAPI generation with nullable TypedDict."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "typing.TypedDict", "--target-python-version", "3.11"],
    )


@LEGACY_BLACK_SKIP
@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.3.0"),
    reason="Require Black version 23.3.0 or later ",
)
def test_main_msgspec_nullable(output_file: Path) -> None:
    """Test OpenAPI generation with nullable msgspec.Struct."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="msgspec_nullable.py",
        extra_args=["--output-model-type", "msgspec.Struct", "--target-python-version", "3.11"],
    )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.3.0"),
    reason="Require Black version 23.3.0 or later ",
)
def test_main_typed_dict_nullable_strict_nullable(output_file: Path) -> None:
    """Test OpenAPI generation with strict nullable TypedDict."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "typing.TypedDict", "--target-python-version", "3.11", "--strict-nullable"],
    )


@pytest.mark.benchmark
def test_main_openapi_nullable_31(output_file: Path) -> None:
    """Test OpenAPI 3.1 generation with nullable types."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable_31.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="nullable_31.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--strip-default-none", "--use-union-operator"],
    )


def test_main_openapi_nullable_required_annotated(output_file: Path) -> None:
    """Test OpenAPI generation with nullable required fields using annotations."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable_required_annotated.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="nullable_required_annotated.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--strict-nullable",
            "--use-annotated",
            "--snake-case-field",
        ],
    )


@pytest.mark.cli_doc(
    options=["--custom-file-header-path"],
    input_schema="openapi/api.yaml",
    cli_args=["--custom-file-header-path", "custom_file_header.txt"],
    golden_output="openapi/custom_file_header.py",
)
def test_main_custom_file_header_path(output_file: Path) -> None:
    """Add custom header content from file to generated code.

    The `--custom-file-header-path` flag allows you to specify a file containing
    custom header content (like copyright notices, linting directives, or module docstrings)
    to be inserted at the top of generated Python files.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_file_header.py",
        extra_args=["--custom-file-header-path", str(DATA_PATH / "custom_file_header.txt")],
    )


def test_main_custom_file_header_duplicate_options(capsys: pytest.CaptureFixture, output_file: Path) -> None:
    """Test OpenAPI generation with duplicate custom file header options."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        expected_exit=Exit.ERROR,
        extra_args=[
            "--custom-file-header-path",
            str(DATA_PATH / "custom_file_header.txt"),
            "--custom-file-header",
            "abc",
        ],
        capsys=capsys,
        expected_stderr_contains="`--custom_file_header_path` can not be used with `--custom_file_header`.",
    )


def test_main_custom_file_header_with_docstring(output_file: Path) -> None:
    """Test future import placement after docstring in custom header."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_file_header_with_docstring.py",
        extra_args=["--custom-file-header-path", str(DATA_PATH / "custom_file_header_with_docstring.txt")],
    )


def test_main_custom_file_header_with_import(output_file: Path) -> None:
    """Test future import placement before existing imports in custom header."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_file_header_with_import.py",
        extra_args=["--custom-file-header-path", str(DATA_PATH / "custom_file_header_with_import.txt")],
    )


def test_main_custom_file_header_with_docstring_and_import(output_file: Path) -> None:
    """Test future import placement with docstring and imports in custom header."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_file_header_with_docstring_and_import.py",
        extra_args=["--custom-file-header-path", str(DATA_PATH / "custom_file_header_with_docstring_and_import.txt")],
    )


def test_main_custom_file_header_without_future_imports(output_file: Path) -> None:
    """Test custom header with --disable-future-imports option."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_file_header_no_future.py",
        extra_args=[
            "--custom-file-header-path",
            str(DATA_PATH / "custom_file_header.txt"),
            "--disable-future-imports",
        ],
    )


def test_main_custom_file_header_empty(output_file: Path) -> None:
    """Test empty custom header file."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_file_header_empty.py",
        extra_args=["--custom-file-header-path", str(DATA_PATH / "custom_file_header_empty.txt")],
    )


def test_main_custom_file_header_invalid_syntax(output_file: Path) -> None:
    """Test custom header with invalid Python syntax."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_file_header_invalid_syntax.py",
        extra_args=["--custom-file-header-path", str(DATA_PATH / "custom_file_header_invalid_syntax.txt")],
        skip_code_validation=True,
    )


def test_main_custom_file_header_comments_only(output_file: Path) -> None:
    """Test custom header with only comments (no statements)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_file_header_comments_only.py",
        extra_args=["--custom-file-header-path", str(DATA_PATH / "custom_file_header_comments_only.txt")],
    )


def test_main_pydantic_v2(output_file: Path) -> None:
    """Test OpenAPI generation with Pydantic v2 output."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_custom_id_pydantic_v2(output_file: Path) -> None:
    """Test OpenAPI generation with custom ID for Pydantic v2."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "custom_id.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="custom_id_pydantic_v2.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


@pytest.mark.cli_doc(
    options=["--use-serialize-as-any"],
    input_schema="openapi/serialize_as_any.yaml",
    cli_args=["--use-serialize-as-any"],
    golden_output="openapi/serialize_as_any_pydantic_v2.py",
)
def test_main_openapi_serialize_as_any_pydantic_v2(output_file: Path) -> None:
    """Wrap fields with subtypes in Pydantic's SerializeAsAny.

    The `--use-serialize-as-any` flag applies Pydantic v2's SerializeAsAny wrapper
    to fields that have subtype relationships, ensuring proper serialization of
    polymorphic types and inheritance hierarchies.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "serialize_as_any.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="serialize_as_any_pydantic_v2.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--use-serialize-as-any"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_all_of_with_relative_ref(output_file: Path) -> None:
    """Test OpenAPI generation with allOf and relative reference."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "all_of_with_relative_ref" / "openapi.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="all_of_with_relative_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--keep-model-order",
            "--collapse-root-models",
            "--field-constraints",
            "--use-title-as-name",
            "--field-include-all-keys",
            "--use-field-description",
        ],
    )


@LEGACY_BLACK_SKIP
def test_main_openapi_msgspec_struct(min_version: str, output_file: Path) -> None:
    """Test OpenAPI generation with msgspec Struct output."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="msgspec_struct.py",
        extra_args=["--target-python-version", min_version, "--output-model-type", "msgspec.Struct"],
    )


@LEGACY_BLACK_SKIP
def test_main_openapi_msgspec_struct_snake_case(min_version: str, output_file: Path) -> None:
    """Test OpenAPI generation with msgspec Struct and snake case."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_ordered_required_fields.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="msgspec_struct_snake_case.py",
        extra_args=[
            "--target-python-version",
            min_version,
            "--snake-case-field",
            "--output-model-type",
            "msgspec.Struct",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_openapi_msgspec_use_annotated_with_field_constraints(output_file: Path) -> None:
    """Test OpenAPI generation with msgspec using Annotated and field constraints."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_constrained.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="msgspec_use_annotated_with_field_constraints.py",
        extra_args=["--field-constraints", "--target-python-version", "3.10", "--output-model-type", "msgspec.Struct"],
    )


@pytest.mark.parametrize(
    ("output_model", "expected_file"),
    [
        ("pydantic_v2.BaseModel", "discriminator/enum_one_literal_as_default.py"),
        ("dataclasses.dataclass", "discriminator/dataclass_enum_one_literal_as_default.py"),
    ],
)
@pytest.mark.cli_doc(
    options=["--use-one-literal-as-default"],
    input_schema="openapi/discriminator_enum.yaml",
    cli_args=["--use-one-literal-as-default"],
    model_outputs={
        "pydantic_v2": "openapi/discriminator/enum_one_literal_as_default.py",
        "dataclass": "openapi/discriminator/dataclass_enum_one_literal_as_default.py",
    },
)
def test_main_openapi_discriminator_one_literal_as_default(
    output_model: str, expected_file: str, output_file: Path
) -> None:
    """Set default value when only one literal is valid for a discriminator field.

    The `--use-one-literal-as-default` flag sets default values for discriminator
    fields when only one literal value is valid, reducing boilerplate in model
    instantiation.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / expected_file,
        extra_args=["--output-model-type", output_model, "--use-one-literal-as-default"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_one_literal_as_default_dataclass_py310(output_file: Path) -> None:
    """Test OpenAPI generation with discriminator one literal as default for dataclass with Python 3.10+."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "discriminator_enum.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "discriminator" / "dataclass_enum_one_literal_as_default_py310.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--use-one-literal-as-default",
            "--target-python-version",
            "3.10",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_dataclass_inheritance_parent_default(output_file: Path) -> None:
    """Test dataclass field ordering fix when parent has default field."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "dataclass_inheritance_field_ordering.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_OPENAPI_PATH / "dataclass_inheritance_field_ordering_py310.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--target-python-version",
            "3.10",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_keyword_only_dataclass(output_file: Path) -> None:
    """Test OpenAPI generation with keyword-only dataclass."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "inheritance.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="dataclass_keyword_only.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--keyword-only",
            "--target-python-version",
            "3.10",
        ],
    )


def test_main_openapi_dataclass_with_naive_datetime(capsys: pytest.CaptureFixture, output_file: Path) -> None:
    """Test OpenAPI generation with dataclass using naive datetime."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "inheritance.yaml",
        output_path=output_file,
        input_file_type="openapi",
        expected_exit=Exit.ERROR,
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--output-datetime-class",
            "NaiveDatetime",
        ],
        capsys=capsys,
        expected_stderr_contains=(
            '`--output-datetime-class` only allows "datetime" for `--output-model-type` dataclasses.dataclass'
        ),
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_keyword_only_msgspec(min_version: str, output_file: Path) -> None:
    """Test OpenAPI generation with keyword-only msgspec."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "inheritance.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="msgspec_keyword_only.py",
        extra_args=["--output-model-type", "msgspec.Struct", "--keyword-only", "--target-python-version", min_version],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_keyword_only_msgspec_with_extra_data(min_version: str, output_file: Path) -> None:
    """Test OpenAPI generation with keyword-only msgspec and extra data."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "inheritance.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="msgspec_keyword_only_omit_defaults.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--keyword-only",
            "--target-python-version",
            min_version,
            "--extra-template-data",
            str(OPEN_API_DATA_PATH / "extra_data_msgspec.json"),
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_generate_openapi_keyword_only_msgspec_with_extra_data(tmp_path: Path) -> None:
    """Test OpenAPI generation with keyword-only msgspec using generate function."""
    extra_data = json.loads((OPEN_API_DATA_PATH / "extra_data_msgspec.json").read_text())
    output_file: Path = tmp_path / "output.py"
    generate(
        input_=OPEN_API_DATA_PATH / "inheritance.yaml",
        output=output_file,
        input_file_type=InputFileType.OpenAPI,
        output_model_type=DataModelType.MsgspecStruct,
        keyword_only=True,
        target_python_version=PythonVersionMin,
        extra_template_data=defaultdict(dict, extra_data),
        # Following values are defaults in the CLI, but not in the API
        openapi_scopes=[OpenAPIScope.Schemas],
        # Following values are implied by `msgspec.Struct` in the CLI
        use_annotated=True,
        field_constraints=True,
    )
    assert_file_content(output_file, "msgspec_keyword_only_omit_defaults.py")


@pytest.mark.skipif(
    black.__version__.split(".")[0] < "22",
    reason="Installed black doesn't support Python version 3.10",
)
@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_openapi_msgspec_use_union_operator(output_file: Path) -> None:
    """Test msgspec Struct generation with union operator (Python 3.10+)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "nullable.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="msgspec_use_union_operator.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--use-union-operator",
            "--target-python-version",
            "3.10",
        ],
    )


@MSGSPEC_LEGACY_BLACK_SKIP
def test_main_openapi_msgspec_anyof(min_version: str, output_file: Path) -> None:
    """Test msgspec Struct generation with anyOf fields."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "anyof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="msgspec_anyof.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--target-python-version",
            min_version,
        ],
    )


@LEGACY_BLACK_SKIP
def test_main_openapi_msgspec_oneof_with_null(output_file: Path) -> None:
    """Test msgspec Struct generation with oneOf containing null type."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "msgspec_oneof_with_null.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="msgspec_oneof_with_null.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
        ],
    )


@LEGACY_BLACK_SKIP
def test_main_openapi_msgspec_oneof_with_null_union_operator(output_file: Path) -> None:
    """Test msgspec Struct generation with oneOf containing null type using union operator."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "msgspec_oneof_with_null.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="msgspec_oneof_with_null_union_operator.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--use-union-operator",
        ],
    )


def test_main_openapi_referenced_default(output_file: Path) -> None:
    """Test OpenAPI generation with referenced default values."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "referenced_default.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="referenced_default.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_referenced_default_use_annotated(output_file: Path) -> None:
    """Test OpenAPI generation with referenced default values using --use-annotated."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "referenced_default.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="referenced_default_use_annotated.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--use-annotated"],
    )


def test_main_openapi_root_model_default_primitive(output_file: Path) -> None:
    """Test RootModel with primitive default value in union type."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "root_model_default_primitive.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="root_model_default_primitive.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


@pytest.mark.cli_doc(
    options=["--parent-scoped-naming"],
    input_schema="openapi/duplicate_models2.yaml",
    cli_args=[
        "--parent-scoped-naming",
        "--use-operation-id-as-name",
        "--openapi-scopes",
        "paths",
        "schemas",
        "parameters",
    ],
    golden_output="openapi/duplicate_models2.py",
)
def test_duplicate_models(output_file: Path) -> None:
    """Namespace models by their parent scope to avoid naming conflicts.

    The `--parent-scoped-naming` flag prefixes model names with their parent scope
    (operation/path/parameter) to prevent name collisions when the same model name
    appears in different contexts within an OpenAPI specification.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "duplicate_models2.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="duplicate_models2.py",
        extra_args=[
            "--use-operation-id-as-name",
            "--openapi-scopes",
            "paths",
            "schemas",
            "parameters",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--parent-scoped-naming",
        ],
    )


def test_main_openapi_shadowed_imports(output_file: Path) -> None:
    """Test OpenAPI generation with shadowed imports."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "shadowed_imports.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="shadowed_imports.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_extra_fields_forbid(output_file: Path) -> None:
    """Test OpenAPI generation with extra fields forbidden."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "additional_properties.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="additional_properties.py",
        extra_args=["--extra-fields", "forbid"],
    )


def test_main_openapi_same_name_objects(output_file: Path) -> None:
    """Test OpenAPI generation with same name objects."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "same_name_objects.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="same_name_objects.py",
    )


def test_main_openapi_type_alias(output_file: Path) -> None:
    """Test that TypeAliasType is generated for OpenAPI schemas for Python 3.10-3.11."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias.py",
        extra_args=["--use-type-alias"],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 23,
    reason="Installed black doesn't support the new 'type' statement",
)
def test_main_openapi_type_alias_py312(output_file: Path) -> None:
    """Test that type statement syntax is generated for OpenAPI schemas with Python 3.12+ and Pydantic v2."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias.yaml",
        output_path=output_file,
        input_file_type="openapi",
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


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 23,
    reason="Installed black doesn't support the target python version",
)
def test_main_openapi_type_alias_mutual_recursive_py311(output_file: Path) -> None:  # pragma: no cover
    """Test mutual recursive type aliases render with quoted forward refs on Python 3.11."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_mutual_recursive.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias_mutual_recursive.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.11",
            "--output-model-type",
            "pydantic.BaseModel",
        ],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 23,
    reason="Installed black doesn't support the target python version",
)
def test_main_openapi_type_alias_mutual_recursive_typealiastype_py311(output_file: Path) -> None:  # pragma: no cover
    """Test mutual recursive type aliases render with quoted forward refs for TypeAliasType on Python 3.11."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_mutual_recursive.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="msgspec_mutual_type_alias.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.11",
            "--output-model-type",
            "msgspec.Struct",
        ],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 23,
    reason="Installed black doesn't support the target python version",
)
def test_main_openapi_type_alias_recursive_py311(output_file: Path) -> None:  # pragma: no cover
    """Test recursive type aliases render with quoted self references on Python 3.11."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_recursive.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias_recursive_py311.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.11",
            "--output-model-type",
            "pydantic.BaseModel",
        ],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 23,
    reason="Installed black doesn't support the new 'type' statement",
)
def test_main_openapi_type_alias_recursive_py312(output_file: Path) -> None:
    """
    Test that handling of type aliases work as expected for recursive types.

    NOTE: applied to python 3.12--14
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_recursive.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias_recursive_py312.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.12",
            "--use-standard-collections",
            "--use-union-operator",
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_openapi_type_alias_recursive(output_file: Path) -> None:
    """Test recursive type aliases with proper forward reference quoting."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_recursive.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias_recursive.py",
        extra_args=["--use-type-alias"],
    )


def test_main_openapi_type_alias_recursive_pydantic_v2(output_file: Path) -> None:
    """Test recursive RootModel with forward references in Pydantic v2.

    Without --use-type-alias, recursive schemas generate RootModel classes.
    Forward references in the generic parameter must be quoted to avoid
    NameError at class definition time.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_recursive.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias_recursive_pydantic_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_main_openapi_type_alias_cross_module_collision_a(output_file: Path) -> None:
    """Test TypeAlias generation for module A in cross-module collision scenario."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_cross_module_collision" / "a.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias_cross_module_collision_a.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.10",
        ],
    )


def test_main_openapi_type_alias_cross_module_collision_b(output_file: Path) -> None:
    """Test TypeAlias generation for module B with self-referential forward reference."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_cross_module_collision" / "b.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias_cross_module_collision_b.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.10",
        ],
    )


def test_main_openapi_type_alias_forward_ref_multiple(output_file: Path) -> None:
    """Test TypeAlias with multiple forward references that require quoting."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "type_alias_forward_ref_multiple.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="type_alias_forward_ref_multiple.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.10",
        ],
    )


def test_main_openapi_byte_format(output_file: Path) -> None:
    """Test OpenAPI generation with byte format."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "byte_format.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="byte_format.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_unquoted_null(output_file: Path) -> None:
    """Test OpenAPI generation with unquoted null values."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "unquoted_null.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="unquoted_null.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_webhooks(output_file: Path) -> None:
    """Test OpenAPI generation with webhooks scope."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "webhooks.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        extra_args=["--openapi-scopes", "schemas", "webhooks"],
    )


def test_main_openapi_non_operations_and_security(output_file: Path) -> None:
    """Test OpenAPI generation with non-operation fields and security inheritance."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "non_operations_and_security.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        extra_args=["--openapi-scopes", "schemas", "paths", "webhooks"],
    )


def test_main_openapi_webhooks_with_parameters(output_file: Path) -> None:
    """Test OpenAPI generation with webhook-level and operation-level parameters."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "webhooks_with_parameters.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        extra_args=["--openapi-scopes", "schemas", "webhooks", "parameters"],
    )


def test_webhooks_ref_with_external_schema(output_file: Path) -> None:
    """Test OpenAPI generation with $ref to external webhook file containing relative schema refs."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "webhooks_ref_with_external_schema" / "openapi.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="webhooks_ref_with_external_schema.py",
        extra_args=["--openapi-scopes", "schemas", "webhooks"],
    )


def test_main_openapi_external_ref_with_transitive_local_ref(output_file: Path) -> None:
    """Test OpenAPI generation with external ref that has transitive local refs."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "external_ref_with_transitive_local_ref" / "openapi.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="external_ref_with_transitive_local_ref/output.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_namespace_subns_ref(output_dir: Path) -> None:
    """Test OpenAPI generation with namespaced schema referencing subnamespace.

    Regression test for issue #2366: When a schema with a dot-delimited name
    (e.g., ns.wrapper) references another schema in a subnamespace
    (e.g., ns.subns.item), the generated import should be "from . import subns"
    (same package) instead of "from .. import subns" (parent package).
    """
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "namespace_subns_ref.json",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "namespace_subns_ref",
        )


def test_main_openapi_read_only_write_only_default(output_file: Path) -> None:
    """Test readOnly/writeOnly default: base model only."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_default.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


@pytest.mark.cli_doc(
    options=["--read-only-write-only-model-type"],
    input_schema="openapi/read_only_write_only.yaml",
    cli_args=["--output-model-type", "pydantic_v2.BaseModel", "--read-only-write-only-model-type", "request-response"],
    golden_output="openapi/read_only_write_only_request_response.py",
)
def test_main_openapi_read_only_write_only_request_response(output_file: Path) -> None:
    """Generate separate request and response models for readOnly/writeOnly fields.

    The `--read-only-write-only-model-type` option controls how models with readOnly or writeOnly
    properties are generated. The 'request-response' mode creates separate Request and Response
    variants for each schema that contains readOnly or writeOnly fields, allowing proper type
    validation for API requests and responses without a shared base model.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_request_response.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "request-response",
        ],
    )


def test_main_openapi_read_only_write_only_all(output_file: Path) -> None:
    """Test readOnly/writeOnly all: Base + Request + Response models."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_all.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_allof(output_file: Path) -> None:
    """Test readOnly/writeOnly with allOf inheritance."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_allof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_allof.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_allof_request_response(output_file: Path) -> None:
    """Test readOnly/writeOnly with allOf using request-response mode (no base model)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_allof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_allof_request_response.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "request-response",
        ],
    )


def test_main_openapi_read_only_write_only_collision(output_file: Path) -> None:
    """Test readOnly/writeOnly with name collision (UserRequest already exists)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_collision.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_collision.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_ref(output_file: Path) -> None:
    """Test readOnly/writeOnly on $ref target schema."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_ref.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_double_collision(output_file: Path) -> None:
    """Test readOnly/writeOnly with double collision (UserRequest and UserRequestModel exist)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_double_collision.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_double_collision.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_nested_allof(output_file: Path) -> None:
    """Test readOnly/writeOnly with nested allOf inheritance."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_nested_allof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_nested_allof.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_union(output_file: Path) -> None:
    """Test readOnly/writeOnly with Union type field."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_union.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_union.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_url_ref(mocker: MockerFixture, output_file: Path) -> None:
    """Test readOnly/writeOnly with URL $ref to external schema."""
    remote_schema = (OPEN_API_DATA_PATH / "read_only_write_only_url_ref_remote.yaml").read_text()
    mock_response = mocker.Mock()
    mock_response.text = remote_schema

    mocker.patch("httpx.get", return_value=mock_response)

    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_url_ref.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_url_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_allof_url_ref(mocker: MockerFixture, output_file: Path) -> None:
    """Test readOnly/writeOnly with allOf that references external URL schema."""
    remote_schema = (OPEN_API_DATA_PATH / "read_only_write_only_allof_url_ref_remote.yaml").read_text()
    mock_response = mocker.Mock()
    mock_response.text = remote_schema

    mocker.patch("httpx.get", return_value=mock_response)

    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_allof_url_ref.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_allof_url_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_allof_order(output_file: Path) -> None:
    """Test readOnly/writeOnly with allOf where child is listed before parent in schema."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_allof_order.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_allof_order.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_nested_allof_order(output_file: Path) -> None:
    """Test readOnly/writeOnly with nested allOf where models are listed in reverse order."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_nested_allof_order.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_nested_allof_order.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_allof_required_only(output_file: Path) -> None:
    """Test readOnly/writeOnly with allOf containing item with only 'required' (no ref, no properties)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_allof_required_only.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_allof_required_only.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_mixed(output_file: Path) -> None:
    """Test request-response mode generates base models for schemas without readOnly/writeOnly."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_mixed.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_mixed.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "request-response",
        ],
    )


def test_main_openapi_read_only_write_only_anyof(output_file: Path) -> None:
    """Test readOnly/writeOnly detection in anyOf and oneOf compositions."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_anyof.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_anyof.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_duplicate_allof_ref(output_file: Path) -> None:
    """Test readOnly/writeOnly with duplicate $ref in allOf."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_duplicate_allof_ref.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_duplicate_allof_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_ref_with_desc(output_file: Path) -> None:
    """Test readOnly/writeOnly on $ref with description (JsonSchemaObject with ref)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_ref_with_desc.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_ref_with_desc.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_shared_base_ref(output_file: Path) -> None:
    """Test readOnly/writeOnly with diamond inheritance (shared base via multiple paths)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_shared_base_ref.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_shared_base_ref.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_read_only_write_only_empty_base(output_file: Path) -> None:
    """Test readOnly/writeOnly with empty base class (no fields)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "read_only_write_only_empty_base.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="read_only_write_only_empty_base.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--read-only-write-only-model-type",
            "all",
        ],
    )


def test_main_openapi_dot_notation_inheritance(output_dir: Path) -> None:
    """Test dot notation in schema names with inheritance."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "dot_notation_inheritance.yaml",
        output_path=output_dir,
        expected_directory=EXPECTED_OPENAPI_PATH / "dot_notation_inheritance",
        input_file_type="openapi",
    )


def test_main_openapi_dot_notation_deep_inheritance(output_dir: Path) -> None:
    """Test dot notation with deep inheritance from ancestor packages (issue #2039)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "dot_notation_deep_inheritance.yaml",
        output_path=output_dir,
        expected_directory=EXPECTED_OPENAPI_PATH / "dot_notation_deep_inheritance",
        input_file_type="openapi",
    )


def test_main_openapi_strict_types_field_constraints_pydantic_v2(output_file: Path) -> None:
    """Test strict types with field constraints for pydantic v2 (issue #1884)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "strict_types_field_constraints.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="strict_types_field_constraints_pydantic_v2.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--field-constraints",
            "--strict-types",
            "int",
            "float",
            "str",
        ],
    )


def test_main_openapi_strict_types_field_constraints_msgspec(output_file: Path) -> None:
    """Test strict types with field constraints for msgspec (issue #1884)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "strict_types_field_constraints.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="strict_types_field_constraints_msgspec.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--field-constraints",
            "--strict-types",
            "int",
            "float",
            "str",
        ],
    )


def test_main_openapi_circular_imports_stripe_like(output_dir: Path) -> None:
    """Test that circular imports between root and submodules are resolved with _internal.py."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "circular_imports_stripe_like.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "circular_imports_stripe_like",
            input_file_type="openapi",
        )


def test_main_openapi_circular_imports_acyclic(output_dir: Path) -> None:
    """Test that acyclic dependencies do not create _internal.py."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "circular_imports_acyclic.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "circular_imports_acyclic",
            input_file_type="openapi",
        )


def test_main_openapi_circular_imports_class_conflict(output_dir: Path) -> None:
    """Test that class name conflicts in merged _internal.py are resolved with sequential renaming."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "circular_imports_class_conflict.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "circular_imports_class_conflict",
            input_file_type="openapi",
        )


def test_main_openapi_circular_imports_with_inheritance(output_dir: Path) -> None:
    """Test that circular imports with base class inheritance are resolved."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "circular_imports_with_inheritance.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "circular_imports_with_inheritance",
            input_file_type="openapi",
        )


def test_main_openapi_circular_imports_small_cycle(output_dir: Path) -> None:
    """Test that small 2-module cycles also create _internal.py."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "circular_imports_small_cycle.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "circular_imports_small_cycle",
            input_file_type="openapi",
        )


def test_main_openapi_circular_imports_different_prefixes(output_dir: Path) -> None:
    """Test circular imports with different module prefixes (tests LCP computation)."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "circular_imports_different_prefixes.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "circular_imports_different_prefixes",
            input_file_type="openapi",
        )


def test_main_openapi_circular_imports_mixed_prefixes(output_dir: Path) -> None:
    """Test circular imports with mixed common/different prefixes (tests LCP break branch)."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "circular_imports_mixed_prefixes.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "circular_imports_mixed_prefixes",
            input_file_type="openapi",
        )


def test_warning_empty_schemas_with_paths(tmp_path: Path) -> None:
    """Test warning when components/schemas is empty but paths exist."""
    openapi_file = tmp_path / "openapi.yaml"
    openapi_file.write_text("""
openapi: 3.1.0
info:
  title: Test
  version: '1'
paths:
  /test:
    get:
      responses:
        200:
          description: OK
""")

    with pytest.warns(UserWarning, match=r"No schemas found.*--openapi-scopes paths"), contextlib.suppress(Exception):
        generate(openapi_file)


def test_main_allof_enum_ref(output_file: Path) -> None:
    """Test OpenAPI generation with allOf referencing enum from another schema."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_enum_ref.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
    )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse("2.0.0"),
    reason="Require Pydantic version 2.0.0 or later",
)
def test_main_openapi_module_class_name_collision_pydantic_v2(output_dir: Path) -> None:
    """Test Issue #1994: module and class name collision (e.g., A.A schema)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "module_class_name_collision" / "openapi.json",
        output_path=output_dir,
        expected_directory=EXPECTED_OPENAPI_PATH / "module_class_name_collision",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--openapi-scopes",
            "schemas",
            "--openapi-scopes",
            "paths",
        ],
    )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse("2.0.0"),
    reason="Require Pydantic version 2.0.0 or later",
)
def test_main_openapi_module_class_name_collision_deep_pydantic_v2(output_dir: Path) -> None:
    """Test Issue #1994: deep module collision (e.g., A.B.B schema)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "module_class_name_collision_deep" / "openapi.json",
        output_path=output_dir,
        expected_directory=EXPECTED_OPENAPI_PATH / "module_class_name_collision_deep",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--openapi-scopes",
            "schemas",
            "--openapi-scopes",
            "paths",
        ],
    )


def test_main_nested_package_enum_default(output_dir: Path) -> None:
    """Test enum default values use short names in same module with nested package paths."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "nested_package_enum_default.json",
            output_path=output_dir,
            expected_directory=EXPECTED_OPENAPI_PATH / "nested_package_enum_default",
            extra_args=[
                "--output-model-type",
                "dataclasses.dataclass",
                "--set-default-enum-member",
            ],
        )


def test_main_openapi_x_enum_names(output_file: Path) -> None:
    """Test OpenAPI generation with x-enumNames extension (NSwag/NJsonSchema style)."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "x_enum_names.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="x_enum_names.py",
    )


def test_main_enum_builtin_conflict(output_file: Path) -> None:
    """Test enum member names that conflict with str methods get underscore suffix."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "enum_builtin_conflict.yaml",
            output_path=output_file,
            input_file_type="openapi",
            assert_func=assert_file_content,
            expected_file="enum_builtin_conflict.py",
            extra_args=["--use-subclass-enum"],
        )


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        ("pydantic.BaseModel", "unique_items_default_set_pydantic.py"),
        ("pydantic_v2.BaseModel", "unique_items_default_set_pydantic_v2.py"),
        ("dataclasses.dataclass", "unique_items_default_set_dataclass.py"),
        ("msgspec.Struct", "unique_items_default_set_msgspec.py"),
    ],
)
def test_main_unique_items_default_set(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test --use-unique-items-as-set converts list defaults to set literals."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "unique_items_default_set.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model, "--use-unique-items-as-set"],
    )


def test_main_openapi_null_only_enum(output_file: Path) -> None:
    """Test OpenAPI generation with enum containing only null value."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "null_only_enum.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="null_only_enum.py",
    )


@pytest.mark.cli_doc(
    options=["--use-status-code-in-response-name"],
    input_schema="openapi/use_status_code_in_response_name.yaml",
    cli_args=["--use-status-code-in-response-name", "--openapi-scopes", "schemas", "paths"],
    golden_output="openapi/use_status_code_in_response_name.py",
)
def test_main_openapi_use_status_code_in_response_name(output_file: Path) -> None:
    """Include HTTP status code in response model names.

    The `--use-status-code-in-response-name` flag includes the HTTP status code
    in generated response model class names. Instead of generating ambiguous names
    like ResourceGetResponse, ResourceGetResponse1, ResourceGetResponse2, it generates
    clear names like ResourceGetResponse200, ResourceGetResponse400, ResourceGetResponseDefault.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "use_status_code_in_response_name.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="use_status_code_in_response_name.py",
        extra_args=["--use-status-code-in-response-name", "--openapi-scopes", "schemas", "paths"],
    )


@freeze_time(TIMESTAMP)
def test_main_openapi_request_bodies_scope(output_file: Path) -> None:
    """Test generating models from components/requestBodies using requestbodies scope."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "request_bodies_scope.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="request_bodies_scope.py",
        extra_args=["--openapi-scopes", "requestbodies", "--output-model-type", "pydantic_v2.BaseModel"],
    )


@freeze_time(TIMESTAMP)
def test_main_openapi_request_bodies_scope_with_ref(output_file: Path) -> None:
    """Test generating models from components/requestBodies with $ref at requestBody level."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "request_bodies_scope_with_ref.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="request_bodies_scope_with_ref.py",
        extra_args=["--openapi-scopes", "requestbodies", "--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_x_property_names(output_file: Path) -> None:
    """Test x-propertyNames extension for OpenAPI 3.0 is converted to propertyNames."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "x_property_names.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="x_property_names.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_main_openapi_x_property_names_non_dict(output_file: Path) -> None:
    """Test x-propertyNames with non-dict value is ignored."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "x_property_names_non_dict.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="x_property_names_non_dict.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


def test_query_parameters_with_model_config(output_file: Path) -> None:
    """Test that query parameter classes include model_config when config options are used.

    Regression test for https://github.com/koxudaxi/datamodel-code-generator/issues/2491
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "query_parameters_with_config.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file="query_parameters_with_config.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--openapi-scopes",
            "schemas",
            "paths",
            "parameters",
            "--use-annotated",
            "--extra-fields",
            "forbid",
            "--allow-population-by-field-name",
        ],
    )
