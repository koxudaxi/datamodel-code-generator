"""Parity tests for the process-local parsed source cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import InputFileType, _clear_parser_source_data_cache
from tests.conftest import assert_output
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, OPEN_API_DATA_PATH, run_main_with_args

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _input_file_type_option(input_file_type: InputFileType) -> str:
    match input_file_type:
        case InputFileType.JsonSchema:
            return "jsonschema"
        case InputFileType.OpenAPI:
            return "openapi"
        case _:  # pragma: no cover
            msg = f"Unsupported parsed source cache parity input type: {input_file_type}"
            raise AssertionError(msg)


def _build_generate_args(
    input_path: Path,
    output_path: Path,
    input_file_type: InputFileType,
    extra_args: Sequence[str] | None,
) -> list[str]:
    args = [
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--input-file-type",
        _input_file_type_option(input_file_type),
        "--disable-timestamp",
        "--formatters",
        "builtin",
    ]
    if extra := list(extra_args or ()):
        return [*args, *extra]
    return args


def _run_generate_with_parsed_source_cache(
    input_path: Path,
    output_path: Path,
    input_file_type: InputFileType,
    *,
    use_cache: bool,
    extra_args: Sequence[str] | None,
) -> None:
    _clear_parser_source_data_cache()
    run_main_with_args(
        _build_generate_args(input_path, output_path, input_file_type, extra_args),
        use_parsed_source_cache=use_cache,
        use_builtin_default_formatter=False,
    )


@pytest.mark.parametrize(
    ("input_path", "input_file_type", "extra_args"),
    [
        pytest.param(
            JSON_SCHEMA_DATA_PATH / "external_definitions_root.json",
            InputFileType.JsonSchema,
            None,
            id="jsonschema-external-definitions",
        ),
        pytest.param(
            JSON_SCHEMA_DATA_PATH / "all_of_ref" / "test.json",
            InputFileType.JsonSchema,
            ["--class-name", "Test"],
            id="jsonschema-relative-all-of",
        ),
        pytest.param(
            OPEN_API_DATA_PATH / "paths_external_ref" / "openapi.yaml",
            InputFileType.OpenAPI,
            ["--openapi-scopes", "paths"],
            id="openapi-paths-external-ref",
        ),
        pytest.param(
            OPEN_API_DATA_PATH / "external_ref_mapping" / "api.yaml",
            InputFileType.OpenAPI,
            None,
            id="openapi-external-ref-mapping",
        ),
    ],
)
def test_generate_output_matches_with_and_without_parsed_source_cache(
    input_path: Path,
    input_file_type: InputFileType,
    extra_args: Sequence[str] | None,
    tmp_path: Path,
) -> None:
    """Keep representative ref-heavy generation output stable across cache states."""
    cached_output = tmp_path / "cached.py"
    uncached_output = tmp_path / "uncached.py"

    _run_generate_with_parsed_source_cache(
        input_path,
        cached_output,
        input_file_type,
        use_cache=True,
        extra_args=extra_args,
    )
    _run_generate_with_parsed_source_cache(
        input_path,
        uncached_output,
        input_file_type,
        use_cache=False,
        extra_args=extra_args,
    )

    assert_output(uncached_output.read_text(encoding="utf-8"), cached_output)
