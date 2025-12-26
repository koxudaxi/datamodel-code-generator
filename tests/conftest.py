"""Test configuration and shared fixtures."""

from __future__ import annotations

import difflib
import inspect
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, cast

import pytest
import time_machine
from inline_snapshot import external_file, register_format_alias
from typing_extensions import Required

from datamodel_code_generator import MIN_VERSION

if TYPE_CHECKING:
    from collections.abc import Callable

CLI_DOC_COLLECTION_OUTPUT = Path(__file__).parent / "cli_doc" / ".cli_doc_collection.json"
CLI_DOC_SCHEMA_VERSION = 1
_VERSION_PATTERN = re.compile(r"^\d+\.\d+$")


class CliDocKwargs(TypedDict, total=False):
    """Type definition for @pytest.mark.cli_doc marker keyword arguments."""

    options: Required[list[str]]
    cli_args: Required[list[str]]
    input_schema: str | None
    config_content: str | None
    input_model: str | None
    golden_output: str | None
    version_outputs: dict[str, str] | None
    model_outputs: dict[str, str] | None
    expected_stdout: str | None
    related_options: list[str] | None
    aliases: list[str] | None


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --collect-cli-docs option."""
    parser.addoption(
        "--collect-cli-docs",
        action="store_true",
        default=False,
        help="Collect CLI documentation metadata from tests marked with @pytest.mark.cli_doc",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the cli_doc marker."""
    config.addinivalue_line(
        "markers",
        "cli_doc(options, input_schema=None, cli_args=None, golden_output=None, version_outputs=None, "
        "model_outputs=None, expected_stdout=None, config_content=None, aliases=None, **kwargs): "
        "Mark test as CLI documentation source. "
        "Either golden_output, version_outputs, model_outputs, or expected_stdout is required. "
        "aliases: list of alternative option names (e.g., ['--capitalise-enum-members']).",
    )
    config._cli_doc_items: list[dict[str, Any]] = []


def _validate_cli_doc_marker(node_id: str, kwargs: CliDocKwargs) -> list[str]:  # noqa: ARG001, PLR0912, PLR0914  # pragma: no cover
    """Validate marker required fields and types."""
    errors: list[str] = []

    if "options" not in kwargs:
        errors.append("Missing required field: 'options'")
    if "cli_args" not in kwargs:
        errors.append("Missing required field: 'cli_args'")

    has_golden = "golden_output" in kwargs and kwargs["golden_output"] is not None
    has_versions = "version_outputs" in kwargs and kwargs["version_outputs"] is not None
    has_models = "model_outputs" in kwargs and kwargs["model_outputs"] is not None
    has_stdout = "expected_stdout" in kwargs and kwargs["expected_stdout"] is not None
    if not has_golden and not has_versions and not has_models and not has_stdout:
        errors.append("Either 'golden_output', 'version_outputs', 'model_outputs', or 'expected_stdout' is required")

    has_input_schema = "input_schema" in kwargs and kwargs["input_schema"] is not None
    has_config_content = "config_content" in kwargs and kwargs["config_content"] is not None
    has_input_model = "input_model" in kwargs and kwargs["input_model"] is not None
    if not has_input_schema and not has_config_content and not has_input_model and not has_stdout:
        errors.append(
            "Either 'input_schema', 'config_content', or 'input_model' is required "
            "(or 'expected_stdout' with cli_args as input)"
        )

    if "options" in kwargs:
        opts = kwargs["options"]
        if not isinstance(opts, list):
            errors.append(f"'options' must be a list, got {type(opts).__name__}")
        elif not opts:
            errors.append("'options' must be a non-empty list")
        elif not all(isinstance(o, str) for o in opts):
            errors.append("'options' must be a list of strings")

    if "cli_args" in kwargs:
        args = kwargs["cli_args"]
        if not isinstance(args, list):
            errors.append(f"'cli_args' must be a list, got {type(args).__name__}")
        elif not all(isinstance(a, str) for a in args):
            errors.append("'cli_args' must be a list of strings")

    if "input_schema" in kwargs:
        schema = kwargs["input_schema"]
        if not isinstance(schema, str):
            errors.append(f"'input_schema' must be a string, got {type(schema).__name__}")

    if has_input_model:
        input_model = kwargs["input_model"]
        if not isinstance(input_model, str):
            errors.append(f"'input_model' must be a string, got {type(input_model).__name__}")
        else:
            parts = input_model.split(":", 1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"'input_model' must be in 'module:name' format, got {input_model!r}")

    if has_golden:
        golden = kwargs["golden_output"]
        if not isinstance(golden, str):
            errors.append(f"'golden_output' must be a string, got {type(golden).__name__}")

    if has_versions:
        versions = kwargs["version_outputs"]
        if not isinstance(versions, dict):
            errors.append(f"'version_outputs' must be a dict, got {type(versions).__name__}")
        else:
            for key, value in versions.items():
                if not isinstance(key, str):
                    errors.append(f"'version_outputs' keys must be strings, got {type(key).__name__}")
                elif not _VERSION_PATTERN.match(key):
                    errors.append(f"Invalid version key '{key}': must match X.Y format (e.g., '3.10')")
                if not isinstance(value, str):
                    errors.append(f"'version_outputs' values must be strings, got {type(value).__name__}")

    if has_models:
        models = kwargs["model_outputs"]
        if not isinstance(models, dict):
            errors.append(f"'model_outputs' must be a dict, got {type(models).__name__}")
        else:
            valid_keys = {"pydantic_v1", "pydantic_v2", "dataclass", "typeddict", "msgspec"}
            for key, value in models.items():
                if not isinstance(key, str):
                    errors.append(f"'model_outputs' keys must be strings, got {type(key).__name__}")
                elif key not in valid_keys:
                    errors.append(f"Invalid model key '{key}': must be one of {valid_keys}")
                if not isinstance(value, str):
                    errors.append(f"'model_outputs' values must be strings, got {type(value).__name__}")

    if "related_options" in kwargs:
        related = kwargs["related_options"]
        if not isinstance(related, list):
            errors.append(f"'related_options' must be a list, got {type(related).__name__}")
        elif not all(isinstance(r, str) for r in related):
            errors.append("'related_options' must be a list of strings")

    if "aliases" in kwargs:
        aliases = kwargs["aliases"]
        if aliases is not None:
            if not isinstance(aliases, list):
                errors.append(f"'aliases' must be a list, got {type(aliases).__name__}")
            elif not all(isinstance(a, str) for a in aliases):
                errors.append("'aliases' must be a list of strings")

    return errors


def pytest_collection_modifyitems(
    session: pytest.Session,  # noqa: ARG001
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:  # pragma: no cover
    """Collect CLI doc metadata from tests with cli_doc marker.

    Always collects metadata for use by test_cli_doc_coverage.py.
    Only validates markers when --collect-cli-docs is used.
    """
    collect_cli_docs = config.getoption("--collect-cli-docs", default=False)
    validation_errors: list[tuple[str, list[str]]] = []

    for item in items:
        marker = item.get_closest_marker("cli_doc")
        if marker is None:
            continue

        if collect_cli_docs:
            errors = _validate_cli_doc_marker(item.nodeid, cast("CliDocKwargs", marker.kwargs))
            if errors:
                validation_errors.append((item.nodeid, errors))
                continue

        docstring = ""
        func = getattr(item, "function", None)
        if func is not None:
            docstring = func.__doc__ or ""

        config._cli_doc_items.append({
            "node_id": item.nodeid,
            "marker_kwargs": marker.kwargs,
            "docstring": docstring,
        })

    if validation_errors:
        error_msg = "CLI doc marker validation errors:\n"
        for node_id, errors in validation_errors:
            error_msg += f"\n  {node_id}:\n"
            error_msg += "\n".join(f"    - {e}" for e in errors)
        pytest.fail(error_msg, pytrace=False)


def pytest_runtestloop(session: pytest.Session) -> bool | None:  # pragma: no cover
    """Skip test execution when --collect-cli-docs is used."""
    if session.config.getoption("--collect-cli-docs"):
        return True
    return None


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # noqa: ARG001  # pragma: no cover
    """Save collected CLI doc metadata to JSON file."""
    config = session.config
    if not config.getoption("--collect-cli-docs"):
        return

    items = getattr(config, "_cli_doc_items", [])

    output = {
        "schema_version": CLI_DOC_SCHEMA_VERSION,
        "items": items,
    }

    CLI_DOC_COLLECTION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with Path(CLI_DOC_COLLECTION_OUTPUT).open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


class CodeValidationStats:
    """Track code validation statistics."""

    def __init__(self) -> None:
        """Initialize statistics counters."""
        self.compile_count = 0
        self.compile_time = 0.0
        self.exec_count = 0
        self.exec_time = 0.0
        self.errors: list[tuple[str, str]] = []

    def record_compile(self, elapsed: float) -> None:
        """Record a compile operation."""
        self.compile_count += 1
        self.compile_time += elapsed

    def record_exec(self, elapsed: float) -> None:
        """Record an exec operation."""
        self.exec_count += 1
        self.exec_time += elapsed

    def record_error(self, file_path: str, error: str) -> None:  # pragma: no cover
        """Record a validation error."""
        self.errors.append((file_path, error))


_validation_stats = CodeValidationStats()


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:  # noqa: ARG001  # pragma: no cover
    """Print code validation and CLI doc collection summary at the end of test run."""
    if config.getoption("--collect-cli-docs", default=False):
        items = getattr(config, "_cli_doc_items", [])
        terminalreporter.write_sep("=", "CLI Documentation Collection")
        terminalreporter.write_line(f"Collected {len(items)} CLI doc items -> {CLI_DOC_COLLECTION_OUTPUT}")

    if _validation_stats.compile_count > 0:
        terminalreporter.write_sep("=", "Code Validation Summary")
        terminalreporter.write_line(
            f"Compiled {_validation_stats.compile_count} files in {_validation_stats.compile_time:.3f}s "
            f"(avg: {_validation_stats.compile_time / _validation_stats.compile_count * 1000:.2f}ms)"
        )
        if _validation_stats.exec_count > 0:
            terminalreporter.write_line(
                f"Executed {_validation_stats.exec_count} files in {_validation_stats.exec_time:.3f}s "
                f"(avg: {_validation_stats.exec_time / _validation_stats.exec_count * 1000:.2f}ms)"
            )
        if _validation_stats.errors:
            terminalreporter.write_line(f"\nValidation errors: {len(_validation_stats.errors)}")
            for file_path, error in _validation_stats.errors:
                terminalreporter.write_line(f"  {file_path}: {error}")


def _parse_time_string(time_str: str) -> datetime:
    """Parse time string to datetime with UTC timezone."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(time_str, fmt)  # noqa: DTZ007
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt  # noqa: TRY300
        except ValueError:  # noqa: PERF203
            continue
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))  # pragma: no cover


def freeze_time(time_to_freeze: str, **kwargs: Any) -> time_machine.travel:  # noqa: ARG001
    """Freeze time using time-machine (100-200x faster than freezegun)."""
    dt = _parse_time_string(time_to_freeze)
    return time_machine.travel(dt, tick=False)


def _normalize_line_endings(text: str) -> str:
    """Normalize line endings to LF for cross-platform comparison."""
    return text.replace("\r\n", "\n")


def _get_tox_env() -> str:  # pragma: no cover
    """Get the current tox environment name from TOX_ENV_NAME or fallback.

    Strips '-parallel' suffix since inline-snapshot requires -n0 (single process).
    """
    import os

    env = os.environ.get("TOX_ENV_NAME", "<version>")
    # Remove -parallel suffix since inline-snapshot needs single process mode
    return env.removesuffix("-parallel")


def _format_snapshot_hint(action: str) -> str:  # pragma: no cover
    """Format a hint message for inline-snapshot commands with rich formatting."""
    from io import StringIO

    from rich.console import Console
    from rich.text import Text

    tox_env = _get_tox_env()
    command = f"  tox run -e {tox_env} -- --inline-snapshot={action}"

    description = "To update the expected file, run:" if action == "fix" else "To create the expected file, run:"

    output = StringIO()
    console = Console(file=output, force_terminal=True, width=200, soft_wrap=False)

    console.print(Text(description, style="default"))
    console.print(Text(command, style="bold cyan"))

    return output.getvalue()


def _format_new_content(content: str) -> str:  # pragma: no cover
    """Format new content (for create mode) with green color."""
    from io import StringIO

    from rich.console import Console
    from rich.text import Text

    output = StringIO()
    console = Console(file=output, force_terminal=True, width=200, soft_wrap=False)

    for line in content.splitlines():
        console.print(Text(f"+{line}", style="green"))

    return output.getvalue()


def _format_diff(expected: str, actual: str, expected_path: Path) -> str:  # pragma: no cover
    """Format a unified diff between expected and actual content with colors."""
    from io import StringIO

    from rich.console import Console
    from rich.text import Text

    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile=str(expected_path),
            tofile="actual",
        )
    )

    if not diff_lines:
        return ""

    output = StringIO()
    console = Console(file=output, force_terminal=True, width=200, soft_wrap=False)

    for line in diff_lines:
        line_stripped = line.rstrip("\n")
        # Skip header lines since file path is already in the error message
        if line.startswith(("---", "+++")):
            continue
        if line.startswith("@@"):
            console.print(Text(line_stripped, style="cyan"))
        elif line.startswith("-"):
            console.print(Text(line_stripped, style="red"))
        elif line.startswith("+"):
            console.print(Text(line_stripped, style="green"))
        else:
            # Use default to override pytest's red color for E lines
            console.print(Text(line_stripped, style="default"))

    return output.getvalue()


def _assert_with_external_file(content: str, expected_path: Path) -> None:
    """Assert content matches external file, handling line endings."""
    __tracebackhide__ = True
    try:
        expected = external_file(expected_path)
    except FileNotFoundError:  # pragma: no cover
        hint = _format_snapshot_hint("create")
        formatted_content = _format_new_content(content)
        msg = f"Expected file not found: {expected_path}\n{hint}\n{formatted_content}"
        raise AssertionError(msg) from None  # pragma: no cover
    normalized_content = _normalize_line_endings(content)
    if isinstance(expected, str):  # pragma: no branch
        normalized_expected = _normalize_line_endings(expected)
        if normalized_content != normalized_expected:  # pragma: no cover
            hint = _format_snapshot_hint("fix")
            diff = _format_diff(normalized_expected, normalized_content, expected_path)
            msg = f"Content mismatch for {expected_path}\n{hint}\n{diff}"
            raise AssertionError(msg) from None
    else:
        assert expected == normalized_content  # pragma: no cover


class AssertFileContent(Protocol):
    """Protocol for file content assertion callable."""

    def __call__(
        self,
        output_file: Path,
        expected_name: str | Path | None = None,
        encoding: str = "utf-8",
        transform: Callable[[str], str] | None = None,
    ) -> None:
        """Assert file content matches expected output."""
        ...


def create_assert_file_content(
    base_path: Path,
) -> AssertFileContent:
    """Create an assert function bound to a specific expected path.

    Args:
        base_path: The base path for expected files (e.g., EXPECTED_JSON_SCHEMA_PATH).

    Returns:
        A function that asserts file content matches expected.

    Usage:
        # In test module
        assert_file_content = create_assert_file_content(EXPECTED_JSON_SCHEMA_PATH)

        # In tests - infer from function name
        assert_file_content(output_file)  # test_main_foo -> foo.py

        # Explicit filename
        assert_file_content(output_file, "custom.py")
        assert_file_content(output_file, "subdir/bar.py")
        assert_file_content(output_file, f"{expected_output}/file.py")
    """

    def _assert_file_content(
        output_file: Path,
        expected_name: str | Path | None = None,
        encoding: str = "utf-8",
        transform: Callable[[str], str] | None = None,
    ) -> None:
        """Assert that file content matches expected external file."""
        __tracebackhide__ = True
        if expected_name is None:
            frame = inspect.currentframe()
            assert frame is not None
            assert frame.f_back is not None
            func_name = frame.f_back.f_code.co_name
            del frame
            name = func_name
            for prefix in ("test_main_", "test_"):
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                    break
            expected_name = f"{name}.py"

        expected_path = base_path / expected_name
        content = output_file.read_text(encoding=encoding)
        if transform is not None:
            content = transform(content)
        _assert_with_external_file(content, expected_path)

    return _assert_file_content


def assert_output(
    output: str,
    expected_path: Path,
) -> None:
    """Assert that output string matches expected external file.

    Args:
        output: The output string to compare (e.g., captured.out, parser.parse()).
        expected_path: Path to the expected file.

    Usage:
        assert_output(captured.out, EXPECTED_PATH / "output.py")
        assert_output(parser.parse(), EXPECTED_PATH / "output.py")
    """
    __tracebackhide__ = True
    _assert_with_external_file(output, expected_path)


def assert_directory_content(
    output_dir: Path,
    expected_dir: Path,
    pattern: str = "*.py",
    encoding: str = "utf-8",
) -> None:
    """Assert all files in output_dir match expected files in expected_dir.

    Args:
        output_dir: Directory containing generated output files.
        expected_dir: Directory containing expected files.
        pattern: Glob pattern for files to compare (default: "*.py").
        encoding: File encoding (default: "utf-8").

    Usage:
        assert_directory_content(tmp_path / "model", EXPECTED_PATH / "main_modular")
    """
    __tracebackhide__ = True
    output_files = {p.relative_to(output_dir) for p in output_dir.rglob(pattern)}
    expected_files = {p.relative_to(expected_dir) for p in expected_dir.rglob(pattern)}

    # Check for extra expected files (output missing files that are expected)
    extra = expected_files - output_files
    assert not extra, f"Expected files not in output: {extra}"

    # Compare all output files (including new ones not yet in expected)
    for output_path in output_dir.rglob(pattern):
        relative_path = output_path.relative_to(output_dir)
        expected_path = expected_dir / relative_path
        result = output_path.read_text(encoding=encoding)
        _assert_with_external_file(result, expected_path)


def _get_full_body(result: object) -> str:
    """Get full body from Result."""
    return getattr(result, "body", "")


def assert_parser_results(
    results: dict,
    expected_dir: Path,
    pattern: str = "*.py",
) -> None:
    """Assert parser results match expected files.

    Args:
        results: Dictionary with string keys mapping to objects with .body attribute.
        expected_dir: Directory containing expected files.
        pattern: Glob pattern for files to compare (default: "*.py").

    Usage:
        results = {delimiter.join(p): r for p, r in parser.parse().items()}
        assert_parser_results(results, EXPECTED_PATH / "parser_output")
    """
    __tracebackhide__ = True
    for expected_path in expected_dir.rglob(pattern):
        key = str(expected_path.relative_to(expected_dir))
        result_obj = results.pop(key)
        _assert_with_external_file(_get_full_body(result_obj), expected_path)


def assert_parser_modules(
    modules: dict,
    expected_dir: Path,
) -> None:
    """Assert parser modules match expected files.

    Args:
        modules: Dictionary with tuple keys mapping to objects with .body attribute.
        expected_dir: Directory containing expected files.

    Usage:
        modules = parser.parse()
        assert_parser_modules(modules, EXPECTED_PATH / "parser_modular")
    """
    __tracebackhide__ = True
    for paths, result in modules.items():
        expected_path = expected_dir.joinpath(*paths)
        _assert_with_external_file(_get_full_body(result), expected_path)


@pytest.fixture(autouse=True)
def _inline_snapshot_file_formats() -> None:
    register_format_alias(".py", ".txt")
    register_format_alias(".pyi", ".txt")
    register_format_alias(".snapshot", ".txt")


@pytest.fixture(scope="session")
def min_version() -> str:
    """Return minimum Python version as string."""
    return f"3.{MIN_VERSION}"


@pytest.fixture(scope="session", autouse=True)
def _preload_heavy_modules() -> None:
    """Pre-import heavy modules once per session to warm up the import cache.

    This reduces per-test overhead when running with pytest-xdist,
    as each worker only pays the import cost once at session start.
    """
    import black  # noqa: F401
    import inflect  # noqa: F401
    import isort  # noqa: F401

    import datamodel_code_generator  # noqa: F401


def validate_generated_code(
    code: str,
    file_path: str,
    *,
    do_exec: bool = False,
) -> None:
    """Validate generated code by compiling and optionally executing it.

    Args:
        code: The generated Python code to validate.
        file_path: Path to the file (for error reporting).
        do_exec: Whether to execute the code after compiling (default: False).
    """
    try:
        start = time.perf_counter()
        compiled = compile(code, file_path, "exec")
        _validation_stats.record_compile(time.perf_counter() - start)

        if do_exec:
            start = time.perf_counter()
            exec(compiled, {})
            _validation_stats.record_exec(time.perf_counter() - start)
    except SyntaxError as e:  # pragma: no cover
        _validation_stats.record_error(file_path, f"SyntaxError: {e}")
        raise
    except Exception as e:  # pragma: no cover
        _validation_stats.record_error(file_path, f"{type(e).__name__}: {e}")
        raise
