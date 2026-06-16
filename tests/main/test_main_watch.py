"""Tests for watch mode functionality."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import ModuleType
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

PROJECT_ROOT = Path(__file__).parents[2]
PACKAGE_ROOT = Path(datamodel_code_generator.__file__).parent
WATCH_CLI_TIMEOUT_SECONDS = 15.0
WATCH_CLI_STOP_TIMEOUT_SECONDS = 5.0
WATCH_CLI_READY_DELAY_SECONDS = 0.3
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


def _watch_cli_command(input_path: Path, output_path: Path) -> list[str]:
    command = [sys.executable]
    coverage_file = os.environ.get("COVERAGE_FILE", "")
    if coverage_file and "-nocov" not in coverage_file:
        command.extend(["-m", "coverage", "run", "--parallel-mode", "--source", str(PACKAGE_ROOT)])
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
    return command


def _collect_stream_lines(stream: TextIO, lines: list[str]) -> None:
    lines.extend(stream)


def _start_watch_cli(
    input_path: Path,
    output_path: Path,
) -> tuple[subprocess.Popen[str], list[str], list[str], threading.Thread, threading.Thread]:
    process = subprocess.Popen(
        _watch_cli_command(input_path, output_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
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


def _lines_contain(lines: list[str], expected_text: str) -> bool:
    return any(expected_text in line for line in lines)


def _file_contains(path: Path, expected_text: str) -> bool:
    if not path.is_file():
        return False
    return expected_text in path.read_text(encoding="utf-8")


def _start_watch_cli_until_ready(
    input_path: Path,
    output_path: Path,
) -> tuple[subprocess.Popen[str], list[str], list[str], threading.Thread, threading.Thread]:
    process, stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_watch_cli(input_path, output_path)
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

    assert command[1:6] == ["-m", "coverage", "run", "--parallel-mode", "--source"]


@pytest.mark.allow_direct_assert
def test_watch_cli_command_skips_coverage_for_nocov_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test watch CLI subprocess skips coverage for no-cov tox envs."""
    monkeypatch.setenv("COVERAGE_FILE", ".tox/.coverage.py314-nocov-parallel")

    command = _watch_cli_command(tmp_path / "schema.json", tmp_path / "output.py")

    assert "coverage" not in command


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
    mocker: pytest.MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test error message when watchfiles is not installed."""
    mocker.patch.dict("sys.modules", {"watchfiles": None})
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
def test_main_watch_uses_watch_module_import_seam(output_file: Path, mocker: pytest.MockerFixture) -> None:
    """Test main resolves watch_and_regenerate through datamodel_code_generator.watch."""
    mock_generate = mocker.patch("datamodel_code_generator.__main__.run_generate_from_config", return_value=None)
    mock_watch = mocker.Mock(return_value=Exit.OK)
    watch_module = ModuleType("datamodel_code_generator.watch")
    watch_module.watch_and_regenerate = mock_watch
    mocker.patch.dict(sys.modules, {"datamodel_code_generator.watch": watch_module})

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


def test_get_watchfiles_import_error(mocker: pytest.MockerFixture) -> None:
    """Test _get_watchfiles raises exception when watchfiles is not installed."""
    from datamodel_code_generator.watch import _get_watchfiles

    mocker.patch.dict("sys.modules", {"watchfiles": None})
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
        input_file.write_text(WATCH_SCHEMA_CHANGED, encoding="utf-8")
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: _file_contains(output_file, "age: int | None = None"),
            "file output to be regenerated",
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
        input_file.write_text(WATCH_SCHEMA_CHANGED, encoding="utf-8")
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: _file_contains(output_file, "age: int | None = None"),
            "directory output to be regenerated",
        )
        assert_output(output_file.read_text(encoding="utf-8"), EXPECTED_MAIN_PATH / "watch_file_change.py")
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
        input_file.write_text(WATCH_SCHEMA_INVALID, encoding="utf-8")
        _wait_for_watch_cli(
            process,
            stdout_lines,
            stderr_lines,
            lambda: _lines_contain(stderr_lines, "Error:"),
            "generation error to be reported",
        )
    finally:
        _stop_watch_cli(process, stdout_thread, stderr_thread)
