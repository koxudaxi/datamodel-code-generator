"""Tests for --input-model option."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

import pydantic
import pytest

from datamodel_code_generator import __main__ as main_module
from datamodel_code_generator import arguments
from datamodel_code_generator.__main__ import Exit, main

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

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


def _assert_output_contains(content: str, expected: str) -> None:
    """Assert output contains expected string."""
    __tracebackhide__ = True
    if expected not in content:  # pragma: no cover
        pytest.fail(f"Expected output to contain: {expected!r}\n\nActual output:\n{content}")


def _assert_file_exists(path: Path) -> None:
    """Assert file exists."""
    __tracebackhide__ = True
    if not path.exists():  # pragma: no cover
        pytest.fail(f"Expected file to exist: {path}")


def run_input_model_and_assert(
    *,
    input_model: str,
    output_path: Path,
    extra_args: Sequence[str] | None = None,
    expected_output_contains: Sequence[str] | None = None,
) -> None:
    """Run main with --input-model and assert results."""
    __tracebackhide__ = True
    args = ["--input-model", input_model, "--output", str(output_path)]
    if extra_args:
        args.extend(extra_args)

    return_code = main(args)
    _assert_exit_code(return_code, Exit.OK, f"--input-model {input_model}")
    _assert_file_exists(output_path)

    if expected_output_contains:
        content = output_path.read_text(encoding="utf-8")
        for expected in expected_output_contains:
            _assert_output_contains(content, expected)


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
    """Import a Python type or dict schema from a module (module:Object or path/to/file.py:Object)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
        expected_output_contains=["name", "age"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_to_typeddict(tmp_path: Path) -> None:
    """Test generating TypedDict from Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
        expected_output_contains=["TypedDict"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_with_jsonschema_type(tmp_path: Path) -> None:
    """Test --input-model with explicit jsonschema input-file-type."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
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
        extra_args=["--input-file-type", "openapi"],
        expected_output_contains=["User"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_std_dataclass(tmp_path: Path) -> None:
    """Test standard dataclass input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dataclass_models:User",
        output_path=tmp_path / "output.py",
        expected_output_contains=["name", "age"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_pydantic_dataclass(tmp_path: Path) -> None:
    """Test Pydantic dataclass input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_dataclass_models:User",
        output_path=tmp_path / "output.py",
        expected_output_contains=["name", "age"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_typeddict(tmp_path: Path) -> None:
    """Test TypedDict input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.typeddict_models:User",
        output_path=tmp_path / "output.py",
        expected_output_contains=["name", "age"],
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
    import sys

    cwd = str(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cwd not in sys.path

    original_sys_path = sys.path.copy()
    try:
        run_input_model_and_assert(
            input_model="tests.data.python.input_model.pydantic_models:User",
            output_path=tmp_path / "output.py",
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
        expected_output_contains=["name", "age"],
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
        expected_output_contains=["name", "age"],
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
def test_input_model_preserves_set_type(tmp_path: Path) -> None:
    """Test that Set[T] is preserved when converting Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["set[str]", "tags:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_preserves_frozenset_type(tmp_path: Path) -> None:
    """Test that FrozenSet[T] is preserved when converting Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["frozenset[int]", "frozen_tags:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_preserves_mapping_type(tmp_path: Path) -> None:
    """Test that Mapping[K, V] is preserved when converting Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["Mapping[str, int]", "metadata:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_preserves_sequence_type(tmp_path: Path) -> None:
    """Test that Sequence[T] is preserved when converting Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["Sequence[str]", "items:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_preserves_nested_model_types(tmp_path: Path) -> None:
    """Test that types in nested models are also preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["frozenset[str]", "values:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_x_python_type_to_typeddict(tmp_path: Path) -> None:
    """Test that x-python-type works when outputting to TypedDict."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
        expected_output_contains=["TypedDict", "set[str]", "Mapping[str, int]"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_x_python_type_to_dataclass(tmp_path: Path) -> None:
    """Test that x-python-type works when outputting to dataclass."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        extra_args=["--output-model-type", "dataclasses.dataclass"],
        expected_output_contains=["@dataclass", "set[str]", "Mapping[str, int]"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_dataclass_with_python_types(tmp_path: Path) -> None:
    """Test that Set/Mapping types are preserved from dataclass input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dataclass_models:DataclassWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["set[str]", "frozenset[int]", "Mapping[str, int]", "Sequence[str]"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_recursive_model_types(tmp_path: Path) -> None:
    """Test that recursive models handle x-python-type correctly."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:RecursiveNode",
        output_path=tmp_path / "output.py",
        expected_output_contains=["set[str]", "value:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_optional_set_type(tmp_path: Path) -> None:
    """Test that Optional[Set[str]] is preserved when converting Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["set[str] | None", "optional_set:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_optional_set_to_typeddict(tmp_path: Path) -> None:
    """Test that Optional[Set[str]] works when outputting to TypedDict."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
        expected_output_contains=["TypedDict", "set[str] | None", "optional_set:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_union_none_frozenset(tmp_path: Path) -> None:
    """Test that Union[None, FrozenSet[str]] is preserved (container not first arg)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["frozenset[str] | None", "nullable_frozenset:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_optional_mapping_union_syntax(tmp_path: Path) -> None:
    """Test that Mapping[str, str] | None using | syntax is preserved correctly.

    In Python 3.10-3.13, get_origin(X | Y) returns types.UnionType.
    This test verifies that types.UnionType is handled correctly in those versions.
    """
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["Mapping[str, str] | None", "optional_mapping:"],
    )


# ============================================================================
# Callable and unserializable type tests
# ============================================================================


@SKIP_PYDANTIC_V1
def test_input_model_callable_basic(tmp_path: Path) -> None:
    """Test that Callable[[str], str] is preserved when converting Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCallableTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["Callable[[str], str]", "callback:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_callable_multi_param(tmp_path: Path) -> None:
    """Test that Callable[[int, int], bool] is preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCallableTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["Callable[[int, int], bool]", "multi_param_callback:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_callable_variadic(tmp_path: Path) -> None:
    """Test that Callable[..., Any] is preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCallableTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["Callable[..., Any]", "variadic_callback:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_callable_no_param(tmp_path: Path) -> None:
    """Test that Callable[[], None] is preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCallableTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["Callable[[], None]", "no_param_callback:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_callable_optional(tmp_path: Path) -> None:
    """Test that Callable[[str], str] | None is preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCallableTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["Callable[[str], str] | None", "optional_callback:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_type_field(tmp_path: Path) -> None:
    """Test that Type[BaseModel] is preserved with proper import."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCallableTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=[
            "Type[BaseModel]",
            "type_field:",
            "from pydantic.main import BaseModel",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_nested_callable(tmp_path: Path) -> None:
    """Test that list[Callable[[str], int]] is preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCallableTypes",
        output_path=tmp_path / "output.py",
        expected_output_contains=["list[Callable[[str], int]]", "nested_callable:"],
    )


@SKIP_PYDANTIC_V1
def test_input_model_nested_model_with_callable(tmp_path: Path) -> None:
    """Test that nested models with Callable types in $defs are processed."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithNestedCallable",
        output_path=tmp_path / "output.py",
        expected_output_contains=[
            "Callable[[str], int]",
            "Callable[[int], str]",
            "NestedCallableModel",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_custom_class(tmp_path: Path) -> None:
    """Test that custom classes trigger handle_invalid_for_json_schema."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCustomClass",
        output_path=tmp_path / "output.py",
        expected_output_contains=[
            "CustomClass",
            "custom_obj:",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_union_callable(tmp_path: Path) -> None:
    """Test that Union[Callable, int] and raw Callable are preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithUnionCallable",
        output_path=tmp_path / "output.py",
        expected_output_contains=[
            "Callable[[str], str] | int",
            "union_callback:",
            "Callable",
            "raw_callable:",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_custom_generic_type_import(tmp_path: Path) -> None:
    """Test that custom generic types are properly imported with full module path."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCustomGeneric",
        output_path=tmp_path / "output.py",
        expected_output_contains=[
            "from tests.data.python.input_model.pydantic_models import CustomGenericDict",
            "CustomGenericDict[str, int]",
            "CustomGenericDict[str, str] | None",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_default_put_dict_import(tmp_path: Path) -> None:
    """Test that DefaultPutDict generic type is properly imported from parser module."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithDefaultPutDict",
        output_path=tmp_path / "output.py",
        expected_output_contains=[
            "from datamodel_code_generator.parser import DefaultPutDict",
            "DefaultPutDict[str, str]",
            "DefaultPutDict[str, int] | None",
        ],
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
        extra_args=["--output-model-type", "typing.TypedDict"],
        expected_output_contains=[
            "Status: TypeAlias =",
            "class Address",
            "class User",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_regenerate_all_explicit(tmp_path: Path) -> None:
    """Test explicit regenerate-all strategy regenerates all types."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "regenerate-all",
        ],
        expected_output_contains=[
            "Status: TypeAlias =",
            "class Address",
            "class User",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign(tmp_path: Path) -> None:
    """Test reuse-foreign imports enum (always) and same-family types."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.nested_models import Status",
            "class Metadata",
            "class Address",
            "class User",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_no_regeneration(tmp_path: Path) -> None:
    """Test reuse-foreign imports only types compatible with output (enum always, same family)."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.nested_models import Status",
            "class Metadata",
            "class Address",
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    assert "Status: TypeAlias" not in content


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_all(tmp_path: Path) -> None:
    """Test reuse-all strategy imports all referenced types."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=tmp_path / "output.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.nested_models import",
            "Address",
            "Metadata",
            "Status",
            "class User",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_all_no_regeneration(tmp_path: Path) -> None:
    """Test reuse-all strategy does not regenerate any referenced classes."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.nested_models:User",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
        expected_output_contains=[
            "class User",
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    assert "Status: TypeAlias" not in content
    assert "class Metadata" not in content
    assert "class Address" not in content


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
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
        expected_output_contains=[
            "class User",
            "name: str",
            "age: int",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_dataclass_reuse_foreign(tmp_path: Path) -> None:
    """Test reuse-foreign strategy with dataclass input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dataclass_nested:Task",
        output_path=tmp_path / "output.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.dataclass_nested import Priority",
            "class Task",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_typeddict_reuse_all(tmp_path: Path) -> None:
    """Test reuse-all strategy with TypedDict input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.typeddict_nested:Member",
        output_path=tmp_path / "output.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.typeddict_nested import",
            "Role",
            "Profile",
            "class Member",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_typeddict_reuse_foreign(tmp_path: Path) -> None:
    """Test reuse-foreign strategy with TypedDict input imports enum, regenerates typeddict."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.typeddict_nested:Member",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.typeddict_nested import Role",
            "class Member",
            "class Profile",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_same_family_typeddict(tmp_path: Path) -> None:
    """Test reuse-foreign imports TypedDict when output is TypedDict (same family)."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithTypedDict",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.mixed_nested import",
            "Category",
            "NestedTypedDict",
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    assert "class NestedTypedDict" not in content


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_different_family_regenerate(tmp_path: Path) -> None:
    """Test reuse-foreign regenerates Pydantic model when output is TypedDict."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithPydantic",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.mixed_nested import Category",
            "class NestedPydantic",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_same_family_dataclass(tmp_path: Path) -> None:
    """Test reuse-foreign imports dataclass when output is dataclass (same family)."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithDataclass",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.mixed_nested import",
            "Category",
            "NestedDataclass",
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    assert "class NestedDataclass" not in content


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_mixed_types(tmp_path: Path) -> None:
    """Test reuse-foreign with mixed nested types (TypedDict, Pydantic, dataclass)."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithMixed",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.mixed_nested import",
            "Category",
            "NestedTypedDict",
            "class NestedPydantic",
            "class NestedDataclass",
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    assert "class NestedTypedDict" not in content


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_pydantic_output(tmp_path: Path) -> None:
    """Test reuse-foreign imports Pydantic when output is Pydantic (same family)."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithPydantic",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "pydantic.BaseModel",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.mixed_nested import",
            "Category",
            "NestedPydantic",
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    assert "class NestedPydantic" not in content


@SKIP_PYDANTIC_V1
def test_input_model_ref_strategy_reuse_foreign_msgspec_output(tmp_path: Path) -> None:
    """Test reuse-foreign regenerates non-msgspec types when output is msgspec."""
    output_path = tmp_path / "output.py"
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithPydantic",
        output_path=output_path,
        extra_args=[
            "--output-model-type",
            "msgspec.Struct",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
        expected_output_contains=[
            "from tests.data.python.input_model.mixed_nested import Category",
            "class NestedPydantic",
            "class ModelWithPydantic",
        ],
    )


@SKIP_PYDANTIC_V1
def test_input_model_config_class(tmp_path: Path) -> None:
    """Test that config classes like GenerateConfig are properly handled."""
    run_input_model_and_assert(
        input_model="datamodel_code_generator.config:GenerateConfig",
        output_path=tmp_path / "output.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
        expected_output_contains=["TypedDict", "Callable[[str], str]"],
    )
