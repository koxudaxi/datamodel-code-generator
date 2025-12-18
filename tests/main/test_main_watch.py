"""Tests for watch mode functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from datamodel_code_generator.__main__ import Exit
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, run_main_with_args

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.cli_doc(
    options=["--watch"],
    input_schema="jsonschema/person.json",
    cli_args=["--watch", "--check"],
    expected_stdout="Error: --watch and --check cannot be used together",
)
def test_watch_with_check_error(output_file: Path) -> None:
    """Watch mode cannot be used with --check mode.

    The `--watch` flag enables file watching for automatic regeneration.
    It cannot be combined with `--check` since check mode requires a single
    comparison, not continuous watching.
    """
    return_code = run_main_with_args(
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
    assert return_code == Exit.ERROR


@pytest.mark.cli_doc(
    options=["--watch"],
    cli_args=["--watch", "--url", "https://example.com/schema.json"],
    expected_stdout="Error: --watch requires --input file path",
)
def test_watch_with_url_error() -> None:
    """Watch mode requires a file path input, not a URL.

    The `--watch` flag monitors local files for changes. It cannot be used
    with `--url` since remote URLs cannot be watched for changes.
    """
    return_code = run_main_with_args(
        [
            "--watch",
            "--url",
            "https://example.com/schema.json",
        ],
        expected_exit=Exit.ERROR,
    )
    assert return_code == Exit.ERROR


def test_watch_without_input_error(mocker: pytest.MockerFixture) -> None:
    """Watch mode requires --input file path."""
    mocker.patch("sys.stdin.isatty", return_value=False)
    mocker.patch("sys.stdin.read", return_value='{"type": "object"}')
    return_code = run_main_with_args(
        ["--watch"],
        expected_exit=Exit.ERROR,
    )
    assert return_code == Exit.ERROR


def test_watch_without_watchfiles_installed(output_file: Path, mocker: pytest.MockerFixture) -> None:
    """Test error message when watchfiles is not installed."""
    mocker.patch.dict("sys.modules", {"watchfiles": None})
    mocker.patch(
        "datamodel_code_generator.watch._get_watchfiles",
        side_effect=Exception("Please run `pip install 'datamodel-code-generator[watch]'` to use watch mode"),
    )
    return_code = run_main_with_args(
        [
            "--watch",
            "--input",
            str(JSON_SCHEMA_DATA_PATH / "person.json"),
            "--output",
            str(output_file),
        ],
        expected_exit=Exit.ERROR,
    )
    assert return_code == Exit.ERROR


def test_get_watchfiles_import_error() -> None:
    """Test _get_watchfiles raises exception when watchfiles is not installed."""
    from datamodel_code_generator.watch import _get_watchfiles

    with patch.dict("sys.modules", {"watchfiles": None}), pytest.raises(Exception, match="pip install"):
        _get_watchfiles()


def test_get_watchfiles_success() -> None:
    """Test _get_watchfiles returns watchfiles module when installed."""
    from datamodel_code_generator.watch import _get_watchfiles

    result = _get_watchfiles()
    assert result is not None
    assert hasattr(result, "watch")


@pytest.mark.cli_doc(
    options=["--watch", "--watch-delay"],
    input_schema="jsonschema/person.json",
    cli_args=["--watch", "--watch-delay", "1.5"],
    expected_stdout="Watching",
)
def test_watch_and_regenerate_starts_and_stops() -> None:
    """Watch mode starts file watcher and handles clean exit.

    The `--watch` flag starts a file watcher that monitors the input file
    or directory for changes. The `--watch-delay` option sets the debounce
    delay in seconds (default: 0.5) to prevent multiple regenerations for
    rapid file changes. Press Ctrl+C to stop watching.
    """
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import watch_and_regenerate

    mock_watchfiles = MagicMock()
    mock_watchfiles.watch.return_value = iter([])
    config = Config(input=str(JSON_SCHEMA_DATA_PATH / "person.json"), watch_delay=0.5)

    with patch(
        "datamodel_code_generator.watch._get_watchfiles",
        return_value=mock_watchfiles,
    ):
        result = watch_and_regenerate(config, None, None, None)
        assert result == Exit.OK
        mock_watchfiles.watch.assert_called_once()
        call_kwargs = mock_watchfiles.watch.call_args.kwargs
        assert call_kwargs.get("debounce") == 500
        assert call_kwargs.get("recursive") is False


def test_watch_and_regenerate_without_input() -> None:
    """Test watch_and_regenerate returns error when input is None."""
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import watch_and_regenerate

    mock_watchfiles = MagicMock()
    config = Config(input=None)

    with patch(
        "datamodel_code_generator.watch._get_watchfiles",
        return_value=mock_watchfiles,
    ):
        result = watch_and_regenerate(config, None, None, None)
        assert result == Exit.ERROR


def test_watch_and_regenerate_with_directory() -> None:
    """Test that watch_and_regenerate handles directory input with recursive watching."""
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import watch_and_regenerate

    mock_watchfiles = MagicMock()
    mock_watchfiles.watch.return_value = iter([])
    config = Config(input=str(JSON_SCHEMA_DATA_PATH), watch_delay=0.1)

    with patch(
        "datamodel_code_generator.watch._get_watchfiles",
        return_value=mock_watchfiles,
    ):
        result = watch_and_regenerate(config, None, None, None)
        assert result == Exit.OK
        call_kwargs = mock_watchfiles.watch.call_args.kwargs
        assert call_kwargs.get("recursive") is True


def test_watch_and_regenerate_handles_keyboard_interrupt() -> None:
    """Test that watch_and_regenerate handles KeyboardInterrupt gracefully."""
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import watch_and_regenerate

    mock_watchfiles = MagicMock()
    mock_watchfiles.watch.side_effect = KeyboardInterrupt()
    config = Config(input=str(JSON_SCHEMA_DATA_PATH / "person.json"))

    with patch(
        "datamodel_code_generator.watch._get_watchfiles",
        return_value=mock_watchfiles,
    ):
        result = watch_and_regenerate(config, None, None, None)
        assert result == Exit.OK


def test_watch_and_regenerate_on_change(tmp_path: Path) -> None:
    """Test that watch_and_regenerate calls generate on file change."""
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import watch_and_regenerate

    output_file = tmp_path / "output.py"
    mock_watchfiles = MagicMock()
    mock_watchfiles.watch.return_value = iter([
        {("modified", str(JSON_SCHEMA_DATA_PATH / "person.json"))},
    ])
    config = Config(
        input=str(JSON_SCHEMA_DATA_PATH / "person.json"),
        output=output_file,
    )
    mock_generate = MagicMock()

    with (
        patch(
            "datamodel_code_generator.watch._get_watchfiles",
            return_value=mock_watchfiles,
        ),
        patch(
            "datamodel_code_generator.__main__.run_generate_from_config",
            mock_generate,
        ),
    ):
        result = watch_and_regenerate(config, None, None, None)
        assert result == Exit.OK
        mock_generate.assert_called_once()


def test_watch_and_regenerate_handles_generation_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that watch_and_regenerate continues after generation error."""
    from datamodel_code_generator.__main__ import Config
    from datamodel_code_generator.watch import watch_and_regenerate

    mock_watchfiles = MagicMock()
    mock_watchfiles.watch.return_value = iter([
        {("modified", str(JSON_SCHEMA_DATA_PATH / "person.json"))},
    ])
    config = Config(input=str(JSON_SCHEMA_DATA_PATH / "person.json"))

    with (
        patch(
            "datamodel_code_generator.watch._get_watchfiles",
            return_value=mock_watchfiles,
        ),
        patch(
            "datamodel_code_generator.__main__.run_generate_from_config",
            side_effect=Exception("Generation failed"),
        ),
    ):
        result = watch_and_regenerate(config, None, None, None)
        assert result == Exit.OK
        captured = capsys.readouterr()
        assert "Generation failed" in captured.err
