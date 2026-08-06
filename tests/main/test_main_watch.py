"""Tests for watch mode functionality."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, TextIO

import pytest

import datamodel_code_generator
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_output
from tests.main.conftest import (
    EXPECTED_MAIN_PATH,
    JSON_SCHEMA_DATA_PATH,
    assert_watchfiles_module,
    run_main_with_args,
    run_watch_and_assert,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from datamodel_code_generator.watch_dependencies import WatchDependencies

PROJECT_ROOT = Path(__file__).parents[2]
PACKAGE_ROOT = Path(datamodel_code_generator.__file__).parent
WATCH_DATA_PATH = PROJECT_ROOT / "tests/data/watch"
WATCH_CLI_TIMEOUT_SECONDS = 15.0
WATCH_CLI_STOP_TIMEOUT_SECONDS = 5.0
WATCH_CLI_READY_DELAY_SECONDS = 0.3
WATCH_CLI_CHANGE_RETRY_SECONDS = 0.75
WATCH_SCHEMA_INITIAL = """\
{
  "title": "WatchedPerson",
  "type": "object",
  "properties": {
    "name": {
      "type": "string"
    }
  },
  "required": [
    "name"
  ]
}
"""
WATCH_SCHEMA_CHANGED = """\
{
  "title": "WatchedPerson",
  "type": "object",
  "properties": {
    "name": {
      "type": "string"
    },
    "age": {
      "type": "integer"
    }
  },
  "required": [
    "name"
  ]
}
"""
WATCH_SCHEMA_INVALID = '{"title": "WatchedPerson",'
WATCH_GENERATION_ERROR = "generation error"


def _watch_cli_command(input_path: Path, output_path: Path, extra_args: list[str] | None = None) -> list[str]:
    command = [sys.executable]
    coverage_file = os.environ.get("COVERAGE_FILE", "")
    if coverage_file and "-nocov" not in coverage_file:
        command.extend([
            "-m",
            "coverage",
            "run",
            "--branch",
            "--concurrency=thread",
            "--parallel-mode",
            "--source",
            str(PACKAGE_ROOT),
        ])
    command.extend([
        "-m",
        "datamodel_code_generator",
        "--watch",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--watch-delay",
        "0.1",
        "--input-file-type",
        "jsonschema",
        "--formatters",
        "builtin",
        "--disable-timestamp",
    ])
    if extra_args:
        command.extend(extra_args)
    return command


def _collect_stream_lines(stream: TextIO, lines: list[str]) -> None:
    lines.extend(stream)


def _start_watch_cli(
    input_path: Path,
    output_path: Path,
    extra_args: list[str] | None = None,
    working_directory: Path = PROJECT_ROOT,
) -> tuple[subprocess.Popen[str], list[str], list[str], threading.Thread, threading.Thread]:
    environment = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "WATCHFILES_FORCE_POLLING": os.environ.get("WATCHFILES_FORCE_POLLING", "true"),
    }
    if working_directory != PROJECT_ROOT and (coverage_file := environment.get("COVERAGE_FILE")):
        coverage_path = Path(coverage_file)
        if not coverage_path.is_absolute():
            environment["COVERAGE_FILE"] = str((PROJECT_ROOT / coverage_path).resolve())
    process = subprocess.Popen(
        _watch_cli_command(input_path, output_path, extra_args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=working_directory,
        env=environment,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0,
    )
    if process.stdout is None or process.stderr is None:  # pragma: no cover
        pytest.fail("watch CLI process did not expose output streams")

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    stdout_thread = threading.Thread(
        target=_collect_stream_lines,
        args=(process.stdout, stdout_lines),
        name="watch-cli-stdout",
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_collect_stream_lines,
        args=(process.stderr, stderr_lines),
        name="watch-cli-stderr",
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    return process, stdout_lines, stderr_lines, stdout_thread, stderr_thread


def _stop_watch_cli(
    process: subprocess.Popen[str],
    stdout_thread: threading.Thread,
    stderr_thread: threading.Thread,
) -> None:
    if process.poll() is None:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=WATCH_CLI_STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=WATCH_CLI_STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=WATCH_CLI_STOP_TIMEOUT_SECONDS)
    stdout_thread.join(timeout=1.0)
    stderr_thread.join(timeout=1.0)


def _watch_cli_output(stdout_lines: list[str], stderr_lines: list[str]) -> str:
    return f"stdout:\n{''.join(stdout_lines)}\n\nstderr:\n{''.join(stderr_lines)}"


def _wait_for_watch_cli(
    process: subprocess.Popen[str],
    stdout_lines: list[str],
    stderr_lines: list[str],
    condition: Callable[[], bool],
    description: str,
) -> None:
    deadline = time.monotonic() + WATCH_CLI_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if condition():
            return
        if (return_code := process.poll()) is not None:
            pytest.fail(
                f"watch CLI exited with {return_code} before {description}\n"
                f"{_watch_cli_output(stdout_lines, stderr_lines)}"
            )
        time.sleep(0.05)
    pytest.fail(f"Timed out waiting for {description}\n{_watch_cli_output(stdout_lines, stderr_lines)}")


def _write_watch_cli_input_and_wait(
    process: subprocess.Popen[str],
    stdout_lines: list[str],
    stderr_lines: list[str],
    input_file: Path,
    content: str,
    condition: Callable[[], bool],
    description: str,
) -> None:
    last_write = 0.0
    input_file.write_text(content, encoding="utf-8")

    def condition_after_write() -> bool:
        nonlocal last_write

        if condition():
            return True

        now = time.monotonic()
        if now - last_write >= WATCH_CLI_CHANGE_RETRY_SECONDS:
            input_file.touch()
            last_write = now
        return False

    _wait_for_watch_cli(process, stdout_lines, stderr_lines, condition_after_write, description)


def _lines_contain(lines: list[str], expected_text: str) -> bool:
    return any(expected_text in line for line in lines)


def _file_contains(path: Path, expected_text: str) -> bool:
    if not path.is_file():
        return False
    return expected_text in path.read_text(encoding="utf-8")


def _record_failed_dependency(dependencies: WatchDependencies, path: Path) -> None:
    from datamodel_code_generator.watch_dependencies import record_local_dependency

    with dependencies.generation():
        record_local_dependency(path)
        raise RuntimeError(WATCH_GENERATION_ERROR)


def _start_watch_cli_until_ready(
    input_path: Path,
    output_path: Path,
    extra_args: list[str] | None = None,
    working_directory: Path = PROJECT_ROOT,
) -> tuple[subprocess.Popen[str], list[str], list[str], threading.Thread, threading.Thread]:
    if extra_args is None and working_directory == PROJECT_ROOT:
        process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli(input_path, output_path)
    else:
        process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli(
            input_path,
            output_path,
            extra_args,
            working_directory,
        )
    try:
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: _lines_contain(stdout_lines, "Watching "),
            "watch mode to start",
        )
        time.sleep(WATCH_CLI_READY_DELAY_SECONDS)
    except BaseException:
        _stop_watch_cli(process, stdout_thread, stderr_thread)
        raise
    return process, stdout_lines, stderr_lines, stdout_thread, stderr_thread


@pytest.mark.allow_direct_assert
def test_watch_cli_command_uses_coverage_for_coverage_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test watch CLI subprocess runs under coverage for coverage-enabled tox envs."""
    monkeypatch.setenv("COVERAGE_FILE", ".tox/.coverage.py314-parallel")

    command = _watch_cli_command(tmp_path / "schema.json", tmp_path / "output.py")

    assert command[1:8] == ["-m", "coverage", "run", "--branch", "--concurrency=thread", "--parallel-mode", "--source"]


@pytest.mark.allow_direct_assert
def test_watch_cli_command_skips_coverage_for_nocov_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test watch CLI subprocess skips coverage for no-cov tox envs."""
    monkeypatch.setenv("COVERAGE_FILE", ".tox/.coverage.py314-nocov-parallel")

    command = _watch_cli_command(tmp_path / "schema.json", tmp_path / "output.py")

    assert "coverage" not in command


@pytest.mark.allow_direct_assert
def test_watch_cli_resolves_relative_coverage_file_for_other_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test a watch subprocess keeps its coverage data at the project root."""
    project_root = tmp_path / "project"
    working_directory = tmp_path / "working-directory"
    project_root.mkdir()
    working_directory.mkdir()
    input_file = working_directory / "schema.json"
    output_file = working_directory / "output.py"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    coverage_file = ".coverage.watch-cli"
    monkeypatch.setattr(sys.modules[__name__], "PROJECT_ROOT", project_root)
    monkeypatch.setenv("COVERAGE_FILE", coverage_file)

    process, _stdout_lines, _stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        working_directory=working_directory,
    )
    _stop_watch_cli(process, stdout_thread, stderr_thread)

    assert list(project_root.glob(f"{coverage_file}.*"))
    assert not list(working_directory.glob(f"{coverage_file}.*"))


@pytest.mark.allow_direct_assert
def test_watch_cli_helpers_report_process_output(tmp_path: Path) -> None:
    """Test watch CLI helper predicates cover missing files and captured output."""
    output = _watch_cli_output(["out"], ["err"])
    assert output == "stdout:\nout\n\nstderr:\nerr"
    assert not _file_contains(tmp_path / "missing.py", "age")


def test_wait_for_watch_cli_reports_process_exit() -> None:
    """Test watch CLI waiting reports early process exits."""

    class ExitedProcess:
        def poll(self) -> int:
            return 7

    with pytest.raises(pytest.fail.Exception, match="exited with 7"):
        _wait_for_watch_cli(
            ExitedProcess(),  # ty: ignore[arg-type]
            ["started\n"],
            ["failed\n"],
            lambda: False,
            "ready",
        )


@pytest.mark.allow_direct_assert
def test_wait_for_watch_cli_reports_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test watch CLI waiting reports timeouts."""

    class RunningProcess:
        def poll(self) -> None:
            return None

    assert RunningProcess().poll() is None
    monkeypatch.setattr(sys.modules[__name__], "WATCH_CLI_TIMEOUT_SECONDS", -1.0)
    with pytest.raises(pytest.fail.Exception, match="Timed out"):
        _wait_for_watch_cli(
            RunningProcess(),  # ty: ignore[arg-type]
            [],
            [],
            lambda: False,
            "ready",
        )


@pytest.mark.allow_direct_assert
def test_stop_watch_cli_joins_threads_after_completed_process() -> None:
    """Test watch CLI cleanup joins stream reader threads after completed process."""

    class CompletedProcess:
        def poll(self) -> int:
            return 0

    class ThreadStub:
        def __init__(self) -> None:
            self.joined = False

        def join(self, *, timeout: float) -> None:
            self.joined = timeout == 1.0

    stdout_thread = ThreadStub()
    stderr_thread = ThreadStub()

    _stop_watch_cli(CompletedProcess(), stdout_thread, stderr_thread)  # ty: ignore[arg-type]

    assert stdout_thread.joined
    assert stderr_thread.joined


@pytest.mark.allow_direct_assert
def test_stop_watch_cli_sends_windows_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test watch CLI cleanup sends the Windows interrupt signal on Windows."""

    class RunningProcess:
        def __init__(self) -> None:
            self.sent_signal: int | None = None

        def poll(self) -> None:
            return None

        def send_signal(self, value: int) -> None:
            self.sent_signal = value

        @pytest.mark.allow_direct_assert
        def wait(self, *, timeout: float) -> None:
            assert timeout == WATCH_CLI_STOP_TIMEOUT_SECONDS

    class ThreadStub:
        @pytest.mark.allow_direct_assert
        def join(self, *, timeout: float) -> None:
            assert timeout == 1.0

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM, raising=False)
    process = RunningProcess()

    _stop_watch_cli(process, ThreadStub(), ThreadStub())  # ty: ignore[arg-type]

    assert process.sent_signal == signal.SIGTERM


@pytest.mark.allow_direct_assert
def test_stop_watch_cli_kills_after_repeated_timeouts() -> None:
    """Test watch CLI cleanup kills the subprocess when graceful stop times out."""
    expected_signal = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT

    class RunningProcess:
        def __init__(self) -> None:
            self.wait_calls = 0
            self.terminated = False
            self.killed = False

        def poll(self) -> None:
            return None

        @pytest.mark.allow_direct_assert
        def send_signal(self, value: int) -> None:
            assert value == expected_signal

        def wait(self, *, timeout: float) -> None:
            self.wait_calls += 1
            if self.wait_calls < 3:
                raise subprocess.TimeoutExpired(cmd="watch", timeout=timeout)

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

    class ThreadStub:
        @pytest.mark.allow_direct_assert
        def join(self, *, timeout: float) -> None:
            assert timeout == 1.0

    process = RunningProcess()

    _stop_watch_cli(process, ThreadStub(), ThreadStub())  # ty: ignore[arg-type]

    assert process.terminated
    assert process.killed


@pytest.mark.allow_direct_assert
def test_start_watch_cli_until_ready_stops_process_on_start_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test watch CLI startup cleanup runs when readiness wait fails."""

    class ProcessStub:
        pass

    class ThreadStub:
        pass

    stopped: list[ProcessStub] = []
    process = ProcessStub()
    stdout_thread = ThreadStub()
    stderr_thread = ThreadStub()

    @pytest.mark.allow_direct_assert
    def fake_start_watch_cli(
        input_path: Path, output_path: Path
    ) -> tuple[ProcessStub, list[str], list[str], ThreadStub, ThreadStub]:
        assert input_path.name == "schema.json"
        assert output_path.name == "output.py"
        return process, [], [], stdout_thread, stderr_thread

    @pytest.mark.allow_direct_assert
    def fake_wait_for_watch_cli(
        process_: ProcessStub,
        stdout_lines: list[str],
        stderr_lines: list[str],
        condition: Callable[[], bool],
        description: str,
    ) -> None:
        assert process_ is process
        assert not stdout_lines
        assert not stderr_lines
        assert description == "watch mode to start"
        assert not condition()
        raise KeyboardInterrupt

    @pytest.mark.allow_direct_assert
    def fake_stop_watch_cli(process_: ProcessStub, stdout_thread_: ThreadStub, stderr_thread_: ThreadStub) -> None:
        assert process_ is process
        assert stdout_thread_ is stdout_thread
        assert stderr_thread_ is stderr_thread
        stopped.append(process_)

    monkeypatch.setattr(sys.modules[__name__], "_start_watch_cli", fake_start_watch_cli)
    monkeypatch.setattr(sys.modules[__name__], "_wait_for_watch_cli", fake_wait_for_watch_cli)
    monkeypatch.setattr(sys.modules[__name__], "_stop_watch_cli", fake_stop_watch_cli)

    with pytest.raises(KeyboardInterrupt):
        _start_watch_cli_until_ready(Path("schema.json"), Path("output.py"))

    assert stopped == [process]


@pytest.mark.cli_doc(
    options=["--watch"],
    option_description="""Watch input file(s) for changes and regenerate output automatically.

The `--watch` flag enables continuous file monitoring mode. When enabled,
datamodel-codegen watches the input file or directory for changes and
automatically regenerates the output whenever changes are detected.
Press Ctrl+C to stop watching.

!!! warning "Requires extra dependency"

    The watch feature requires the `watch` extra:

    ```bash
    pip install 'datamodel-code-generator[watch]'
    ```""",
    input_schema="jsonschema/person.json",
    cli_args=["--watch", "--check"],
    expected_stdout="Error: --watch and --check cannot be used together",
    primary=True,
)
def test_watch_with_check_error(output_file: Path) -> None:
    """Watch mode cannot be used with --check mode.

    The `--watch` flag enables file watching for automatic regeneration.
    It cannot be combined with `--check` since check mode requires a single
    comparison, not continuous watching.
    """
    run_main_with_args(
        [
            "--watch",
            "--check",
            "--input",
            str(JSON_SCHEMA_DATA_PATH / "person.json"),
            "--output",
            str(output_file),
        ],
        expected_exit=Exit.ERROR,
    )


@pytest.mark.cli_doc(
    options=["--watch"],
    option_description="""Watch input file(s) for changes and regenerate output automatically.

The `--watch` flag monitors local files for changes. It requires a local file
path via `--input` and cannot be used with `--url` since remote URLs cannot
be watched for changes.""",
    cli_args=["--watch", "--url", "https://example.com/schema.json"],
    expected_stdout="Error: --watch requires --input file path",
)
def test_watch_with_url_error() -> None:
    """Watch mode requires a file path input, not a URL.

    The `--watch` flag monitors local files for changes. It cannot be used
    with `--url` since remote URLs cannot be watched for changes.
    """
    run_main_with_args(
        [
            "--watch",
            "--url",
            "https://example.com/schema.json",
        ],
        expected_exit=Exit.ERROR,
    )


def test_watch_without_input_error() -> None:
    """Watch mode requires --input file path."""
    run_main_with_args(
        ["--watch"],
        expected_exit=Exit.ERROR,
    )


def test_watch_without_watchfiles_installed(
    output_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error message when watchfiles is not installed."""
    monkeypatch.setitem(sys.modules, "watchfiles", None)
    run_main_with_args(
        [
            "--watch",
            "--input",
            str(JSON_SCHEMA_DATA_PATH / "person.json"),
            "--output",
            str(output_file),
        ],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="pip install",
    )


@pytest.mark.allow_direct_assert
def test_main_watch_uses_watch_module_import_seam(
    output_file: Path, mocker: pytest.MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test main resolves watch_and_regenerate through datamodel_code_generator.watch."""
    mock_generate = mocker.patch("datamodel_code_generator.__main__.run_generate_from_config", return_value=None)
    mock_watch = mocker.Mock(return_value=Exit.OK)
    watch_module = ModuleType("datamodel_code_generator.watch")
    watch_module.watch_and_regenerate = mock_watch
    monkeypatch.setitem(sys.modules, "datamodel_code_generator.watch", watch_module)

    run_main_with_args(
        [
            "--watch",
            "--input",
            str(JSON_SCHEMA_DATA_PATH / "person.json"),
            "--output",
            str(output_file),
        ],
    )

    mock_generate.assert_called_once()
    mock_watch.assert_called_once()
    config = mock_watch.call_args.args[0]
    assert config.watch is True
    assert config.input == JSON_SCHEMA_DATA_PATH / "person.json"


def test_get_watchfiles_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _get_watchfiles raises exception when watchfiles is not installed."""
    from datamodel_code_generator.watch import _get_watchfiles

    monkeypatch.setitem(sys.modules, "watchfiles", None)
    with pytest.raises(Exception, match="pip install"):
        _get_watchfiles()


def test_get_watchfiles_success() -> None:
    """Test _get_watchfiles returns watchfiles module when installed."""
    from datamodel_code_generator.watch import _get_watchfiles

    result = _get_watchfiles()
    assert_watchfiles_module(result)


@pytest.mark.cli_doc(
    options=["--watch", "--watch-delay"],
    option_description="""Set debounce delay in seconds for watch mode.

The `--watch-delay` option configures the debounce interval (default: 0.5 seconds)
for watch mode. This prevents multiple regenerations when files are rapidly
modified in succession. The delay ensures that after the last file change,
the generator waits the specified time before regenerating.

**Related:** [`--watch`](general-options.md#watch)""",
    input_schema="jsonschema/person.json",
    cli_args=["--watch", "--watch-delay", "1.5"],
    expected_stdout="Watching",
)
def test_watch_cli_regenerates_file_output_on_change(tmp_path: Path) -> None:
    """Watch mode regenerates file output when the input file changes.

    The `--watch` flag starts a file watcher that monitors the input file
    or directory for changes. The `--watch-delay` option sets the debounce
    delay in seconds (default: 0.5) to prevent multiple regenerations for
    rapid file changes. Press Ctrl+C to stop watching.
    """
    input_file = tmp_path / "schema.json"
    output_file = tmp_path / "output.py"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            input_file,
            WATCH_SCHEMA_CHANGED,
            lambda: _file_contains(output_file, "age: int | None = None"),
            "file output to be regenerated",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_file_change.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_cli_regenerates_for_consecutive_input_changes_without_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep one watcher subscription active across consecutive dependent-file updates."""
    file_change_data_path = WATCH_DATA_PATH / "file_change"
    input_file = tmp_path / "schema.json"
    output_file = tmp_path / "output.py"
    input_file.write_text((file_change_data_path / "initial.json").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("WATCHFILES_FORCE_POLLING", "false")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        ["--watch-delay", "0.05"],
    )

    try:
        time.sleep(WATCH_CLI_CHANGE_RETRY_SECONDS)
        completed_before_first_change = sum(line.strip() == "Done." for line in stdout_lines)
        first_update = tmp_path / "schema-first-update.json"
        first_update.write_text((file_change_data_path / "changed.json").read_text(encoding="utf-8"), encoding="utf-8")
        first_update.replace(input_file)
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: (
                _file_contains(output_file, "age: int | None = None")
                and sum(line.strip() == "Done." for line in stdout_lines) > completed_before_first_change
            ),
            "the first consecutive input change to regenerate",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_file_change.py")
        completed_before_second_change = sum(line.strip() == "Done." for line in stdout_lines)
        time.sleep(0.05)
        second_update = tmp_path / "schema-second-update.json"
        second_update.write_text((file_change_data_path / "initial.json").read_text(encoding="utf-8"), encoding="utf-8")
        second_update.replace(input_file)
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: (
                not _file_contains(output_file, "age: int | None = None")
                and sum(line.strip() == "Done." for line in stdout_lines) > completed_before_second_change
            ),
            "the second consecutive input change to regenerate without re-sending it",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_file_initial.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


@pytest.mark.skipif(os.name == "nt", reason="the lexical input fixture requires POSIX symlinks")
def test_watch_cli_regenerates_when_a_symlinked_input_is_repointed(tmp_path: Path) -> None:
    """Watch both the lexical input link and its resolved schema target."""
    file_change_data_path = WATCH_DATA_PATH / "file_change"
    first_input = tmp_path / "first" / "schema.json"
    second_input = tmp_path / "second" / "schema.json"
    input_link = tmp_path / "input.json"
    output_file = tmp_path / "output.py"
    first_input.parent.mkdir()
    second_input.parent.mkdir()
    first_input.write_text((file_change_data_path / "initial.json").read_text(encoding="utf-8"), encoding="utf-8")
    second_input.write_text((file_change_data_path / "changed.json").read_text(encoding="utf-8"), encoding="utf-8")
    input_link.symlink_to(first_input.relative_to(tmp_path))
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_link,
        output_file,
    )

    try:
        time.sleep(WATCH_CLI_CHANGE_RETRY_SECONDS)
        input_link.unlink()
        input_link.symlink_to(second_input.relative_to(tmp_path))
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: _file_contains(output_file, "age: int | None = None"),
            "the repointed symlink input to regenerate",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_file_change.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_and_regenerate_without_input() -> None:
    """Test watch_and_regenerate returns error when input is None."""
    from datamodel_code_generator.__main__ import Config

    config = Config(input=None)
    run_watch_and_assert(config, expected_exit=Exit.ERROR)


def test_watch_and_regenerate_handles_exhausted_watcher(mocker: pytest.MockerFixture) -> None:
    """Test watch_and_regenerate exits when the watcher iterator is exhausted."""
    from datamodel_code_generator.__main__ import Config

    mock_watchfiles = mocker.Mock()
    mock_watchfiles.watch.return_value = iter(())
    config = Config(input=str(JSON_SCHEMA_DATA_PATH / "person.json"))

    mocker.patch("datamodel_code_generator.watch._get_watchfiles", return_value=mock_watchfiles)
    run_watch_and_assert(config)


@pytest.mark.allow_direct_assert
def test_watch_dependency_paths_are_limited_to_generation_inputs(tmp_path: Path) -> None:
    """Dependency collection retains paths, not parsed source content or output files."""
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import _is_generated_output, _watch_filter
    from datamodel_code_generator.watch_dependencies import (
        WatchDependencies,
        _existing_file,
        _nearest_pyproject_toml,
        record_local_dependency,
        record_module_dependency,
    )

    input_file = tmp_path / "schema.json"
    config_file = tmp_path / "aliases.json"
    header_file = tmp_path / "header.txt"
    template_dir = tmp_path / "templates"
    output_dir = tmp_path / "models"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    config_file.write_text("{}", encoding="utf-8")
    header_file.write_text("# header", encoding="utf-8")
    template_dir.mkdir()
    output_dir.mkdir()
    referenced_file = tmp_path / "reference.json"
    referenced_file.write_text("{}", encoding="utf-8")

    dependencies = WatchDependencies()
    config = Config(
        input=input_file,
        output=output_dir,
        custom_file_header_path=header_file,
        custom_template_dir=template_dir,
    )
    dependencies.configure(config, config_values={"aliases": str(config_file)})
    with dependencies.generation():
        record_local_dependency(referenced_file)

    assert dependencies.files == frozenset({
        PROJECT_ROOT / "pyproject.toml",
        input_file,
        config_file,
        header_file,
        referenced_file,
    })
    assert dependencies.directories == frozenset({template_dir})
    watch_filter = _watch_filter(dependencies)
    assert not _is_generated_output(referenced_file, None)
    assert watch_filter(None, str(referenced_file))
    assert watch_filter(None, str(template_dir / "BaseModel.jinja2"))
    assert not watch_filter(None, str(output_dir / "model.py"))
    assert _existing_file("\0") is None
    assert _nearest_pyproject_toml(tmp_path) is None

    def custom_class_name_generator(name: str) -> str:
        return name

    callable_dependencies = WatchDependencies()
    callable_dependencies.configure(
        SimpleNamespace(
            input=input_file,
            output=None,
            custom_file_header_path=None,
            custom_template_dir=None,
            http_local_ref_path=None,
            custom_class_name_generator=custom_class_name_generator,
        ),
        config_values={},
    )
    assert Path(__file__) in callable_dependencies.files

    import py_compile
    from importlib.util import cache_from_source

    source_module = tmp_path / "custom_module.py"
    source_module.write_text("value = 1\n", encoding="utf-8")
    cached_module = Path(cache_from_source(str(source_module)))
    py_compile.compile(str(source_module), cfile=str(cached_module), doraise=True)
    module = ModuleType("custom_module")
    module.__file__ = str(cached_module)
    with callable_dependencies.generation():
        record_module_dependency(module)
    assert source_module in callable_dependencies.files
    assert record_module_dependency(ModuleType("built_in")) is None

    from datamodel_code_generator.format import CodeFormatter, Formatter, PythonVersionMin

    formatter_dependencies = WatchDependencies()
    with formatter_dependencies.generation():
        CodeFormatter(
            PythonVersionMin,
            custom_formatters=["tests.data.python.custom_formatters.add_comment"],
            formatters=[Formatter.BUILTIN],
        )
    assert PROJECT_ROOT / "tests/data/python/custom_formatters/add_comment.py" in formatter_dependencies.files

    from datamodel_code_generator.parser.protobuf import ProtobufParser

    proto_directory = tmp_path / "protos"
    proto_directory.mkdir()
    root_proto = proto_directory / "root.proto"
    child_proto = proto_directory / "child.proto"
    nested_proto = proto_directory / "nested.proto"
    root_proto.write_text('import "child.proto";\nimport "child.proto";\n', encoding="utf-8")
    child_proto.write_text('import "nested.proto";\n', encoding="utf-8")
    protobuf_dependencies = WatchDependencies()
    with protobuf_dependencies.generation():
        ProtobufParser._record_lexical_import_candidates(
            SimpleNamespace(config=SimpleNamespace(encoding="utf-8")),
            [root_proto],
            [tmp_path / "prepared", proto_directory],
        )
    assert child_proto in protobuf_dependencies.files
    assert nested_proto in protobuf_dependencies.files

    with pytest.raises(RuntimeError, match=WATCH_GENERATION_ERROR):
        _record_failed_dependency(dependencies, tmp_path / "attempted.json")

    assert referenced_file in dependencies.files
    assert tmp_path / "attempted.json" in dependencies.files


@pytest.mark.allow_direct_assert
def test_watch_dependencies_ignore_unexpandable_config_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """An OS error while expanding an optional path keeps it out of the dependency graph."""
    from datamodel_code_generator.watch_dependencies import _existing_file

    original_expanduser = Path.expanduser
    msg = "unexpandable"

    def raise_expansion_error(path: Path) -> Path:
        if path == Path("unexpandable.json"):
            raise OSError(msg)
        return original_expanduser(path)

    monkeypatch.setattr(Path, "expanduser", raise_expansion_error)

    assert _existing_file("unexpandable.json") is None


@pytest.mark.allow_direct_assert
def test_watch_dependencies_skip_unreadable_protobuf_import(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A discovered lexical protobuf import may disappear before it can be read."""
    from datamodel_code_generator.parser.protobuf import ProtobufParser
    from datamodel_code_generator.watch_dependencies import WatchDependencies

    root_proto = tmp_path / "root.proto"
    unreadable_proto = tmp_path / "unreadable.proto"
    root_proto.write_text('import "unreadable.proto";\n', encoding="utf-8")
    unreadable_proto.write_text('syntax = "proto3";\n', encoding="utf-8")
    original_read_text = Path.read_text
    msg = "unreadable"

    def raise_read_error(path: Path, *args: object, **kwargs: object) -> str:
        if path == unreadable_proto:
            raise OSError(msg)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", raise_read_error)
    dependencies = WatchDependencies()
    with dependencies.generation():
        ProtobufParser._record_lexical_import_candidates(
            SimpleNamespace(config=SimpleNamespace(encoding="utf-8")),
            [root_proto],
            [tmp_path / "prepared", tmp_path],
        )

    assert unreadable_proto in dependencies.files


@pytest.mark.allow_direct_assert
def test_watch_with_no_collected_dependencies_stops_cleanly(tmp_path: Path) -> None:
    """An empty dependency graph does not leave an idle watch loop behind."""
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import watch_and_regenerate
    from datamodel_code_generator.watch_dependencies import WatchDependencies

    input_file = tmp_path / "schema.json"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")

    assert (
        watch_and_regenerate(
            Config(input=input_file),
            dependencies=WatchDependencies(),
            regenerate=lambda: Exit.OK,
        )
        == Exit.OK
    )


def test_watch_cli_regenerates_directory_output_on_change(tmp_path: Path) -> None:
    """Watch mode regenerates package output when a schema directory changes."""
    input_dir = tmp_path / "schemas"
    input_dir.mkdir()
    input_file = input_dir / "schema.json"
    output_dir = tmp_path / "models"
    output_file = output_dir / "schema.py"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_dir,
        output_dir,
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            input_file,
            WATCH_SCHEMA_CHANGED,
            lambda: _file_contains(output_file, "age: int | None = None"),
            "directory output to be regenerated",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_file_change.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_cli_regenerates_on_nested_reference_change(tmp_path: Path) -> None:
    """Watch mode fully regenerates after an external local ``$ref`` changes."""
    schema_dir = tmp_path / "schemas"
    shutil.copytree(WATCH_DATA_PATH / "nested_ref", schema_dir)
    input_file = schema_dir / "root.json"
    referenced_file = schema_dir / "child.json"
    output_file = tmp_path / "output.py"
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            referenced_file,
            (schema_dir / "child_changed.json").read_text(encoding="utf-8"),
            lambda: _file_contains(output_file, "age: int | None = None"),
            "nested reference output to be regenerated",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_nested_ref_change.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_cli_regenerates_on_xmlschema_include_change(tmp_path: Path) -> None:
    """Watch mode fully regenerates after an included XML Schema changes."""
    schema_dir = tmp_path / "schemas"
    shutil.copytree(WATCH_DATA_PATH / "xmlschema_include", schema_dir)
    input_file = schema_dir / "root.xsd"
    included_file = schema_dir / "child.xsd"
    output_file = tmp_path / "output.py"
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        ["--input-file-type", "xmlschema"],
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            included_file,
            (schema_dir / "child_changed.xsd").read_text(encoding="utf-8"),
            lambda: _file_contains(output_file, "age: conint(ge=-2147483648, le=2147483647) | None = None"),
            "included XML Schema output to be regenerated",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_xmlschema_include_change.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


@pytest.mark.skipif(find_spec("grpc_tools") is None, reason="requires the protobuf extra")
def test_watch_cli_regenerates_on_protobuf_import_change(tmp_path: Path) -> None:
    """Watch mode fully regenerates after an imported Protocol Buffers file changes."""
    schema_dir = tmp_path / "schemas"
    shutil.copytree(WATCH_DATA_PATH / "protobuf_import", schema_dir)
    input_file = schema_dir / "root.proto"
    imported_file = schema_dir / "child.proto"
    output_file = tmp_path / "output.py"
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        ["--input-file-type", "protobuf"],
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            imported_file,
            (schema_dir / "child_changed.proto").read_text(encoding="utf-8"),
            lambda: _file_contains(output_file, "age: int | None = 0"),
            "imported Protocol Buffers output to be regenerated",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_protobuf_import_change.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


@pytest.mark.skipif(find_spec("grpc_tools") is None, reason="requires the protobuf extra")
def test_watch_cli_recovers_when_an_existing_protobuf_import_adds_a_missing_nested_import(tmp_path: Path) -> None:
    """A failed protoc run retains lexical nested-import candidates for a later create event."""
    schema_dir = tmp_path / "schemas"
    shutil.copytree(WATCH_DATA_PATH / "protobuf_import", schema_dir)
    input_file = schema_dir / "root.proto"
    imported_file = schema_dir / "child.proto"
    missing_import = schema_dir / "nested" / "later.proto"
    output_file = tmp_path / "output.py"
    child_content = (schema_dir / "child_changed.proto").read_text(encoding="utf-8")
    imported_file.write_text(child_content, encoding="utf-8")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        ["--input-file-type", "protobuf"],
    )

    try:
        child_with_missing_import = child_content.replace(
            "\n\nmessage Child",
            '\nimport "nested/later.proto";\n\nmessage Child',
        )
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            imported_file,
            child_with_missing_import,
            lambda: _lines_contain(stderr_lines, "Invalid Protocol Buffers schema"),
            "the missing nested protobuf import to fail",
        )
        completed_before_create = sum(line.strip() == "Done." for line in stdout_lines)
        missing_import.parent.mkdir()
        missing_import.write_text('syntax = "proto3";\n', encoding="utf-8")
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: sum(line.strip() == "Done." for line in stdout_lines) > completed_before_create,
            "the newly created nested protobuf import to recover generation",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_protobuf_import_change.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_cli_regenerates_on_custom_header_change(tmp_path: Path) -> None:
    """Watch mode reloads a configured custom header without watching generated output."""
    input_file = tmp_path / "schema.json"
    header_file = tmp_path / "header.txt"
    output_file = tmp_path / "output.py"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    header_file.write_text("# first header", encoding="utf-8")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        ["--custom-file-header-path", str(header_file)],
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            header_file,
            "# updated header",
            lambda: _file_contains(output_file, "# updated header"),
            "custom header output to be regenerated",
        )
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_cli_regenerates_on_top_level_custom_template_change(tmp_path: Path) -> None:
    """Watch mode clears cached custom templates before a full regeneration."""
    input_dir = tmp_path / "schemas"
    template_dir = tmp_path / "external" / "templates"
    input_file = input_dir / "schema.json"
    template_file = template_dir / "BaseModel.jinja2"
    output_file = tmp_path / "output.py"
    input_dir.mkdir()
    template_dir.mkdir(parents=True)
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    shutil.copyfile(WATCH_DATA_PATH / "custom_templates/initial/BaseModel.jinja2", template_file)
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        ["--custom-template-dir", str(template_dir)],
    )

    try:
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: _file_contains(output_file, 'template_revision = "initial"'),
            "initial custom template output",
        )
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            template_file,
            (WATCH_DATA_PATH / "custom_templates/changed/BaseModel.jinja2").read_text(encoding="utf-8"),
            lambda: _file_contains(output_file, 'template_revision = "changed"'),
            "custom template output to be regenerated",
        )
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_cli_regenerates_when_external_custom_template_directory_is_created_and_recreated(
    tmp_path: Path,
) -> None:
    """Watch mode retains missing configured directories by watching their existing parent."""
    input_dir = tmp_path / "schemas"
    external_dir = tmp_path / "external"
    template_dir = external_dir / "templates"
    input_file = input_dir / "schema.json"
    template_file = template_dir / "BaseModel.jinja2"
    output_file = tmp_path / "output.py"
    input_dir.mkdir()
    external_dir.mkdir()
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        ["--custom-template-dir", str(template_dir)],
    )

    try:
        template_dir.mkdir()
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            template_file,
            (WATCH_DATA_PATH / "custom_templates/initial/BaseModel.jinja2").read_text(encoding="utf-8"),
            lambda: _file_contains(output_file, 'template_revision = "initial"'),
            "created custom template directory output to be regenerated",
        )
        shutil.rmtree(template_dir)
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: output_file.is_file() and not _file_contains(output_file, 'template_revision = "initial"'),
            "deleted custom template directory output to be regenerated",
        )
        template_dir.mkdir()
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            template_file,
            (WATCH_DATA_PATH / "custom_templates/changed/BaseModel.jinja2").read_text(encoding="utf-8"),
            lambda: _file_contains(output_file, 'template_revision = "changed"'),
            "recreated custom template directory output to be regenerated",
        )
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_cli_regenerates_on_alias_configuration_change(tmp_path: Path) -> None:
    """Watch mode resolves a JSON-backed alias configuration again after it changes."""
    input_file = tmp_path / "schema.json"
    aliases_file = tmp_path / "aliases.json"
    output_file = tmp_path / "output.py"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    aliases_file.write_text('{"name": "first_name"}\n', encoding="utf-8")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        ["--aliases", str(aliases_file)],
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            aliases_file,
            '{"name": "updated_name"}\n',
            lambda: _file_contains(output_file, "updated_name: str"),
            "alias configuration output to be regenerated",
        )
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_cli_reloads_pyproject_configuration(tmp_path: Path) -> None:
    """Watch mode resolves the command again after its pyproject.toml changes."""
    input_file = tmp_path / "schema.json"
    output_file = tmp_path / "output.py"
    pyproject_file = tmp_path / "pyproject.toml"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    pyproject_file.write_text("[tool.datamodel-codegen]\nclass-name = 'FirstModel'\n", encoding="utf-8")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        working_directory=tmp_path,
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            pyproject_file,
            "[tool.datamodel-codegen]\nclass-name = 'UpdatedModel'\n",
            lambda: _file_contains(output_file, "class UpdatedModel(BaseModel):"),
            "pyproject configuration output to be regenerated",
        )
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


def test_watch_and_regenerate_handles_keyboard_interrupt(mocker: pytest.MockerFixture) -> None:
    """Test that watch_and_regenerate handles KeyboardInterrupt gracefully."""
    from datamodel_code_generator.__main__ import Config

    mock_watchfiles = mocker.Mock()
    mock_watchfiles.watch.side_effect = KeyboardInterrupt()
    config = Config(input=str(JSON_SCHEMA_DATA_PATH / "person.json"))

    mocker.patch("datamodel_code_generator.watch._get_watchfiles", return_value=mock_watchfiles)
    run_watch_and_assert(config)


def test_watch_and_regenerate_propagates_watcher_exception(mocker: pytest.MockerFixture) -> None:
    """Surface watcher-thread failures to the watch caller."""
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import watch_and_regenerate

    mock_watchfiles = mocker.Mock()
    mock_watchfiles.watch.side_effect = RuntimeError("watcher failed")
    config = Config(input=str(JSON_SCHEMA_DATA_PATH / "person.json"))

    mocker.patch("datamodel_code_generator.watch._get_watchfiles", return_value=mock_watchfiles)
    with pytest.raises(RuntimeError, match="watcher failed"):
        watch_and_regenerate(config, regenerate=lambda: Exit.OK)


@pytest.mark.parametrize("add_catch_up_template_root", [False, True], ids=["unchanged-roots", "changed-roots"])
def test_watch_cli_catches_up_changes_queued_while_restarting_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    add_catch_up_template_root: bool,
) -> None:
    """A retiring watcher retains an input event while dependency roots are restarted."""
    file_change_data_path = WATCH_DATA_PATH / "file_change"
    project_directory = tmp_path / "project"
    formatter_directory = tmp_path / "formatter"
    template_directory = tmp_path / "templates"
    input_file = project_directory / "schema.json"
    output_file = project_directory / "output.py"
    pyproject_file = project_directory / "pyproject.toml"
    formatter_file = formatter_directory / "blocking_formatter.py"
    marker_file = tmp_path / "formatter-started"
    release_file = tmp_path / "formatter-release"
    project_directory.mkdir()
    formatter_directory.mkdir()
    template_directory.mkdir()
    input_file.write_text((file_change_data_path / "initial.json").read_text(encoding="utf-8"), encoding="utf-8")
    pyproject_file.write_text("[tool.datamodel-codegen]\n", encoding="utf-8")
    shutil.copyfile(WATCH_DATA_PATH.parent / "python/custom_formatters/blocking_watch.py", formatter_file)
    previous_python_path = os.environ.get("PYTHONPATH")
    monkeypatch.setenv(
        "PYTHONPATH",
        str(formatter_directory)
        if previous_python_path is None
        else f"{formatter_directory}{os.pathsep}{previous_python_path}",
    )
    monkeypatch.setenv("DATAMODEL_CODEGEN_WATCH_MARKER", str(marker_file))
    monkeypatch.setenv("DATAMODEL_CODEGEN_WATCH_RELEASE", str(release_file))
    monkeypatch.setenv("DATAMODEL_CODEGEN_WATCH_BLOCK_TIMEOUT", "5")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
        working_directory=project_directory,
    )

    try:
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_file_initial.py")
        time.sleep(WATCH_CLI_CHANGE_RETRY_SECONDS)
        pyproject_update = project_directory / "pyproject-update.toml"
        pyproject_update.write_text(
            '[tool.datamodel-codegen]\ncustom-formatters = "blocking_formatter"\n',
            encoding="utf-8",
        )
        pyproject_update.replace(pyproject_file)
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            marker_file.is_file,
            "the custom formatter to begin the root-changing regeneration",
        )
        input_file.write_text((file_change_data_path / "changed.json").read_text(encoding="utf-8"), encoding="utf-8")
        if add_catch_up_template_root:
            caught_up_pyproject = project_directory / "pyproject-catchup.toml"
            caught_up_pyproject.write_text(
                "\n".join([
                    "[tool.datamodel-codegen]",
                    'custom-formatters = "blocking_formatter"',
                    f'custom-template-dir = "{template_directory.as_posix()}"',
                    "",
                ]),
                encoding="utf-8",
            )
            caught_up_pyproject.replace(pyproject_file)
        time.sleep(0.2)
        release_file.touch()
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: (
                _file_contains(output_file, "age: int | None = None")
                and _lines_contain(stdout_lines, "Detected changes while restarting the watcher")
            ),
            "the queued input change to be caught up after the watcher restart",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_file_change.py")
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)


@pytest.mark.allow_direct_assert
def test_watch_dependencies_handle_path_resolution_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Defensive path resolution falls back to the lexical path."""
    from datamodel_code_generator.watch_dependencies import _logical_working_directory, _path_variants

    unresolved_path = tmp_path / "unresolved.json"
    original_resolve = Path.resolve
    original_samefile = Path.samefile
    resolution_error = "unresolvable"
    unresolvable_paths = (unresolved_path, unresolved_path.parent)

    def raise_resolution_error(path: Path, *args: object, **kwargs: object) -> Path:
        if path in unresolvable_paths:
            raise OSError(resolution_error)
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", raise_resolution_error)
    assert _path_variants(unresolved_path) == frozenset({unresolved_path})

    def raise_samefile_error(_path: Path, _other: Path) -> bool:
        raise OSError(resolution_error)

    monkeypatch.setattr(Path, "samefile", raise_samefile_error)
    assert _logical_working_directory() == Path.cwd()
    monkeypatch.setattr(Path, "samefile", original_samefile)


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX symlinks")
@pytest.mark.allow_direct_assert
def test_watch_dependencies_track_symlink_parent_events(tmp_path: Path) -> None:
    """Directory events from symlink replacement remain part of the graph."""
    from datamodel_code_generator.watch_dependencies import WatchDependencies

    source_file = tmp_path / "source.json"
    source_directory = tmp_path / "templates-source"
    file_link = tmp_path / "schema.json"
    directory_link = tmp_path / "templates"
    source_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    source_directory.mkdir()
    file_link.symlink_to(source_file.name)
    directory_link.symlink_to(source_directory.name)
    dependencies = WatchDependencies()
    dependencies.add_file(file_link)
    dependencies.add_directory(directory_link)
    with dependencies.generation():
        dependencies.record_file(file_link)

    assert dependencies.includes(file_link.parent)


def test_watch_cli_reports_generation_error_after_change(tmp_path: Path) -> None:
    """Watch mode reports generation errors after a watched file change."""
    input_file = tmp_path / "schema.json"
    output_file = tmp_path / "output.py"
    input_file.write_text(WATCH_SCHEMA_INITIAL, encoding="utf-8")
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli_until_ready(
        input_file,
        output_file,
    )

    try:
        _write_watch_cli_input_and_wait(
            process,
            stdout_lines,
            stderr_lines,
            input_file,
            WATCH_SCHEMA_INVALID,
            lambda: _lines_contain(stderr_lines, "Error:"),
            "generation error to be reported",
        )
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)
