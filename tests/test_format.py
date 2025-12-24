"""Tests for code formatting functionality."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

from datamodel_code_generator.format import CodeFormatter, Formatter, PythonVersion, PythonVersionMin

EXAMPLE_LICENSE_FILE = str(Path(__file__).parent / "data/python/custom_formatters/license_example.txt")

UN_EXIST_FORMATTER = "tests.data.python.custom_formatters.un_exist"
WRONG_FORMATTER = "tests.data.python.custom_formatters.wrong"
NOT_SUBCLASS_FORMATTER = "tests.data.python.custom_formatters.not_subclass"
ADD_COMMENT_FORMATTER = "tests.data.python.custom_formatters.add_comment"
ADD_LICENSE_FORMATTER = "tests.data.python.custom_formatters.add_license"


def test_python_version() -> None:
    """Ensure that the python version used for the tests is properly listed."""
    _ = PythonVersion("{}.{}".format(*sys.version_info[:2]))


def test_python_version_has_native_deferred_annotations() -> None:
    """Test that has_native_deferred_annotations returns correct values for each Python version."""
    assert not PythonVersion.PY_310.has_native_deferred_annotations
    assert not PythonVersion.PY_311.has_native_deferred_annotations
    assert not PythonVersion.PY_312.has_native_deferred_annotations
    assert not PythonVersion.PY_313.has_native_deferred_annotations
    assert PythonVersion.PY_314.has_native_deferred_annotations


@pytest.mark.parametrize(
    ("skip_string_normalization", "expected_output"),
    [
        (True, "a = 'b'"),
        (False, 'a = "b"'),
    ],
)
def test_format_code_with_skip_string_normalization(
    skip_string_normalization: bool,
    expected_output: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test code formatting with skip string normalization option."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(PythonVersionMin, skip_string_normalization=skip_string_normalization)

    formatted_code = formatter.format_code("a = 'b'")

    assert formatted_code == expected_output + "\n"


def test_format_code_un_exist_custom_formatter() -> None:
    """Test error when custom formatter module doesn't exist."""
    with pytest.raises(ModuleNotFoundError):
        _ = CodeFormatter(
            PythonVersionMin,
            custom_formatters=[UN_EXIST_FORMATTER],
        )


def test_format_code_invalid_formatter_name() -> None:
    """Test error when custom formatter has no CodeFormatter class."""
    with pytest.raises(NameError):
        _ = CodeFormatter(
            PythonVersionMin,
            custom_formatters=[WRONG_FORMATTER],
        )


def test_format_code_is_not_subclass() -> None:
    """Test error when custom formatter doesn't inherit CustomCodeFormatter."""
    with pytest.raises(TypeError):
        _ = CodeFormatter(
            PythonVersionMin,
            custom_formatters=[NOT_SUBCLASS_FORMATTER],
        )


def test_format_code_with_custom_formatter_without_kwargs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test custom formatter that doesn't require kwargs."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        custom_formatters=[ADD_COMMENT_FORMATTER],
    )

    formatted_code = formatter.format_code("x = 1\ny = 2")

    assert formatted_code == "# a comment\nx = 1\ny = 2" + "\n"


def test_format_code_with_custom_formatter_with_kwargs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test custom formatter with kwargs."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        custom_formatters=[ADD_LICENSE_FORMATTER],
        custom_formatters_kwargs={"license_file": EXAMPLE_LICENSE_FILE},
    )

    formatted_code = formatter.format_code("x = 1\ny = 2")

    assert (
        formatted_code
        == """# MIT License
#
# Copyright (c) 2023 Blah-blah
#
x = 1
y = 2
"""
    )


def test_format_code_with_two_custom_formatters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chaining multiple custom formatters."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        custom_formatters=[
            ADD_COMMENT_FORMATTER,
            ADD_LICENSE_FORMATTER,
        ],
        custom_formatters_kwargs={"license_file": EXAMPLE_LICENSE_FILE},
    )

    formatted_code = formatter.format_code("x = 1\ny = 2")

    assert (
        formatted_code
        == """# MIT License
#
# Copyright (c) 2023 Blah-blah
#
# a comment
x = 1
y = 2
"""
    )


def test_format_code_ruff_format_formatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ruff format formatter."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_FORMAT],
    )
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = b"output"
        formatted_code = formatter.format_code("input")

    assert formatted_code == "output"
    mock_run.assert_called_once_with(
        ("ruff", "format", "-"), input=b"input", capture_output=True, check=False, cwd=str(tmp_path)
    )


def test_format_code_ruff_check_formatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ruff check formatter with auto-fix."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK],
    )
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = b"output"
        formatted_code = formatter.format_code("input")

    assert formatted_code == "output"
    mock_run.assert_called_once_with(
        ("ruff", "check", "--fix", "-"), input=b"input", capture_output=True, check=False, cwd=str(tmp_path)
    )


def test_settings_path_with_existing_file(tmp_path: Path) -> None:
    """Test settings_path with existing file uses parent directory."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")
    existing_file = tmp_path / "existing.py"
    existing_file.write_text("", encoding="utf-8")

    formatter = CodeFormatter(PythonVersionMin, settings_path=existing_file)

    assert formatter.settings_path == str(tmp_path)


def test_settings_path_with_nonexistent_file(tmp_path: Path) -> None:
    """Test settings_path with nonexistent file uses existing parent."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")
    nonexistent_file = tmp_path / "nonexistent.py"

    formatter = CodeFormatter(PythonVersionMin, settings_path=nonexistent_file)

    assert formatter.settings_path == str(tmp_path)


def test_settings_path_with_deeply_nested_nonexistent_path(tmp_path: Path) -> None:
    """Test settings_path with deeply nested nonexistent path finds existing ancestor."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")
    nested_path = tmp_path / "a" / "b" / "c" / "nonexistent.py"

    formatter = CodeFormatter(PythonVersionMin, settings_path=nested_path)

    assert formatter.settings_path == str(tmp_path)


def test_format_directory_ruff_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test format_directory with ruff check."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK],
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with mock.patch("subprocess.run") as mock_run:
        formatter.format_directory(output_dir)

    mock_run.assert_called_once_with(
        ("ruff", "check", "--fix", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_format_directory_ruff_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test format_directory with ruff format."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_FORMAT],
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with mock.patch("subprocess.run") as mock_run:
        formatter.format_directory(output_dir)

    mock_run.assert_called_once_with(
        ("ruff", "format", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_format_directory_both_ruff_formatters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test format_directory with both ruff check and format."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with mock.patch("subprocess.run") as mock_run:
        formatter.format_directory(output_dir)

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        ("ruff", "check", "--fix", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )
    mock_run.assert_any_call(
        ("ruff", "format", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_defer_formatting_skips_ruff_in_format_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that defer_formatting=True skips ruff in format_code."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BLACK, Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
        defer_formatting=True,
    )

    with mock.patch("subprocess.run") as mock_run:
        formatted_code = formatter.format_code("x = 1")

    mock_run.assert_not_called()
    assert "x = 1" in formatted_code


def test_generate_with_ruff_batch_formatting(tmp_path: Path) -> None:
    """Test that generate uses batch ruff formatting for directory output."""
    from datamodel_code_generator import ModuleSplitMode, generate

    schema = """
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        }
    }
    """
    output_dir = tmp_path / "output"

    with mock.patch("datamodel_code_generator.format.subprocess.run") as mock_run:
        generate(
            input_=schema,
            output=output_dir,
            formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
            module_split_mode=ModuleSplitMode.Single,
        )

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        ("ruff", "check", "--fix", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=mock.ANY,
    )
    mock_run.assert_any_call(
        ("ruff", "format", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=mock.ANY,
    )
