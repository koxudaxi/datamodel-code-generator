"""Tests for --input-model option."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING

import pydantic
import pytest

from datamodel_code_generator import __main__ as main_module
from datamodel_code_generator import arguments
from datamodel_code_generator.__main__ import Exit, main
from tests.conftest import assert_output, freeze_time

if TYPE_CHECKING:
    from collections.abc import Sequence

EXPECTED_INPUT_MODEL_PATH = Path(__file__).parent / "data" / "expected" / "main" / "input_model"
TIMESTAMP = "1985-10-26T01:21:00-07:00"

SKIP_PYDANTIC_V1 = pytest.mark.skipif(
    pydantic.VERSION < "2.0.0",
    reason="--input-model with Pydantic models requires Pydantic v2",
)


def _assert_exit_code(return_code: Exit, expected_exit: Exit, context: str) -> None:
    """Assert exit code matches expected value."""
    __tracebackhide__ = True
    if return_code != expected_exit:  # pragma: no cover
        pytest.fail(f"Expected exit code {expected_exit!r}, got {return_code!r}\n{context}")


def _assert_stderr_contains(captured_err: str, expected: str) -> None:
    """Assert stderr contains expected string."""
    __tracebackhide__ = True
    if expected not in captured_err:  # pragma: no cover
        pytest.fail(f"Expected stderr to contain: {expected!r}\n\nActual stderr:\n{captured_err}")


def _assert_file_exists(path: Path) -> None:
    """Assert file exists."""
    __tracebackhide__ = True
    if not path.exists():  # pragma: no cover
        pytest.fail(f"Expected file to exist: {path}")


def run_input_model_and_assert(
    *,
    input_model: str,
    output_path: Path,
    expected_file: Path,
    extra_args: Sequence[str] | None = None,
) -> None:
    """Run main with --input-model and assert results."""
    __tracebackhide__ = True
    args = ["--input-model", input_model, "--output", str(output_path)]
    if extra_args:
        args.extend(extra_args)

    with freeze_time(TIMESTAMP):
        return_code = main(args)
    _assert_exit_code(return_code, Exit.OK, f"--input-model {input_model}")
    _assert_file_exists(output_path)
    assert_output(output_path.read_text(encoding="utf-8"), expected_file)


def run_input_model_error_and_assert(
    *,
    input_model: str,
    extra_args: Sequence[str] | None = None,
    capsys: pytest.CaptureFixture[str],
    expected_stderr_contains: str,
) -> None:
    """Run main with --input-model expecting error and assert stderr."""
    __tracebackhide__ = True
    args = ["--input-model", input_model]
    if extra_args:
        args.extend(extra_args)

    return_code = main(args)
    _assert_exit_code(return_code, Exit.ERROR, f"--input-model {input_model}")
    captured = capsys.readouterr()
    _assert_stderr_contains(captured.err, expected_stderr_contains)


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the global namespace before each test."""
    new_namespace = Namespace(no_color=False)
    monkeypatch.setattr(arguments, "namespace", new_namespace)
    monkeypatch.setattr(main_module, "namespace", new_namespace)


@SKIP_PYDANTIC_V1
@pytest.mark.cli_doc(
    options=["--input-model"],
    option_description="""Import a Python type or dict schema from a module.

Use the format `module:Object` or `path/to/file.py:Object` to specify the type.""",
    cli_args=["--input-model", "mymodule:MyModel"],
    input_model="mymodule:MyModel",
    expected_stdout="",
)
def test_input_model_pydantic_basemodel(tmp_path: Path) -> None:
    """Test Pydantic BaseModel input converts to Pydantic BaseModel output (default)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_basemodel.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_to_typeddict(tmp_path: Path) -> None:
    """Test generating TypedDict from Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_to_typeddict.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_with_jsonschema_type(tmp_path: Path) -> None:
    """Test --input-model with explicit jsonschema input-file-type."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_with_jsonschema.py",
        extra_args=["--input-file-type", "jsonschema"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_non_jsonschema_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when Pydantic model used with non-jsonschema input-file-type."""
    run_input_model_error_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        extra_args=["--input-file-type", "openapi", "--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="--input-file-type must be 'jsonschema'",
    )


def test_input_model_dict_with_jsonschema(tmp_path: Path) -> None:
    """Test dict input with --input-file-type jsonschema."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dict_schemas:USER_SCHEMA",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "dict_with_jsonschema.py",
        extra_args=["--input-file-type", "jsonschema"],
    )


def test_input_model_dict_without_type_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that dict without --input-file-type raises error."""
    run_input_model_error_and_assert(
        input_model="tests.data.python.input_model.dict_schemas:USER_SCHEMA",
        extra_args=["--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="--input-file-type is required",
    )


def test_input_model_dict_openapi(tmp_path: Path) -> None:
    """Test dict input as OpenAPI spec."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dict_schemas:OPENAPI_SPEC",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "dict_openapi.py",
        extra_args=["--input-file-type", "openapi"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_std_dataclass(tmp_path: Path) -> None:
    """Test stdlib dataclass input converts to Pydantic BaseModel output (default)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dataclass_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "std_dataclass.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_dataclass(tmp_path: Path) -> None:
    """Test Pydantic dataclass input converts to Pydantic BaseModel output (default)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_dataclass_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_dataclass.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_typeddict(tmp_path: Path) -> None:
    """Test TypedDict input converts to Pydantic BaseModel output (default)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.typeddict_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "typeddict.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_dataclass_non_jsonschema_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when dataclass used with non-jsonschema input-file-type."""
    run_input_model_error_and_assert(
        input_model="tests.data.python.input_model.dataclass_models:User",
        extra_args=["--input-file-type", "openapi", "--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="--input-file-type must be 'jsonschema'",
    )


def test_input_model_invalid_format(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when colon is missing."""
    run_input_model_error_and_assert(
        input_model="pydantic.BaseModel",
        capsys=capsys,
        expected_stderr_contains="Invalid --input-model format",
    )


def test_input_model_invalid_module(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when module doesn't exist."""
    run_input_model_error_and_assert(
        input_model="nonexistent_module_12345:Model",
        capsys=capsys,
        expected_stderr_contains="Cannot find module",
    )


def test_input_model_invalid_attr(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when class doesn't exist in module."""
    run_input_model_error_and_assert(
        input_model="pydantic:NonexistentClass12345",
        capsys=capsys,
        expected_stderr_contains="has no attribute",
    )


def test_input_model_unsupported_type(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when object is not a supported type."""
    run_input_model_error_and_assert(
        input_model="pathlib:Path",
        capsys=capsys,
        expected_stderr_contains="is not a supported type",
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_v1_runtime_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error when Pydantic v1 runtime is detected."""
    import builtins

    from tests.data.python.input_model import pydantic_models

    original_hasattr = builtins.hasattr

    def mock_hasattr(obj: object, name: str) -> bool:
        if name == "model_json_schema" and obj is pydantic_models.User:
            return False
        return original_hasattr(obj, name)

    monkeypatch.setattr(builtins, "hasattr", mock_hasattr)

    run_input_model_error_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        capsys=capsys,
        expected_stderr_contains="requires Pydantic v2 runtime",
    )


@SKIP_PYDANTIC_V1
def test_input_model_dataclass_pydantic_import_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error when TypeAdapter import fails for dataclass."""
    import builtins

    original_import = builtins.__import__

    def mock_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "pydantic" and "TypeAdapter" in str(args):
            msg = "mocked import error"
            raise ImportError(msg)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    run_input_model_error_and_assert(
        input_model="tests.data.python.input_model.dataclass_models:User",
        capsys=capsys,
        expected_stderr_contains="requires Pydantic v2 runtime",
    )


@SKIP_PYDANTIC_V1
def test_input_model_mutual_exclusion_with_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --input-model cannot be used with --input."""
    run_input_model_error_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        extra_args=["--input", str(tmp_path / "schema.json")],
        capsys=capsys,
        expected_stderr_contains="--input-model cannot be used with --input or --url",
    )


@SKIP_PYDANTIC_V1
def test_input_model_mutual_exclusion_with_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --input-model cannot be used with --url."""
    run_input_model_error_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        extra_args=["--url", "https://example.com/schema.json"],
        capsys=capsys,
        expected_stderr_contains="--input-model cannot be used with --input or --url",
    )


@SKIP_PYDANTIC_V1
def test_input_model_mutual_exclusion_with_watch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --input-model cannot be used with --watch."""
    run_input_model_error_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        extra_args=["--watch", "--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="--watch cannot be used with --input-model",
    )


@SKIP_PYDANTIC_V1
def test_input_model_adds_cwd_to_sys_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that --input-model adds cwd to sys.path if not present."""
    cwd = str(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cwd not in sys.path

    original_sys_path = sys.path.copy()
    try:
        run_input_model_and_assert(
            input_model="tests.data.python.input_model.pydantic_models:User",
            output_path=tmp_path / "output.py",
            expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_basemodel.py",
        )
        assert cwd in sys.path
    finally:
        sys.path[:] = original_sys_path


@SKIP_PYDANTIC_V1
def test_input_model_path_format(tmp_path: Path) -> None:
    """Test --input-model with path format (path/to/file.py:Object)."""
    run_input_model_and_assert(
        input_model="tests/data/python/input_model/pydantic_models.py:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "path_format.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_path_format_filename_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test --input-model with filename.py format (no slash)."""
    from pathlib import Path as PathLib

    monkeypatch.chdir(PathLib("tests/data/python/input_model"))
    run_input_model_and_assert(
        input_model="pydantic_models.py:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "path_format_filename_only.py",
    )


def test_input_model_path_file_not_found(capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when file path doesn't exist."""
    run_input_model_error_and_assert(
        input_model="./nonexistent_file_12345.py:Model",
        capsys=capsys,
        expected_stderr_contains="File not found",
    )


def test_input_model_path_cannot_load(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error when spec_from_file_location returns None."""
    import importlib.util

    test_file = tmp_path / "test_model.py"
    test_file.write_text("class Model: pass")

    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *_a, **_kw: None)

    run_input_model_error_and_assert(
        input_model=f"{test_file}:Model",
        capsys=capsys,
        expected_stderr_contains="Cannot load module",
    )


def test_input_model_module_import_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error when module import fails."""
    import importlib
    import importlib.util

    class FakeSpec:
        name = "fake_module"

    def fake_find_spec(_name: str) -> FakeSpec:
        return FakeSpec()

    def fake_import_module(_name: str) -> None:
        msg = "fake import error"
        raise ImportError(msg)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    run_input_model_error_and_assert(
        input_model="some_module:Model",
        capsys=capsys,
        expected_stderr_contains="Cannot import module",
    )


# ============================================================================
# x-python-type preservation tests
# ============================================================================


@SKIP_PYDANTIC_V1
@pytest.mark.parametrize(
    "test_id",
    [
        "set_type",
        "frozenset_type",
        "mapping_type",
        "sequence_type",
        "nested_model_types",
    ],
)
def test_input_model_preserves_python_types(tmp_path: Path, test_id: str) -> None:
    """Test that Python collection types are preserved when converting Pydantic model."""
    del test_id
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "model_with_python_types.py",
    )


@SKIP_PYDANTIC_V1
@pytest.mark.parametrize(
    ("output_model_type", "expected_file"),
    [
        ("typing.TypedDict", "model_with_python_types_typeddict.py"),
        ("dataclasses.dataclass", "model_with_python_types_dataclass.py"),
    ],
)
def test_input_model_x_python_type_output_formats(tmp_path: Path, output_model_type: str, expected_file: str) -> None:
    """Test that x-python-type works with different output model types."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / expected_file,
        extra_args=["--output-model-type", output_model_type],
    )


@SKIP_PYDANTIC_V1
def test_input_model_dataclass_with_python_types(tmp_path: Path) -> None:
    """Test that Set/Mapping types are preserved from dataclass input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dataclass_models:DataclassWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "dataclass_with_python_types.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_recursive_model_types(tmp_path: Path) -> None:
    """Test that recursive models handle x-python-type correctly."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:RecursiveNode",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "recursive_model_types.py",
    )


@SKIP_PYDANTIC_V1
@pytest.mark.parametrize(
    "test_id",
    [
        "optional_set",
        "union_none_frozenset",
        "optional_mapping_union_syntax",
    ],
)
def test_input_model_optional_types(tmp_path: Path, test_id: str) -> None:
    """Test that optional/union Python types are preserved when converting Pydantic model."""
    del test_id
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "model_with_python_types.py",
    )


# ============================================================================
# Callable and unserializable type tests
# ============================================================================


@SKIP_PYDANTIC_V1
@pytest.mark.parametrize(
    "test_id",
    [
        "basic",
        "multi_param",
        "variadic",
        "no_param",
        "optional",
        "type_field",
        "nested",
    ],
)
def test_input_model_callable_types(tmp_path: Path, test_id: str) -> None:
    """Test that Callable and Type annotations are preserved when converting Pydantic model."""
    del test_id
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCallableTypes",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "model_with_callable_types.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_nested_model_with_callable(tmp_path: Path) -> None:
    """Test that nested models with Callable types in $defs are processed."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithNestedCallable",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "nested_model_with_callable.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_custom_class(tmp_path: Path) -> None:
    """Test that custom classes trigger handle_invalid_for_json_schema."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCustomClass",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "custom_class.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_union_callable(tmp_path: Path) -> None:
    """Test that Union[Callable, int] and raw Callable are preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithUnionCallable",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "union_callable.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_custom_generic_type_import(tmp_path: Path) -> None:
    """Test that custom generic types are properly imported with full module path."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCustomGeneric",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "custom_generic_type_import.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_default_put_dict_import(tmp_path: Path) -> None:
    """Test that DefaultPutDict generic type is properly imported from parser module."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithDefaultPutDict",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "default_put_dict_import.py",
    )


# ============================================================================
# --input-model-ref-strategy tests
# ============================================================================


@SKIP_PYDANTIC_V1
@pytest.mark.cli_doc(
    options=["--input-model-ref-strategy"],
    option_description="""Strategy for referenced types when using --input-model.

The `--input-model-ref-strategy` option determines whether to regenerate or import
referenced types. Use `regenerate-all` (default) to regenerate all types,
`reuse-foreign` to import types from different families (like enums when generating
dataclasses) while regenerating same-family types, or `reuse-all` to import all
referenced types directly.""",
    cli_args=["--input-model-ref-strategy", "reuse-foreign"],
    input_model="mymodule:MyModel",
    expected_stdout="",
)
def test_input_model_ref_strategy_regenerate_all_default(tmp_path: Path) -> None:
    """Test default regenerate-all strategy regenerates all types."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_regenerate_all.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_regenerate_all_explicit(tmp_path: Path) -> None:
    """Test explicit regenerate-all strategy regenerates all types."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_regenerate_all.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "regenerate-all",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign(tmp_path: Path) -> None:
    """Test reuse-foreign imports enum (always) and same-family types."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_no_regeneration(tmp_path: Path) -> None:
    """Test reuse-foreign imports only types compatible with output (enum always, same family)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_all(tmp_path: Path) -> None:
    """Test reuse-all strategy imports all referenced types."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_all.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_all_no_regeneration(tmp_path: Path) -> None:
    """Test reuse-all strategy does not regenerate any referenced classes."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_all.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_without_input_model(tmp_path: Path) -> None:
    """Test that --input-model-ref-strategy is ignored without --input-model."""
    schema_file = tmp_path / "schema.json"
    schema_file.write_text('{"type": "object", "properties": {"name": {"type": "string"}}}')

    args = [
        "--input",
        str(schema_file),
        "--output",
        str(tmp_path / "output.py"),
        "--input-model-ref-strategy",
        "reuse-all",
    ]
    return_code = main(args)
    assert return_code == Exit.OK


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_no_nested_types(tmp_path: Path) -> None:
    """Test reuse-all strategy with Pydantic model that has no nested types (no $defs)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_no_nested_types.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_dataclass_reuse_foreign(tmp_path: Path) -> None:
    """Test reuse-foreign strategy with dataclass input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dataclass_nested:Task",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_dataclass_reuse_foreign.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_typeddict_reuse_all(tmp_path: Path) -> None:
    """Test reuse-all strategy with TypedDict input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.typeddict_nested:Member",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_typeddict_reuse_all.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_typeddict_reuse_foreign(tmp_path: Path) -> None:
    """Test reuse-foreign strategy with TypedDict input imports enum, regenerates typeddict."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.typeddict_nested:Member",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_typeddict_reuse_foreign.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_same_family_typeddict(tmp_path: Path) -> None:
    """Test reuse-foreign imports TypedDict when output is TypedDict (same family)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithTypedDict",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign_same_family_typeddict.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_different_family_regenerate(tmp_path: Path) -> None:
    """Test reuse-foreign regenerates Pydantic model when output is TypedDict."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithPydantic",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign_different_family.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_same_family_dataclass(tmp_path: Path) -> None:
    """Test reuse-foreign imports dataclass when output is dataclass (same family)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithDataclass",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign_same_family_dataclass.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_mixed_types(tmp_path: Path) -> None:
    """Test reuse-foreign with mixed nested types (TypedDict, Pydantic, dataclass)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithMixed",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign_mixed_types.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_pydantic_output(tmp_path: Path) -> None:
    """Test reuse-foreign imports Pydantic when output is Pydantic (same family)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithPydantic",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign_pydantic_output.py",
        extra_args=[
            "--output-model-type",
            "pydantic.BaseModel",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_msgspec_output(tmp_path: Path) -> None:
    """Test reuse-foreign regenerates non-msgspec types when output is msgspec."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithPydantic",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign_msgspec_output.py",
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_config_class(tmp_path: Path) -> None:
    """Test that config classes like GenerateConfig are properly handled."""
    run_input_model_and_assert(
        input_model="datamodel_code_generator.config:GenerateConfig",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "config_class.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


# ============================================================================
# Inheritance support tests (single and multiple --input-model)
# ============================================================================


def run_multiple_input_models_and_assert(
    *,
    input_models: Sequence[str],
    output_path: Path,
    expected_file: Path,
    extra_args: Sequence[str] | None = None,
) -> None:
    """Run main with multiple --input-model and assert results."""
    __tracebackhide__ = True
    args: list[str] = []
    for input_model in input_models:
        args.extend(["--input-model", input_model])
    args.extend(["--output", str(output_path)])
    if extra_args:
        args.extend(extra_args)

    with freeze_time(TIMESTAMP):
        return_code = main(args)
    _assert_exit_code(return_code, Exit.OK, f"--input-model {input_models}")
    _assert_file_exists(output_path)
    assert_output(output_path.read_text(encoding="utf-8"), expected_file)


def run_multiple_input_models_error_and_assert(
    *,
    input_models: Sequence[str],
    extra_args: Sequence[str] | None = None,
    capsys: pytest.CaptureFixture[str],
    expected_stderr_contains: str,
) -> None:
    """Run main with multiple --input-model expecting error and assert stderr."""
    __tracebackhide__ = True
    args: list[str] = []
    for input_model in input_models:
        args.extend(["--input-model", input_model])
    if extra_args:
        args.extend(extra_args)

    return_code = main(args)
    _assert_exit_code(return_code, Exit.ERROR, f"--input-model {input_models}")
    captured = capsys.readouterr()
    _assert_stderr_contains(captured.err, expected_stderr_contains)


@SKIP_PYDANTIC_V1
def test_input_model_single_with_inheritance(tmp_path: Path) -> None:
    """Test single --input-model with inherited model generates inheritance chain."""
    with freeze_time(TIMESTAMP):
        return_code = main([
            "--input-model",
            "tests.data.python.input_model.inheritance_models:ChildA",
            "--output-model-type",
            "typing.TypedDict",
            "--output",
            str(tmp_path / "output.py"),
        ])
    assert return_code == Exit.OK
    assert_output(
        (tmp_path / "output.py").read_text(encoding="utf-8"),
        EXPECTED_INPUT_MODEL_PATH / "single_inheritance.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_single_multi_level_inheritance(tmp_path: Path) -> None:
    """Test single --input-model with multi-level inheritance."""
    with freeze_time(TIMESTAMP):
        return_code = main([
            "--input-model",
            "tests.data.python.input_model.inheritance_models:GrandChild",
            "--output-model-type",
            "typing.TypedDict",
            "--output",
            str(tmp_path / "output.py"),
        ])
    assert return_code == Exit.OK
    assert_output(
        (tmp_path / "output.py").read_text(encoding="utf-8"),
        EXPECTED_INPUT_MODEL_PATH / "multi_level_inheritance.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_single_no_inheritance(tmp_path: Path) -> None:
    """Test single --input-model with model that has no inheritance."""
    with freeze_time(TIMESTAMP):
        return_code = main([
            "--input-model",
            "tests.data.python.input_model.inheritance_models:NoInheritance",
            "--output-model-type",
            "typing.TypedDict",
            "--output",
            str(tmp_path / "output.py"),
        ])
    assert return_code == Exit.OK
    assert_output(
        (tmp_path / "output.py").read_text(encoding="utf-8"),
        EXPECTED_INPUT_MODEL_PATH / "no_inheritance.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_forked_inheritance(tmp_path: Path) -> None:
    """Test multiple --input-model with forked inheritance shares common parent."""
    with freeze_time(TIMESTAMP):
        return_code = main([
            "--input-model",
            "tests.data.python.input_model.inheritance_models:ChildA",
            "--input-model",
            "tests.data.python.input_model.inheritance_models:ChildB",
            "--output-model-type",
            "typing.TypedDict",
            "--output",
            str(tmp_path / "output.py"),
        ])
    assert return_code == Exit.OK
    assert_output(
        (tmp_path / "output.py").read_text(encoding="utf-8"),
        EXPECTED_INPUT_MODEL_PATH / "forked_inheritance.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_mixed_inheritance(tmp_path: Path) -> None:
    """Test multiple --input-model with different inheritance depths."""
    with freeze_time(TIMESTAMP):
        return_code = main([
            "--input-model",
            "tests.data.python.input_model.inheritance_models:ChildA",
            "--input-model",
            "tests.data.python.input_model.inheritance_models:GrandChild",
            "--output-model-type",
            "typing.TypedDict",
            "--output",
            str(tmp_path / "output.py"),
        ])
    assert return_code == Exit.OK
    assert_output(
        (tmp_path / "output.py").read_text(encoding="utf-8"),
        EXPECTED_INPUT_MODEL_PATH / "mixed_inheritance.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_with_pydantic_output(tmp_path: Path) -> None:
    """Test multiple --input-model works with Pydantic output."""
    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "multiple_with_pydantic_output.py",
        extra_args=["--output-model-type", "pydantic.BaseModel"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_with_dataclass_output(tmp_path: Path) -> None:
    """Test multiple --input-model works with dataclass output."""
    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "multiple_with_dataclass_output.py",
        extra_args=["--output-model-type", "dataclasses.dataclass"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_non_basemodel_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when multiple --input-model includes non-BaseModel."""
    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.dict_schemas:USER_SCHEMA",
        ],
        extra_args=["--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="Multiple --input-model only supports Pydantic v2 BaseModel",
    )


def test_input_model_multiple_pydantic_v1_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error when multiple --input-model used with Pydantic v1 model."""
    import builtins

    original_hasattr = builtins.hasattr

    def mock_hasattr(obj: object, name: str) -> bool:
        if name == "model_json_schema":
            return False
        return original_hasattr(obj, name)

    monkeypatch.setattr(builtins, "hasattr", mock_hasattr)

    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
        ],
        capsys=capsys,
        expected_stderr_contains="requires Pydantic v2 runtime",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_invalid_format_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when multiple --input-model has invalid format."""
    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "invalid_format_no_colon",
        ],
        capsys=capsys,
        expected_stderr_contains="Invalid --input-model format",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_file_not_found_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when multiple --input-model file doesn't exist."""
    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "./nonexistent_file.py:Model",
        ],
        capsys=capsys,
        expected_stderr_contains="File not found",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_module_not_found_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when multiple --input-model module doesn't exist."""
    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "nonexistent_module_xyz:Model",
        ],
        capsys=capsys,
        expected_stderr_contains="Cannot find module",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_attribute_not_found_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when multiple --input-model attribute doesn't exist."""
    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:NonexistentModel",
        ],
        capsys=capsys,
        expected_stderr_contains="has no attribute",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_non_jsonschema_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error when multiple --input-model used with non-jsonschema type."""
    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
        ],
        extra_args=["--input-file-type", "openapi", "--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="--input-file-type must be 'jsonschema'",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_same_module(tmp_path: Path) -> None:
    """Test multiple --input-model from same module reuses module load."""
    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
            "tests.data.python.input_model.inheritance_models:GrandChild",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "multiple_same_module.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_file_path_format(tmp_path: Path) -> None:
    """Test multiple --input-model with file path format."""
    run_multiple_input_models_and_assert(
        input_models=[
            "tests/data/python/input_model/inheritance_models.py:ChildA",
            "tests/data/python/input_model/inheritance_models.py:ChildB",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "forked_inheritance.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_with_ref_strategy(tmp_path: Path) -> None:
    """Test multiple --input-model works with --input-model-ref-strategy."""
    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "forked_inheritance.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_cannot_load_module_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error when spec_from_file_location returns None for multiple models."""
    import importlib.util

    test_file = tmp_path / "test_model.py"
    test_file.write_text("from pydantic import BaseModel\nclass Model(BaseModel): pass")

    original_spec_from_file_location = importlib.util.spec_from_file_location

    def mock_spec(*args: object, **kwargs: object) -> None:
        if hasattr(mock_spec, "called"):
            return None
        mock_spec.called = True  # type: ignore[attr-defined]
        return original_spec_from_file_location(*args, **kwargs)

    monkeypatch.setattr(importlib.util, "spec_from_file_location", mock_spec)

    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests/data/python/input_model/inheritance_models.py:ChildA",
            f"{test_file}:Model",
        ],
        extra_args=["--output", str(tmp_path / "output.py")],
        capsys=capsys,
        expected_stderr_contains="Cannot load module",
    )


@SKIP_PYDANTIC_V1
def test_input_model_multiple_import_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error when module import fails for multiple models."""
    import importlib
    import importlib.util

    class FakeSpec:
        name = "fake_module"

    original_find_spec = importlib.util.find_spec
    original_import_module = importlib.import_module
    call_count = 0

    def fake_find_spec(name: str, *args: object, **kwargs: object) -> FakeSpec | None:
        nonlocal call_count
        call_count += 1
        if "nonexistent_import_module" in name:
            return FakeSpec()
        return original_find_spec(name, *args, **kwargs)

    def fake_import_module(name: str, *args: object, **kwargs: object) -> object:
        if "nonexistent_import_module" in name:
            msg = "fake import error"
            raise ImportError(msg)
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    run_multiple_input_models_error_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "nonexistent_import_module:Model",
        ],
        capsys=capsys,
        expected_stderr_contains="Cannot import module",
    )


@SKIP_PYDANTIC_V1
def test_input_model_empty_child_no_properties(
    tmp_path: Path,
) -> None:
    """Test inheritance with empty child that adds no properties."""
    run_multiple_input_models_and_assert(
        input_models=["tests.data.python.input_model.inheritance_models:EmptyChild"],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "empty_child_no_properties.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_optional_only_child_no_required(
    tmp_path: Path,
) -> None:
    """Test inheritance with child that adds only optional fields."""
    run_multiple_input_models_and_assert(
        input_models=["tests.data.python.input_model.inheritance_models:OptionalOnlyChild"],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "optional_only_child_no_required.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_cwd_already_in_path(
    tmp_path: Path,
) -> None:
    """Test that cwd is not duplicated in sys.path when already present."""
    from pathlib import Path as _Path

    cwd = str(_Path.cwd())
    initial_count = sys.path.count(cwd)

    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "multiple_with_pydantic_output.py",
        extra_args=["--output-model-type", "pydantic.BaseModel"],
    )
    final_count = sys.path.count(cwd)
    assert final_count <= initial_count + 1


@SKIP_PYDANTIC_V1
def test_input_model_multiple_py_file_without_path_separator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test loading .py file without path separator (just filename.py)."""
    model_content = """
from pydantic import BaseModel

class TempModel(BaseModel):
    value: str
"""
    temp_file = tmp_path / "temp_model.py"
    temp_file.write_text(model_content)

    monkeypatch.chdir(tmp_path)

    output_path = tmp_path / "output.py"
    with freeze_time(TIMESTAMP):
        return_code = main([
            "--input-model",
            "tests.data.python.input_model.inheritance_models:ChildA",
            "--input-model",
            "temp_model.py:TempModel",
            "--output",
            str(output_path),
        ])
    assert return_code == Exit.OK
    content = output_path.read_text(encoding="utf-8")
    assert "class ChildA(Parent):" in content
    assert "class Parent(GrandParent):" in content
    assert "class GrandParent(BaseModel):" in content
    assert "class TempModel(BaseModel):" in content
    assert "value:" in content


@SKIP_PYDANTIC_V1
def test_input_model_config_string_coercion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that string input_model in config is coerced to list."""
    config_content = """\
[tool.datamodel-codegen]
input-model = "tests.data.python.input_model.inheritance_models:NoInheritance"
output-model-type = "typing.TypedDict"
"""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(config_content)
    monkeypatch.chdir(tmp_path)

    output_path = tmp_path / "output.py"
    with freeze_time(TIMESTAMP):
        return_code = main(["--output", str(output_path)])
    assert return_code == Exit.OK
    assert_output(
        output_path.read_text(encoding="utf-8"),
        EXPECTED_INPUT_MODEL_PATH / "no_inheritance.py",
    )


@SKIP_PYDANTIC_V1
def test_input_model_output_model_type_default() -> None:
    """Test that output_model_type defaults to PydanticBaseModel when not specified."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    schema = load_model_schema(
        ["tests.data.python.input_model.inheritance_models:NoInheritance"],
        InputFileType.JsonSchema,
        None,
        None,
    )
    assert schema.get("title") == "NoInheritance"
    assert "properties" in schema


# ============================================================================
# Unit tests for helper functions (coverage)
# ============================================================================


def test_simple_type_name_none_type() -> None:
    """Test _simple_type_name with NoneType."""
    from datamodel_code_generator.input_model import _simple_type_name

    result = _simple_type_name(type(None))
    assert result == "None"


def test_simple_type_name_generic_type() -> None:
    """Test _simple_type_name with generic type (has origin)."""
    from datamodel_code_generator.input_model import _simple_type_name

    result = _simple_type_name(list[str])
    assert result == "list[str]"


def test_full_type_name_string_annotation() -> None:
    """Test _full_type_name with string annotation."""
    from datamodel_code_generator.input_model import _full_type_name

    result = _full_type_name("SomeType")  # pyright: ignore[reportArgumentType]
    assert result == "SomeType"


def test_full_type_name_forward_ref() -> None:
    """Test _full_type_name with ForwardRef."""
    from typing import ForwardRef

    from datamodel_code_generator.input_model import _full_type_name

    ref = ForwardRef("MyClass")
    result = _full_type_name(ref)  # pyright: ignore[reportArgumentType]
    assert result == "MyClass"


def test_full_type_name_generic_no_args() -> None:
    """Test _full_type_name with generic type that has no args (covers line 365)."""
    from datamodel_code_generator.input_model import _full_type_name

    # Create a GenericAlias with origin=list but args=() - hits line 365
    # list.__class_getitem__(()) creates list[()] which has origin but no args
    generic_with_no_args = list.__class_getitem__(())
    result = _full_type_name(generic_with_no_args)  # pyright: ignore[reportArgumentType]
    assert result == "list"


def test_full_type_name_typing_special() -> None:
    """Test _full_type_name with typing module special forms."""
    from typing import Any

    from datamodel_code_generator.input_model import _full_type_name

    result = _full_type_name(Any)  # pyright: ignore[reportArgumentType]
    assert result == "Any"


def test_serialize_python_type_full_annotated() -> None:
    """Test _serialize_python_type_full with Annotated type."""
    from typing import Annotated

    from datamodel_code_generator.input_model import _serialize_python_type_full

    # Annotated with a custom type
    result = _serialize_python_type_full(Annotated[int, "some_metadata"])
    assert result == "int"


def test_full_type_name_builtin_type() -> None:
    """Test _full_type_name with builtin type (module='builtins')."""
    from datamodel_code_generator.input_model import _full_type_name

    # int is a builtin type with module='builtins'
    result = _full_type_name(int)
    assert result == "int"


def test_full_type_name_collections_abc_type() -> None:
    """Test _full_type_name with collections.abc type."""
    from collections.abc import Iterable

    from datamodel_code_generator.input_model import _full_type_name

    # Iterable is from collections.abc
    result = _full_type_name(Iterable)  # pyright: ignore[reportArgumentType]
    assert result == "Iterable"
