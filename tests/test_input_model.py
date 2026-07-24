"""Tests for --input-model option."""

from __future__ import annotations

import sys
import types
from argparse import Namespace
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Lock, Thread
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import __main__ as main_module
from datamodel_code_generator import arguments
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_output, freeze_time
from tests.main.conftest import run_main_with_args

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

EXPECTED_INPUT_MODEL_PATH = Path(__file__).parent / "data" / "expected" / "main" / "input_model"
TIMESTAMP = "1985-10-26T01:21:00-07:00"
_MISSING_SYS_MODULE = object()


def _assert_sys_module_missing(module_name: str) -> None:
    """Assert sys.modules does not contain module_name."""
    __tracebackhide__ = True
    if module_name in sys.modules:  # pragma: no cover
        pytest.fail(f"Expected sys.modules to not contain {module_name!r}")


def _assert_sys_module_is(module_name: str, expected_module: types.ModuleType) -> None:
    """Assert sys.modules contains the expected module object."""
    __tracebackhide__ = True
    actual_module = sys.modules.get(module_name)
    if actual_module is not expected_module:  # pragma: no cover
        pytest.fail(f"Expected sys.modules[{module_name!r}] to be restored")


def _assert_sys_modules_with_prefix(module_prefix: str, expected_modules: set[str]) -> None:
    """Assert sys.modules keys with module_prefix match the expected set."""
    __tracebackhide__ = True
    actual_modules = {module_name for module_name in sys.modules if module_name.startswith(module_prefix)}
    if actual_modules != expected_modules:  # pragma: no cover
        pytest.fail(f"Expected sys.modules keys with prefix {module_prefix!r} to be restored")


@contextmanager
def _without_sys_module(module_name: str) -> Iterator[None]:
    """Temporarily remove a sys.modules entry and restore the previous state."""
    previous_module = sys.modules.pop(module_name, _MISSING_SYS_MODULE)
    try:
        yield
    finally:
        if previous_module is _MISSING_SYS_MODULE:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module


def _input_model_args(
    input_models: str | Sequence[str],
    *,
    output_path: Path | None = None,
    extra_args: Sequence[str] | None = None,
) -> list[str]:
    args: list[str] = []
    match input_models:
        case str():
            args.extend(["--input-model", input_models])
        case _:
            for input_model in input_models:
                args.extend(["--input-model", input_model])
    if output_path is not None:
        args.extend(["--output", str(output_path)])
    if not (extra := list(extra_args or ())):
        return args
    args.extend(extra)
    return args


def run_input_model_and_assert(
    *,
    input_model: str,
    output_path: Path,
    expected_file: Path,
    extra_args: Sequence[str] | None = None,
) -> None:
    """Run main with --input-model and assert results."""
    __tracebackhide__ = True
    with freeze_time(TIMESTAMP):
        run_main_with_args(
            _input_model_args(input_model, output_path=output_path, extra_args=extra_args),
            use_parsed_source_cache=False,
            use_builtin_default_formatter=False,
            isolate_model_template_cache=True,
        )
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
    run_main_with_args(
        _input_model_args(input_model, extra_args=extra_args),
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=expected_stderr_contains,
        use_parsed_source_cache=False,
        use_builtin_default_formatter=False,
        isolate_model_template_cache=True,
    )


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the global namespace before each test."""
    new_namespace = Namespace(no_color=False)
    monkeypatch.setattr(arguments, "namespace", new_namespace)
    monkeypatch.setattr(main_module, "namespace", new_namespace)


@pytest.mark.cli_doc(
    options=["--input-model"],
    option_description="""Import a Python type or dict schema from a module or Python file.

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


def test_input_model_pydantic_to_typeddict(tmp_path: Path) -> None:
    """Test generating TypedDict from Pydantic model."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_to_typeddict.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


def test_input_model_pydantic_with_jsonschema_type(tmp_path: Path) -> None:
    """Test --input-model with explicit jsonschema input-file-type."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_with_jsonschema.py",
        extra_args=["--input-file-type", "jsonschema"],
    )


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


def test_input_model_std_dataclass(tmp_path: Path) -> None:
    """Test stdlib dataclass input converts to Pydantic BaseModel output (default)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dataclass_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "std_dataclass.py",
    )


def test_input_model_pydantic_dataclass(tmp_path: Path) -> None:
    """Test Pydantic dataclass input converts to Pydantic BaseModel output (default)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_dataclass_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_dataclass.py",
    )


def test_input_model_typeddict(tmp_path: Path) -> None:
    """Test TypedDict input converts to Pydantic BaseModel output (default)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.typeddict_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "typeddict.py",
    )


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


def test_input_model_adds_cwd_to_sys_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that --input-model temporarily adds cwd to sys.path."""
    input_model_dir = Path("tests/data/python/input_model").resolve()
    cwd = str(input_model_dir)
    monkeypatch.chdir(input_model_dir)
    assert cwd not in sys.path

    run_input_model_and_assert(
        input_model="pydantic_models:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "pydantic_basemodel.py",
    )

    assert cwd not in sys.path


def test_input_model_restores_cwd_in_sys_path_on_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test an input-model error restores a temporarily added cwd."""
    input_model_dir = Path("tests/data/python/input_model").resolve()
    cwd = str(input_model_dir)
    monkeypatch.chdir(input_model_dir)
    assert cwd not in sys.path

    run_input_model_error_and_assert(
        input_model="pydantic_models:Missing",
        capsys=capsys,
        expected_stderr_contains="has no attribute",
    )

    assert cwd not in sys.path


def test_input_model_path_format(tmp_path: Path) -> None:
    """Test --input-model with path format (path/to/file.py:Object)."""
    run_input_model_and_assert(
        input_model="tests/data/python/input_model/pydantic_models.py:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "path_format.py",
    )


def test_input_model_path_format_restores_sys_modules(tmp_path: Path) -> None:
    """Test path-based --input-model does not keep temporary modules alive."""
    model_path = tmp_path / "temporary_input_model.py"
    model_path.write_text(
        "from pydantic import BaseModel\n\nclass User(BaseModel):\n    name: str\n    age: int\n",
        encoding="utf-8",
    )
    module_name = model_path.stem

    with _without_sys_module(module_name):
        run_input_model_and_assert(
            input_model=f"{model_path}:User",
            output_path=tmp_path / "output.py",
            expected_file=EXPECTED_INPUT_MODEL_PATH / "path_format.py",
        )

        _assert_sys_module_missing(module_name)


def test_input_model_path_format_restores_existing_sys_modules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test path-based --input-model restores a pre-existing sys.modules entry."""
    model_path = tmp_path / "existing_input_model.py"
    model_path.write_text(
        "from pydantic import BaseModel\n\nclass User(BaseModel):\n    name: str\n    age: int\n",
        encoding="utf-8",
    )
    module_name = model_path.stem
    existing_module = types.ModuleType(module_name)
    monkeypatch.setitem(sys.modules, module_name, existing_module)

    run_input_model_and_assert(
        input_model=f"{model_path}:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "path_format.py",
    )

    _assert_sys_module_is(module_name, existing_module)


def test_without_sys_module_restores_existing_module() -> None:
    """Test _without_sys_module restores the previous sys.modules entry."""
    module_name = "temporary_existing_input_model"
    existing_module = types.ModuleType(module_name)

    with _without_sys_module(module_name):
        sys.modules[module_name] = existing_module
        with _without_sys_module(module_name):
            _assert_sys_module_missing(module_name)

        _assert_sys_module_is(module_name, existing_module)

    _assert_sys_module_missing(module_name)


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


def test_path_module_name_keeps_same_file_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test path module naming keeps the stem when the loaded module is the same file."""
    from datamodel_code_generator.input_model import _get_path_module_name

    model_path = (tmp_path / "same_file_model.py").resolve()
    model_path.write_text("class Model: pass\n", encoding="utf-8")
    module_name = model_path.stem
    existing_module = types.ModuleType(module_name)
    existing_module.__file__ = str(model_path)
    monkeypatch.setitem(sys.modules, module_name, existing_module)

    assert _get_path_module_name(model_path) == module_name


def test_path_module_name_falls_back_when_existing_file_cannot_resolve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test path module naming keeps the stem when an existing module file cannot resolve."""
    from datamodel_code_generator.input_model import _get_path_module_name

    model_path = (tmp_path / "unresolvable_existing_model.py").resolve()
    model_path.write_text("class Model: pass\n", encoding="utf-8")
    module_name = model_path.stem
    existing_module = types.ModuleType(module_name)
    existing_module.__file__ = "__unresolvable_existing_model__"
    monkeypatch.setitem(sys.modules, module_name, existing_module)

    def fake_resolve(_path: Path, *_args: object, **_kwargs: object) -> Path:
        msg = "cannot resolve"
        raise OSError(msg)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    assert _get_path_module_name(model_path) == module_name


def test_load_module_from_path_restores_sys_modules_on_exec_error(tmp_path: Path) -> None:
    """Test path module loading restores sys.modules when module execution fails."""
    from datamodel_code_generator.input_model import _load_module_from_path

    model_path = (tmp_path / "failing_input_model.py").resolve()
    model_path.write_text("raise RuntimeError('module failed')\n", encoding="utf-8")
    module_name = model_path.stem

    with (
        _without_sys_module(module_name),
        pytest.raises(RuntimeError, match="module failed"),
    ):
        _load_module_from_path(model_path, str(model_path))

    _assert_sys_module_missing(module_name)


def test_load_model_schema_serializes_path_and_dotted_module_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test a dotted import cannot observe a concurrent path module."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    model_path = (tmp_path / "concurrent_input_model.py").resolve()
    control_name = "_input_model_concurrency_control"
    model_path.write_text(
        "from pydantic import BaseModel\n"
        f"import {control_name}\n\n"
        "class Model(BaseModel):\n"
        "    value: str\n\n"
        "    @classmethod\n"
        "    def model_json_schema(cls, *args, **kwargs):\n"
        f"        {control_name}.enter()\n"
        "        return super().model_json_schema(*args, **kwargs)\n",
        encoding="utf-8",
    )
    module_name = model_path.stem
    monkeypatch.syspath_prepend(str(tmp_path))
    started = [Event(), Event()]
    entered = [Event(), Event()]
    release = [Event(), Event()]
    call_lock = Lock()
    call_count = 0
    schemas: list[dict[str, object]] = []

    def enter() -> None:
        nonlocal call_count
        with call_lock:
            index = call_count
            call_count += 1
        entered[index].set()
        release[index].wait(timeout=5)

    control_module = types.ModuleType(control_name)
    control_module.enter = enter  # ty: ignore[unresolved-attribute]

    def load_schema(index: int) -> None:
        started[index].set()
        input_model = f"{module_name}:Model"
        match index:
            case 0:
                input_model = f"{model_path}:Model"
            case _:
                pass
        schemas.append(load_model_schema([input_model], InputFileType.Auto))

    threads = [Thread(target=load_schema, args=(index,)) for index in range(2)]
    with _without_sys_module(module_name), _without_sys_module(control_name):
        sys.modules[control_name] = control_module
        threads[0].start()
        assert entered[0].wait(timeout=5)
        threads[1].start()
        assert started[1].wait(timeout=5)
        try:
            assert not entered[1].wait(timeout=0.1)
            release[0].set()
            assert entered[1].wait(timeout=5)
        finally:
            for event in release:
                event.set()
            for thread in threads:
                thread.join(timeout=5)

        assert all(not thread.is_alive() for thread in threads)
        assert len(schemas) == 2
        assert schemas[0] == schemas[1]

    _assert_sys_module_missing(module_name)


def test_load_model_schema_keeps_unrelated_dotted_modules_concurrent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test unrelated dotted modules retain the concurrent fast path."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    control_name = "_input_model_dotted_concurrency_control"
    module_names = ("first_dotted_input_model", "second_dotted_input_model")
    for module_name in module_names:
        (tmp_path / f"{module_name}.py").write_text(
            "from pydantic import BaseModel\n"
            f"import {control_name}\n\n"
            "class Model(BaseModel):\n"
            "    value: str\n\n"
            "    @classmethod\n"
            "    def model_json_schema(cls, *args, **kwargs):\n"
            f"        {control_name}.enter({module_name!r})\n"
            "        return super().model_json_schema(*args, **kwargs)\n",
            encoding="utf-8",
        )
    monkeypatch.syspath_prepend(str(tmp_path))
    entered = {module_name: Event() for module_name in module_names}
    release = {module_name: Event() for module_name in module_names}
    schemas: list[dict[str, object]] = []

    def enter(module_name: str) -> None:
        entered[module_name].set()
        release[module_name].wait(timeout=5)

    control_module = types.ModuleType(control_name)
    control_module.enter = enter  # ty: ignore[unresolved-attribute]

    def load_schema(module_name: str) -> None:
        schemas.append(load_model_schema([f"{module_name}:Model"], InputFileType.Auto))

    threads = [Thread(target=load_schema, args=(module_name,)) for module_name in module_names]
    with (
        _without_sys_module(module_names[0]),
        _without_sys_module(module_names[1]),
        _without_sys_module(control_name),
    ):
        sys.modules[control_name] = control_module
        threads[0].start()
        assert entered[module_names[0]].wait(timeout=5)
        threads[1].start()
        try:
            assert entered[module_names[1]].wait(timeout=5)
        finally:
            for event in release.values():
                event.set()
            for thread in threads:
                thread.join(timeout=5)

        assert all(not thread.is_alive() for thread in threads)
        assert len(schemas) == 2
        assert schemas[0] == schemas[1]


def test_load_model_schema_imports_dotted_module_ending_in_py(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep pkg.py names as dotted imports when no matching file exists."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    package = tmp_path / "dotted_suffix"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "py.py").write_text(
        "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    value: str\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    schema = load_model_schema(["dotted_suffix.py:Model"], InputFileType.Auto)

    assert schema["title"] == "Model"


def test_load_model_schema_isolates_shadowed_dotted_modules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load a cwd-local dotted model instead of a previous request's module."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_shadowed_input_model"
    request_paths = [tmp_path / "first", tmp_path / "second"]
    for request_path, field_name in zip(request_paths, ("first_value", "second_value"), strict=True):
        request_path.mkdir()
        (request_path / f"{module_name}.py").write_text(
            f"from pydantic import BaseModel\n\nclass Model(BaseModel):\n    {field_name}: str\n",
            encoding="utf-8",
        )

    with _without_sys_module(module_name):
        monkeypatch.chdir(request_paths[0])
        first_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        monkeypatch.chdir(request_paths[1])
        second_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

    assert list(first_schema["properties"]) == ["first_value"]  # ty: ignore[invalid-argument-type]
    assert list(second_schema["properties"]) == ["second_value"]  # ty: ignore[invalid-argument-type]


def test_load_model_schema_isolates_shadowed_dotted_packages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Restore dotted package parents and siblings after a cwd-local request."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    package_name = "_shadowed_input_package"
    request_paths = [tmp_path / "first", tmp_path / "second"]
    for request_path, field_type in zip(request_paths, ("str", "int"), strict=True):
        package = request_path / package_name
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "fields.py").write_text(f"FieldType = {field_type}\n", encoding="utf-8")
        (package / "models.py").write_text(
            "from pydantic import BaseModel\n"
            "from .fields import FieldType\n\n"
            "class Model(BaseModel):\n"
            "    value: FieldType\n",
            encoding="utf-8",
        )

    module_name = f"{package_name}.models"
    with (
        _without_sys_module(package_name),
        _without_sys_module(f"{package_name}.fields"),
        _without_sys_module(module_name),
    ):
        monkeypatch.chdir(request_paths[0])
        first_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        monkeypatch.chdir(request_paths[1])
        second_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

    assert first_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
    assert second_schema["properties"]["value"]["type"] == "integer"  # ty: ignore[call-non-callable]
    _assert_sys_modules_with_prefix(package_name, set())


def test_load_model_schema_restores_explicit_path_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not reuse a cwd-local dependency from an earlier path request."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    model_name = "_request_path_model"
    dependency_name = "_request_path_dependency"
    request_paths = [tmp_path / "first", tmp_path / "second"]
    for request_path, field_type in zip(request_paths, ("str", "int"), strict=True):
        request_path.mkdir()
        (request_path / f"{dependency_name}.py").write_text(f"FieldType = {field_type}\n", encoding="utf-8")
        (request_path / f"{model_name}.py").write_text(
            "from pydantic import BaseModel\n"
            f"from {dependency_name} import FieldType\n\n"
            "class Model(BaseModel):\n"
            "    value: FieldType\n",
            encoding="utf-8",
        )

    property_types: list[str] = []
    with _without_sys_module(model_name), _without_sys_module(dependency_name):
        for request_path in request_paths:
            monkeypatch.chdir(request_path)
            schema = load_model_schema(
                [f"{(request_path / f'{model_name}.py').resolve()}:Model"],
                InputFileType.Auto,
            )
            property_types.append(schema["properties"]["value"]["type"])  # ty: ignore[call-non-callable]
            _assert_sys_module_missing(model_name)
            _assert_sys_module_missing(dependency_name)

    assert property_types == ["string", "integer"]


def test_load_model_schema_keeps_nonlocal_path_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep standard import caching for dependencies outside the path request directory."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    model_name = "_nonlocal_dependency_model"
    dependency_name = "_nonlocal_path_dependency"
    model_dir = tmp_path / "model"
    dependency_dir = tmp_path / "dependency"
    model_dir.mkdir()
    dependency_dir.mkdir()
    (dependency_dir / f"{dependency_name}.py").write_text("FieldType = str\n", encoding="utf-8")
    model_path = model_dir / f"{model_name}.py"
    model_path.write_text(
        "from pydantic import BaseModel\n"
        f"from {dependency_name} import FieldType\n\n"
        "class Model(BaseModel):\n"
        "    value: FieldType\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(model_dir)
    monkeypatch.syspath_prepend(str(dependency_dir))

    with _without_sys_module(model_name), _without_sys_module(dependency_name):
        schema = load_model_schema([f"{model_path}:Model"], InputFileType.Auto)
        assert schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        _assert_sys_module_missing(model_name)
        if (dependency_module := sys.modules.get(dependency_name)) is None:  # pragma: no cover
            pytest.fail("Expected the nonlocal dependency to retain standard import caching")
        _assert_sys_module_is(dependency_name, dependency_module)


def test_load_model_schema_restores_initial_cwd_local_dotted_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remove a cwd-local dotted module even when no cached module preceded it."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_initial_local_input_model"
    (tmp_path / f"{module_name}.py").write_text(
        "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    value: str\n",
        encoding="utf-8",
    )

    with _without_sys_module(module_name):
        monkeypatch.chdir(tmp_path)
        schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        assert schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        _assert_sys_module_missing(module_name)


def test_load_model_schema_restores_cached_dotted_dynamic_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Track a cwd-local dependency imported by a cached model's schema hook."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_cached_dynamic_input_model"
    dependency_name = "_cached_dynamic_input_dependency"
    unrelated_name = "_cached_dynamic_input_unrelated"
    (tmp_path / f"{dependency_name}.py").write_text("VALUE = 'loaded'\n", encoding="utf-8")
    (tmp_path / f"{unrelated_name}.py").write_text("VALUE = 'preserved'\n", encoding="utf-8")
    (tmp_path / f"{module_name}.py").write_text(
        "from pydantic import BaseModel\n\n"
        "_calls = 0\n\n"
        "class Model(BaseModel):\n"
        "    value: str\n\n"
        "    @classmethod\n"
        "    def model_json_schema(cls, *args, **kwargs):\n"
        "        global _calls\n"
        "        _calls += 1\n"
        "        if _calls > 1:\n"
        f"            __import__({dependency_name!r})\n"
        "        return super().model_json_schema(*args, **kwargs)\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    with (
        _without_sys_module(module_name),
        _without_sys_module(dependency_name),
        _without_sys_module(unrelated_name),
    ):
        first_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        unrelated_module = __import__(unrelated_name)
        second_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

        assert first_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert second_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        _assert_sys_module_missing(module_name)
        _assert_sys_module_missing(dependency_name)
        _assert_sys_module_is(unrelated_name, unrelated_module)


def test_load_model_schema_keeps_nested_nonlocal_dotted_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep dependencies imported from a nested sys.path entry cached."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_local_model_with_nested_dependency"
    dependency_name = "_nested_nonlocal_dotted_dependency"
    dependency_dir = tmp_path / "site-packages"
    dependency_dir.mkdir()
    (dependency_dir / f"{dependency_name}.py").write_text("FieldType = str\n", encoding="utf-8")
    (tmp_path / f"{module_name}.py").write_text(
        "from pydantic import BaseModel\n"
        f"from {dependency_name} import FieldType\n\n"
        "class Model(BaseModel):\n"
        "    value: FieldType\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(dependency_dir))

    with _without_sys_module(module_name), _without_sys_module(dependency_name):
        schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        dependency_module = sys.modules.get(dependency_name)

        assert schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        _assert_sys_module_missing(module_name)
        if dependency_module is None:  # pragma: no cover
            pytest.fail("Expected the nested nonlocal dependency to retain standard import caching")
        _assert_sys_module_is(dependency_name, dependency_module)


def test_load_model_schema_reuses_cwd_independent_cached_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reuse a simple loaded model without entering request-local import state."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    caller_dir = tmp_path / "caller"
    module_dir = tmp_path / "modules"
    caller_dir.mkdir()
    module_dir.mkdir()
    module_name = "_cwd_independent_cached_model"
    (module_dir / f"{module_name}.py").write_text(
        "from pydantic import BaseModel\n\n"
        "class Model(BaseModel):\n"
        "    value: str\n"
        "    count: int\n\n"
        "class ModelList(BaseModel):\n"
        "    values: list[str]\n\n"
        + "".join(f"class Model{index}(BaseModel):\n    value: str\n\n" for index in range(17)),
        encoding="utf-8",
    )
    monkeypatch.chdir(caller_dir)
    monkeypatch.syspath_prepend(str(caller_dir))
    monkeypatch.syspath_prepend(str(module_dir))

    with _without_sys_module(module_name):
        cached_module = __import__(module_name)
        original_model = cached_module.Model
        first_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        second_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        list_schema = load_model_schema([f"{module_name}:ModelList"], InputFileType.Auto)
        cached_module.Model = cached_module.ModelList
        replacement_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        cached_module.Model = original_model
        for index in range(17):
            load_model_schema([f"{module_name}:Model{index}"], InputFileType.Auto)
        (caller_dir / f"{module_name}.py").write_text(
            "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    value: str\n    count: str\n",
            encoding="utf-8",
        )
        collision_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

        assert first_schema == second_schema
        assert first_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert first_schema["properties"]["count"]["type"] == "integer"  # ty: ignore[call-non-callable]
        assert list_schema["properties"]["values"]["items"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert replacement_schema == list_schema
        assert collision_schema == first_schema
        _assert_sys_module_is(module_name, cached_module)


def test_load_model_schema_reuses_safe_private_dotted_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generate a primitive cached local model without restoring it into sys.modules."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_safe_private_cached_model"
    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(
        "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    value: str\n    count: int\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    with _without_sys_module(module_name):
        first_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        second_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        third_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        module_path.write_text(
            "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    changed_value: int\n",
            encoding="utf-8",
        )
        changed_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

        assert first_schema == second_schema == third_schema
        assert first_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert first_schema["properties"]["count"]["type"] == "integer"  # ty: ignore[call-non-callable]
        assert changed_schema["properties"]["changed_value"]["type"] == "integer"  # ty: ignore[call-non-callable]
        _assert_sys_module_missing(module_name)


def test_load_model_schema_refreshes_changed_private_dotted_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reload a cached local model when its source or local dependency changes."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_refreshable_private_cached_model"
    dependency_name = "_refreshable_private_cached_dependency"
    module_path = tmp_path / f"{module_name}.py"
    dependency_path = tmp_path / f"{dependency_name}.py"
    dependency_path.write_text("FieldType = str\n", encoding="utf-8")
    module_path.write_text(
        "from pydantic import BaseModel\n"
        f"from {dependency_name} import FieldType\n\n"
        "class Model(BaseModel):\n"
        "    value: FieldType\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    with _without_sys_module(module_name), _without_sys_module(dependency_name):
        initial_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        dependency_path.write_text("FieldType = list[str]\n", encoding="utf-8")
        dependency_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        module_path.write_text(
            "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    updated_value: int\n",
            encoding="utf-8",
        )
        updated_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

        assert initial_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert dependency_schema["properties"]["value"]["items"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert updated_schema["properties"]["updated_value"]["type"] == "integer"  # ty: ignore[call-non-callable]
        _assert_sys_module_missing(module_name)
        _assert_sys_module_missing(dependency_name)


def test_load_model_schema_refreshes_changed_private_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reload a cached local model when its parent package initializer changes."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    package_name = "_refreshable_private_package"
    module_name = f"{package_name}.model"
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    init_path = package_dir / "__init__.py"
    init_path.write_text("FieldType = str\n", encoding="utf-8")
    (package_dir / "model.py").write_text(
        f"from {package_name} import FieldType\n"
        "from pydantic import BaseModel\n\n"
        "class Model(BaseModel):\n"
        "    value: FieldType\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    with _without_sys_module(package_name), _without_sys_module(module_name):
        initial_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        init_path.write_text("FieldType = list[str]\n", encoding="utf-8")
        updated_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

        assert initial_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert updated_schema["properties"]["value"]["items"]["type"] == "string"  # ty: ignore[call-non-callable]
        _assert_sys_modules_with_prefix(package_name, set())


def test_load_model_schema_refreshes_referenced_inert_parent_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Track an inert parent package explicitly referenced by the model module."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    package_name = "_referenced_inert_private_package"
    module_name = f"{package_name}.model"
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    init_path = package_dir / "__init__.py"
    init_path.write_text("", encoding="utf-8")
    (package_dir / "model.py").write_text(
        f"import {package_name}\n"
        "from pydantic import BaseModel\n\n"
        f"FieldType = getattr({package_name}, 'FieldType', str)\n\n"
        "class Model(BaseModel):\n"
        "    value: FieldType\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    with _without_sys_module(package_name), _without_sys_module(module_name):
        initial_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        init_path.write_text("FieldType = int\n", encoding="utf-8")
        updated_schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

        assert initial_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert updated_schema["properties"]["value"]["type"] == "integer"  # ty: ignore[call-non-callable]
        _assert_sys_modules_with_prefix(package_name, set())


def test_input_module_baseline_detects_same_size_key_replacement() -> None:
    """Refresh the module baseline when its size and final key remain unchanged."""
    from datamodel_code_generator.input_model import _input_module_baseline

    removed_name = "_input_baseline_removed"
    added_name = "_input_baseline_added"
    last_name = "_input_baseline_last"
    removed_module = types.ModuleType(removed_name)
    added_module = types.ModuleType(added_name)
    last_module = types.ModuleType(last_name)

    with (
        _without_sys_module(removed_name),
        _without_sys_module(added_name),
        _without_sys_module(last_name),
    ):
        sys.modules[removed_name] = removed_module
        sys.modules[last_name] = last_module
        _, initial_names = _input_module_baseline()
        sys.modules.pop(removed_name)
        sys.modules[added_name] = added_module
        sys.modules.pop(last_name)
        sys.modules[last_name] = last_module
        _, refreshed_names = _input_module_baseline()

        assert removed_name in initial_names
        assert added_name not in initial_names
        assert removed_name not in refreshed_names
        assert added_name in refreshed_names


def test_load_model_schema_cleans_lazy_import_after_same_size_module_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not let a stale module-name baseline retain a request-local lazy import."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import _input_module_baseline, load_model_schema

    module_name = "_baseline_swap_cached_model"
    dependency_name = "_baseline_swap_lazy_dependency"
    added_name = "_baseline_swap_added"
    last_name = "_baseline_swap_last"
    (tmp_path / f"{dependency_name}.py").write_text("VALUE = 'loaded'\n", encoding="utf-8")
    (tmp_path / f"{module_name}.py").write_text(
        "from pydantic import BaseModel\n\n"
        "class Model(BaseModel):\n"
        "    value: str\n\n"
        "    @classmethod\n"
        "    def model_json_schema(cls, *args, **kwargs):\n"
        f"        __import__({dependency_name!r})\n"
        "        return super().model_json_schema(*args, **kwargs)\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    with (
        _without_sys_module(module_name),
        _without_sys_module(dependency_name),
        _without_sys_module(added_name),
        _without_sys_module(last_name),
    ):
        load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        sys.modules[dependency_name] = types.ModuleType(dependency_name)
        sys.modules[last_name] = last_module = types.ModuleType(last_name)
        _input_module_baseline()
        sys.modules.pop(dependency_name)
        sys.modules[added_name] = types.ModuleType(added_name)
        sys.modules.pop(last_name)
        sys.modules[last_name] = last_module

        load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

        _assert_sys_module_missing(module_name)
        _assert_sys_module_missing(dependency_name)


def test_input_model_module_origin_helpers_use_real_origins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recognize a real module file while rejecting a module without an origin."""
    from datamodel_code_generator.input_model import (
        _local_module_fingerprint,
        _local_module_fingerprint_is_current,
        _module_is_from_directory,
        _module_is_from_local_import,
    )

    module_name = "_input_model_origin_helper"
    (tmp_path / f"{module_name}.py").write_text("VALUE = 'loaded'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    with _without_sys_module(module_name):
        module = __import__(module_name)
        originless_module = types.ModuleType("_originless_input_model")
        namespace_module = types.ModuleType("_namespace_input_dependency")
        namespace_module.__path__ = [str(tmp_path)]  # ty: ignore[unresolved-attribute]
        missing_module = types.ModuleType("_missing_input_model")
        missing_module.__file__ = str(tmp_path / "missing.py")

        assert _module_is_from_directory(module, tmp_path)
        assert not _module_is_from_local_import(module_name, types.ModuleType(module_name), tmp_path)
        assert _local_module_fingerprint(
            module_name,
            {
                module_name: module,
                "_namespace_input_dependency": namespace_module,
                "_nonlocal_input_dependency": types,
            },
            tmp_path,
        )
        assert _local_module_fingerprint(module_name, {module_name: originless_module}, tmp_path) is None
        assert _local_module_fingerprint(module_name, {module_name: missing_module}, tmp_path) is None
        assert not _local_module_fingerprint_is_current(None)
        assert not _local_module_fingerprint_is_current(((str(tmp_path / "missing.py"), 0, 0),))


def test_load_model_schema_reuses_cached_dotted_package_for_new_sibling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reuse a private package cache when loading another module below its root."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    package_name = "_cached_sibling_input_models"
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    for module_name, field_type in (("first", "str"), ("second", "int")):
        (package_dir / f"{module_name}.py").write_text(
            f"from pydantic import BaseModel\n\nclass Model(BaseModel):\n    value: {field_type}\n",
            encoding="utf-8",
        )
    first_module = f"{package_name}.first"
    second_module = f"{package_name}.second"
    monkeypatch.chdir(tmp_path)

    with (
        _without_sys_module(package_name),
        _without_sys_module(first_module),
        _without_sys_module(second_module),
    ):
        first_schema = load_model_schema([f"{first_module}:Model"], InputFileType.Auto)
        second_schema = load_model_schema([f"{second_module}:Model"], InputFileType.Auto)

        assert first_schema["properties"]["value"]["type"] == "string"  # ty: ignore[call-non-callable]
        assert second_schema["properties"]["value"]["type"] == "integer"  # ty: ignore[call-non-callable]
        _assert_sys_modules_with_prefix(package_name, set())


def test_load_model_schema_bounds_local_dotted_module_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evict the least-recently used private module state at the cache bound."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import (
        _LOCAL_DOTTED_MODULE_CACHE,
        _LOCAL_DOTTED_MODULE_CACHE_SIZE,
        load_model_schema,
    )

    module_names = [f"_bounded_input_model_{index}" for index in range(_LOCAL_DOTTED_MODULE_CACHE_SIZE + 1)]
    for module_name in module_names:
        (tmp_path / f"{module_name}.py").write_text(
            "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    value: str\n",
            encoding="utf-8",
        )
    monkeypatch.chdir(tmp_path)

    for module_name in module_names:
        with _without_sys_module(module_name):
            load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
            _assert_sys_module_missing(module_name)

    assert len(_LOCAL_DOTTED_MODULE_CACHE) == _LOCAL_DOTTED_MODULE_CACHE_SIZE


def test_load_model_schema_serializes_cached_dotted_dynamic_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep cached schema-hook imports isolated across concurrent requests."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_concurrent_cached_dynamic_model"
    dependency_name = "_concurrent_cached_dynamic_dependency"
    control_name = "_concurrent_cached_dynamic_control"
    (tmp_path / f"{dependency_name}.py").write_text("VALUE = 'loaded'\n", encoding="utf-8")
    (tmp_path / f"{module_name}.py").write_text(
        f"import {control_name}\n"
        "from pydantic import BaseModel\n\n"
        "class Model(BaseModel):\n"
        "    value: str\n\n"
        "    @classmethod\n"
        "    def model_json_schema(cls, *args, **kwargs):\n"
        f"        if {control_name}.enabled:\n"
        f"            {control_name}.enter()\n"
        f"            __import__({dependency_name!r})\n"
        "        return super().model_json_schema(*args, **kwargs)\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    entered = [Event(), Event()]
    release = [Event(), Event()]
    enter_lock = Lock()
    enter_count = 0

    def enter() -> None:
        nonlocal enter_count
        with enter_lock:
            index = enter_count
            enter_count += 1
        entered[index].set()
        release[index].wait(timeout=5)

    control_module = types.ModuleType(control_name)
    control_module.enabled = False  # ty: ignore[unresolved-attribute]
    control_module.enter = enter  # ty: ignore[unresolved-attribute]
    schemas: list[dict[str, object]] = []
    errors: list[Exception] = []

    def load_schema() -> None:
        try:
            schemas.append(load_model_schema([f"{module_name}:Model"], InputFileType.Auto))
        except Exception as exc:  # noqa: BLE001  # pragma: no cover
            errors.append(exc)

    with (
        _without_sys_module(module_name),
        _without_sys_module(dependency_name),
        _without_sys_module(control_name),
    ):
        sys.modules[control_name] = control_module
        load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        control_module.enabled = True  # ty: ignore[unresolved-attribute]
        threads = [Thread(target=load_schema) for _ in range(2)]
        threads[0].start()
        assert entered[0].wait(timeout=5)
        threads[1].start()
        try:
            assert not entered[1].wait(timeout=0.1)
            release[0].set()
            assert entered[1].wait(timeout=5)
        finally:
            for event in release:
                event.set()
            for thread in threads:
                thread.join(timeout=5)

        _assert_sys_module_missing(module_name)
        _assert_sys_module_missing(dependency_name)

    assert not errors
    assert len(schemas) == 2
    assert all(not thread.is_alive() for thread in threads)


def test_load_model_schema_restores_failing_cwd_local_dotted_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Restore local dotted import state when module execution fails."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_failing_local_input_model"
    (tmp_path / f"{module_name}.py").write_text("raise RuntimeError('module failed')\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with (
        _without_sys_module(module_name),
        pytest.raises(RuntimeError, match="module failed"),
    ):
        load_model_schema([f"{module_name}:Model"], InputFileType.Auto)

    _assert_sys_module_missing(module_name)


def test_load_model_schema_isolates_cwd_local_namespace_packages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not retain a same-named namespace package between request directories."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    package_name = "_request_namespace_models"
    module_name = f"{package_name}.models"
    request_paths = [tmp_path / "first", tmp_path / "second"]
    for request_path, field_type in zip(request_paths, ("str", "int"), strict=True):
        package_path = request_path / package_name
        package_path.mkdir(parents=True)
        (package_path / "models.py").write_text(
            f"from pydantic import BaseModel\n\nclass Model(BaseModel):\n    value: {field_type}\n",
            encoding="utf-8",
        )

    property_types: list[str] = []
    with _without_sys_module(package_name), _without_sys_module(module_name):
        for request_path in request_paths:
            monkeypatch.chdir(request_path)
            schema = load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
            property_types.append(schema["properties"]["value"]["type"])  # ty: ignore[call-non-callable]
            _assert_sys_modules_with_prefix(package_name, set())

    assert property_types == ["string", "integer"]


def test_load_model_schema_restore_does_not_replace_newer_module_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leave a module replacement made after request-local loading untouched."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    module_name = "_identity_safe_input_model"
    control_name = "_identity_safe_input_model_control"
    (tmp_path / f"{module_name}.py").write_text(
        "import sys\n"
        "import types\n"
        f"import {control_name}\n"
        "from pydantic import BaseModel\n\n"
        "class Model(BaseModel):\n"
        "    value: str\n\n"
        "    @classmethod\n"
        "    def model_json_schema(cls, *args, **kwargs):\n"
        "        replacement = types.ModuleType(__name__)\n"
        f"        {control_name}.replacement = replacement\n"
        "        sys.modules[__name__] = replacement\n"
        "        return super().model_json_schema(*args, **kwargs)\n",
        encoding="utf-8",
    )
    previous_module = types.ModuleType(module_name)
    control_module = types.ModuleType(control_name)

    with _without_sys_module(module_name), _without_sys_module(control_name):
        sys.modules[module_name] = previous_module
        sys.modules[control_name] = control_module
        monkeypatch.chdir(tmp_path)
        load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        _assert_sys_module_is(module_name, control_module.replacement)  # ty: ignore[unresolved-attribute]


def test_load_model_schema_tracks_concurrent_cwd_sys_path_users(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the temporary cwd path until the final concurrent dotted request exits."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    caller_dir = tmp_path / "caller"
    module_dir = tmp_path / "modules"
    caller_dir.mkdir()
    module_dir.mkdir()
    module_names = ("_first_nonlocal_input_model", "_second_nonlocal_input_model")
    control_name = "_nonlocal_input_model_control"
    for module_name in module_names:
        (module_dir / f"{module_name}.py").write_text(
            "from pydantic import BaseModel\n"
            f"import {control_name}\n\n"
            "class Model(BaseModel):\n"
            "    value: str\n\n"
            "    @classmethod\n"
            "    def model_json_schema(cls, *args, **kwargs):\n"
            f"        {control_name}.enter({module_name!r})\n"
            "        return super().model_json_schema(*args, **kwargs)\n",
            encoding="utf-8",
        )
    entered = {module_name: Event() for module_name in module_names}
    release = {module_name: Event() for module_name in module_names}

    def enter(module_name: str) -> None:
        entered[module_name].set()
        release[module_name].wait(timeout=5)

    control_module = types.ModuleType(control_name)
    control_module.enter = enter  # ty: ignore[unresolved-attribute]
    errors: list[Exception] = []

    def load_schema(module_name: str) -> None:
        try:
            load_model_schema([f"{module_name}:Model"], InputFileType.Auto)
        except Exception as exc:  # noqa: BLE001  # pragma: no cover
            errors.append(exc)

    monkeypatch.chdir(caller_dir)
    monkeypatch.syspath_prepend(str(module_dir))
    cwd = str(caller_dir)
    threads = [Thread(target=load_schema, args=(module_name,)) for module_name in module_names]
    with (
        _without_sys_module(module_names[0]),
        _without_sys_module(module_names[1]),
        _without_sys_module(control_name),
    ):
        sys.modules[control_name] = control_module
        for thread in threads:
            thread.start()
        try:
            for module_name in module_names:
                assert entered[module_name].wait(timeout=5)
            release[module_names[0]].set()
            threads[0].join(timeout=5)
            assert cwd in sys.path
        finally:
            for event in release.values():
                event.set()
            for thread in threads:
                thread.join(timeout=5)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert cwd not in sys.path


def test_path_is_within_rejects_invalid_path(tmp_path: Path) -> None:
    """Treat an invalid third-party module path as outside the request directory."""
    from datamodel_code_generator.input_model import _path_is_within

    assert not _path_is_within(object(), tmp_path)  # type: ignore[arg-type]


@pytest.mark.parametrize(("outer_is_path", "nested_is_path"), [(True, False), (False, True)])
def test_load_model_schema_supports_recursive_path_and_dotted_contexts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    outer_is_path: bool,
    nested_is_path: bool,
) -> None:
    """Keep recursive path and dotted model loads compatible without leaking context."""
    from datamodel_code_generator import InputFileType
    from datamodel_code_generator.input_model import load_model_schema

    control_name = "_input_model_recursive_context_control"
    outer_name = "_recursive_outer_model"
    nested_name = "_recursive_nested_model"
    outer_path = tmp_path / f"{outer_name}.py"
    nested_path = tmp_path / f"{nested_name}.py"
    outer_path.write_text(
        "from pydantic import BaseModel\n"
        f"import {control_name}\n\n"
        "class Outer(BaseModel):\n"
        "    value: str\n\n"
        "    @classmethod\n"
        "    def model_json_schema(cls, *args, **kwargs):\n"
        f"        {control_name}.load_nested()\n"
        "        return super().model_json_schema(*args, **kwargs)\n",
        encoding="utf-8",
    )
    nested_path.write_text(
        "from pydantic import BaseModel\n\nclass Nested(BaseModel):\n    value: str\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    outer_module = str(outer_path.resolve()) if outer_is_path else outer_name
    nested_module = str(nested_path.resolve()) if nested_is_path else nested_name
    nested_schemas: list[dict[str, object]] = []
    outer_schemas: list[dict[str, object]] = []
    errors: list[Exception] = []

    def load_nested() -> None:
        nested_schemas.append(load_model_schema([f"{nested_module}:Nested"], InputFileType.Auto))

    control_module = types.ModuleType(control_name)
    control_module.load_nested = load_nested  # ty: ignore[unresolved-attribute]

    def load_outer() -> None:
        try:
            outer_schemas.append(load_model_schema([f"{outer_module}:Outer"], InputFileType.Auto))
        except Exception as exc:  # noqa: BLE001  # pragma: no cover - surfaced in the test thread
            errors.append(exc)

    thread = Thread(target=load_outer)
    with (
        _without_sys_module(outer_name),
        _without_sys_module(nested_name),
        _without_sys_module(control_name),
    ):
        sys.modules[control_name] = control_module
        thread.start()
        thread.join(timeout=5)

    assert not thread.is_alive()
    if errors:  # pragma: no cover
        raise errors[0]
    assert outer_schemas[0]["title"] == "Outer"
    assert nested_schemas[0]["title"] == "Nested"
    _assert_sys_module_missing(outer_name)
    _assert_sys_module_missing(nested_name)


def test_is_input_model_base_schema_requires_dict() -> None:
    """Test base schema detection returns false for non-dict values."""
    from datamodel_code_generator.input_model import _is_input_model_base_schema

    assert not _is_input_model_base_schema("not a schema")


# ============================================================================
# x-python-type preservation tests
# ============================================================================


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


def test_input_model_dataclass_with_python_types(tmp_path: Path) -> None:
    """Test that Set/Mapping types are preserved from dataclass input."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.dataclass_models:DataclassWithPythonTypes",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "dataclass_with_python_types.py",
    )


def test_input_model_recursive_model_types(tmp_path: Path) -> None:
    """Test that recursive models handle x-python-type correctly."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:RecursiveNode",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "recursive_model_types.py",
    )


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


def test_input_model_nested_model_with_callable(tmp_path: Path) -> None:
    """Test that nested models with Callable types in $defs are processed."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithNestedCallable",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "nested_model_with_callable.py",
    )


def test_input_model_custom_class(tmp_path: Path) -> None:
    """Test that custom classes trigger handle_invalid_for_json_schema."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCustomClass",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "custom_class.py",
    )


def test_input_model_union_callable(tmp_path: Path) -> None:
    """Test that Union[Callable, int] and raw Callable are preserved."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithUnionCallable",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "union_callable.py",
    )


def test_input_model_custom_generic_type_import(tmp_path: Path) -> None:
    """Test that custom generic types are properly imported with full module path."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.pydantic_models:ModelWithCustomGeneric",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "custom_generic_type_import.py",
    )


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


def test_input_model_path_ref_strategy_reuse_all_keeps_stem_imports(tmp_path: Path) -> None:
    """Test path-based reuse-all keeps the existing stem-based import path."""
    run_input_model_and_assert(
        input_model="tests/data/python/input_model/nested_models.py:User",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "path_ref_strategy_reuse_all.py",
        extra_args=[
            "--output-model-type",
            "typing.TypedDict",
            "--input-model-ref-strategy",
            "reuse-all",
        ],
    )


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
    run_main_with_args(
        args,
        use_parsed_source_cache=False,
        use_builtin_default_formatter=False,
        isolate_model_template_cache=True,
    )


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


def test_input_model_ref_strategy_reuse_foreign_pydantic_output(tmp_path: Path) -> None:
    """Test reuse-foreign imports Pydantic when output is Pydantic (same family)."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.mixed_nested:ModelWithPydantic",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "ref_strategy_reuse_foreign_pydantic_output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--input-model-ref-strategy",
            "reuse-foreign",
        ],
    )


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
    with freeze_time(TIMESTAMP):
        run_main_with_args(
            _input_model_args(input_models, output_path=output_path, extra_args=extra_args),
            use_parsed_source_cache=False,
            use_builtin_default_formatter=False,
            isolate_model_template_cache=True,
        )
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
    run_main_with_args(
        _input_model_args(input_models, extra_args=extra_args),
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=expected_stderr_contains,
        use_parsed_source_cache=False,
        use_builtin_default_formatter=False,
        isolate_model_template_cache=True,
    )


def test_input_model_single_with_inheritance(tmp_path: Path) -> None:
    """Test single --input-model with inherited model generates inheritance chain."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.inheritance_models:ChildA",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "single_inheritance.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


def test_input_model_single_multi_level_inheritance(tmp_path: Path) -> None:
    """Test single --input-model with multi-level inheritance."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.inheritance_models:GrandChild",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "multi_level_inheritance.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


def test_input_model_single_no_inheritance(tmp_path: Path) -> None:
    """Test single --input-model with model that has no inheritance."""
    run_input_model_and_assert(
        input_model="tests.data.python.input_model.inheritance_models:NoInheritance",
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "no_inheritance.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


def test_input_model_multiple_forked_inheritance(tmp_path: Path) -> None:
    """Test multiple --input-model with forked inheritance shares common parent."""
    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "forked_inheritance.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


def test_input_model_multiple_mixed_inheritance(tmp_path: Path) -> None:
    """Test multiple --input-model with different inheritance depths."""
    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:GrandChild",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "mixed_inheritance.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


def test_input_model_multiple_with_pydantic_output(tmp_path: Path) -> None:
    """Test multiple --input-model works with Pydantic output."""
    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "tests.data.python.input_model.inheritance_models:ChildB",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "multiple_with_pydantic_output.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )


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


def test_input_model_multiple_file_path_same_basename_forward_refs(tmp_path: Path) -> None:
    """Test same-basename path modules keep separate namespaces for forward refs."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first_model_path = first_dir / "models.py"
    second_model_path = second_dir / "models.py"
    first_model_path.write_text(
        "from __future__ import annotations\n\n"
        "from pydantic import BaseModel\n\n"
        "class UserA(BaseModel):\n"
        "    friend: FriendA\n\n"
        "class FriendA(BaseModel):\n"
        "    alpha: str\n",
        encoding="utf-8",
    )
    second_model_path.write_text(
        "from __future__ import annotations\n\n"
        "from pydantic import BaseModel\n\n"
        "class UserB(BaseModel):\n"
        "    friend: FriendB\n\n"
        "class FriendB(BaseModel):\n"
        "    beta: int\n",
        encoding="utf-8",
    )
    module_name = first_model_path.stem
    temporary_module_prefix = "_datamodel_code_generator_input_model_"
    existing_temporary_modules = {
        module_name for module_name in sys.modules if module_name.startswith(temporary_module_prefix)
    }

    with _without_sys_module(module_name):
        run_multiple_input_models_and_assert(
            input_models=[
                f"{first_model_path}:UserA",
                f"{second_model_path}:UserB",
            ],
            output_path=tmp_path / "output.py",
            expected_file=EXPECTED_INPUT_MODEL_PATH / "multiple_same_basename_paths.py",
        )

        _assert_sys_module_missing(module_name)
        _assert_sys_modules_with_prefix(temporary_module_prefix, existing_temporary_modules)


def test_input_model_multiple_file_path_format_restores_sys_modules(tmp_path: Path) -> None:
    """Test multiple path-based --input-model entries do not keep temporary modules alive."""
    model_path = tmp_path / "multiple_input_model.py"
    model_path.write_text(
        "from pydantic import BaseModel\n\n"
        "class GrandParent(BaseModel):\n"
        "    grand_field: str\n\n"
        "class Parent(GrandParent):\n"
        "    parent_field: int\n\n"
        "class ChildA(Parent):\n"
        "    child_a_field: float\n\n"
        "class ChildB(Parent):\n"
        "    child_b_field: bool\n",
        encoding="utf-8",
    )
    module_name = model_path.stem

    with _without_sys_module(module_name):
        run_multiple_input_models_and_assert(
            input_models=[
                f"{model_path}:ChildA",
                f"{model_path}:ChildB",
            ],
            output_path=tmp_path / "output.py",
            expected_file=EXPECTED_INPUT_MODEL_PATH / "forked_inheritance.py",
            extra_args=["--output-model-type", "typing.TypedDict"],
        )

        _assert_sys_module_missing(module_name)


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


def test_input_model_empty_child_no_properties(
    tmp_path: Path,
) -> None:
    """Test inheritance with empty child that adds no properties."""
    run_multiple_input_models_and_assert(
        input_models=["tests.data.python.input_model.inheritance_models:EmptyChild"],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "empty_child_no_properties.py",
    )


def test_input_model_optional_only_child_no_required(
    tmp_path: Path,
) -> None:
    """Test inheritance with child that adds only optional fields."""
    run_multiple_input_models_and_assert(
        input_models=["tests.data.python.input_model.inheritance_models:OptionalOnlyChild"],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "optional_only_child_no_required.py",
    )


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
        extra_args=["--output-model-type", "pydantic_v2.BaseModel"],
    )
    final_count = sys.path.count(cwd)
    assert final_count == initial_count


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

    run_multiple_input_models_and_assert(
        input_models=[
            "tests.data.python.input_model.inheritance_models:ChildA",
            "temp_model.py:TempModel",
        ],
        output_path=tmp_path / "output.py",
        expected_file=EXPECTED_INPUT_MODEL_PATH / "multiple_py_file_without_path_separator.py",
    )


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
        run_main_with_args(
            ["--output", str(output_path)],
            use_parsed_source_cache=False,
            use_builtin_default_formatter=False,
            isolate_model_template_cache=True,
        )
    assert_output(
        output_path.read_text(encoding="utf-8"),
        EXPECTED_INPUT_MODEL_PATH / "no_inheritance.py",
    )


def test_input_model_output_model_type_default() -> None:
    """Test that output_model_type defaults to PydanticV2BaseModel when not specified."""
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
