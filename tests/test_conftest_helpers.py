"""Tests for shared assertion helpers in tests.conftest."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import call

import pytest

from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.format import Formatter
from tests.conftest import (
    _infer_expected_file,
    assert_exact_directory_content,
    assert_inputs_not_mutated,
    assert_parser_modules,
    assert_parser_results,
)
from tests.main import _builtin_parity
from tests.main import conftest as main_conftest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("function_name", "expected_file"),
    [
        ("test_main_pet", "pet.py"),
        ("test_pet", "pet.py"),
        ("helper", "helper.py"),
    ],
)
def test_infer_expected_file(function_name: str, expected_file: str) -> None:
    """Expected filenames are inferred consistently from test function names."""
    assert _infer_expected_file(function_name) == expected_file


def test_assert_exact_directory_content_reports_diff(tmp_path: Path) -> None:
    """Test exact directory comparison reports the mismatched file path."""
    output_dir = tmp_path / "output"
    expected_dir = tmp_path / "expected"
    output_dir.mkdir()
    expected_dir.mkdir()

    (output_dir / "sample.py").write_text("value = 1\n", encoding="utf-8")
    (expected_dir / "sample.py").write_text("value = 2\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="Content mismatch") as exc_info:
        assert_exact_directory_content(output_dir, expected_dir)

    assert "sample.py" in str(exc_info.value)


def test_assert_parser_results_rejects_unexpected_result(tmp_path: Path) -> None:
    """Parser result assertions fail when generated output has no expected file."""
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()
    (expected_dir / "sample.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(AssertionError, match=r"extra\.py"):
        assert_parser_results({"sample.py": "value = 1\n", "extra.py": "value = 2\n"}, expected_dir)


def test_assert_parser_results_rejects_missing_result(tmp_path: Path) -> None:
    """Parser result assertions fail when an expected file is not generated."""
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()
    (expected_dir / "sample.py").write_text("value = 1\n", encoding="utf-8")
    (expected_dir / "missing.py").write_text("value = 2\n", encoding="utf-8")

    with pytest.raises(AssertionError, match=r"missing\.py"):
        assert_parser_results({"sample.py": "value = 1\n"}, expected_dir)


def test_assert_parser_modules_rejects_missing_expected_module(tmp_path: Path) -> None:
    """Parser module assertions fail when an expected module is not generated."""
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()
    (expected_dir / "sample.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="Expected files not in parser modules"):
        assert_parser_modules({}, expected_dir)


def test_assert_parser_modules_rejects_unexpected_module(tmp_path: Path) -> None:
    """Parser module assertions fail when generated output has no expected file."""
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()

    with pytest.raises(AssertionError, match="Parser modules not in expected files"):
        assert_parser_modules({("sample.py",): "value = 1\n"}, expected_dir)


def test_assert_inputs_not_mutated_allows_unchanged_nested_values() -> None:
    """Mutation guard accepts unchanged dict/list inputs and ignores immutable labels."""
    schema = {"properties": {"name": {"type": "string"}}, "required": ["name"]}

    with assert_inputs_not_mutated({"schema": schema, "description": "ignored"}):
        assert schema["properties"]["name"]["type"] == "string"


def test_assert_inputs_not_mutated_reports_nested_mutation() -> None:
    """Mutation guard reports the label for nested dict/list mutations."""
    schema = {"properties": {"name": {"type": "string"}}, "required": ["name"]}

    with (
        pytest.raises(pytest.fail.Exception, match="schema was mutated"),
        assert_inputs_not_mutated({"schema": schema}),
    ):
        schema["required"].append("age")


def test_path_cache_value_at_path_handles_sequences() -> None:
    """Path cache helper can traverse mapping and sequence values."""
    value = {"items": [{"name": "first"}]}

    assert main_conftest._value_at_path(value, ("items", 0, "name")) == "first"


def test_path_cache_value_at_path_reports_invalid_path() -> None:
    """Path cache helper reports paths that cannot be traversed."""
    with pytest.raises(pytest.fail.Exception, match="Expected cached value to contain path"):
        main_conftest._value_at_path({"items": []}, ("items", "name"))


def test_assert_path_cache_reuses_value_reports_cache_miss(tmp_path: Path) -> None:
    """Path cache reuse helper fails when the loader returns a new object."""
    path = tmp_path / "schema.json"
    path.write_text("{}", encoding="utf-8")

    def load_new_value(path: Path, encoding: str) -> object:  # noqa: ARG001
        return {}

    with pytest.raises(pytest.fail.Exception, match=r"Expected cached value .* to be reused"):
        main_conftest.assert_path_cache_reuses_value(load_new_value, path)


def test_assert_path_cache_invalidates_after_write_reports_stale_identity(tmp_path: Path) -> None:
    """Path cache invalidation helper fails when a loader returns the stale object."""
    path = tmp_path / "schema.json"
    path.write_text("old", encoding="utf-8")
    cached_value: dict[str, str] = {}

    def load_stale_value(path: Path, encoding: str) -> object:  # noqa: ARG001
        return cached_value

    with pytest.raises(pytest.fail.Exception, match=r"Expected cached value .* to be invalidated after write"):
        main_conftest.assert_path_cache_invalidates_after_write(load_stale_value, path, "new", "new")


def test_assert_path_cache_invalidates_after_write_reports_unexpected_value(tmp_path: Path) -> None:
    """Path cache invalidation helper fails when the updated value is unexpected."""
    path = tmp_path / "schema.json"
    path.write_text("old", encoding="utf-8")

    def load_text_value(path: Path, encoding: str) -> object:
        return {"value": path.read_text(encoding=encoding)}

    with pytest.raises(pytest.fail.Exception, match="Expected cached value 'expected', got 'actual'"):
        main_conftest.assert_path_cache_invalidates_after_write(
            load_text_value,
            path,
            "actual",
            "expected",
            expected_value_path=("value",),
        )


def test_assert_path_cache_invalidates_after_write_reports_updated_cache_miss(tmp_path: Path) -> None:
    """Path cache invalidation helper fails when the updated value is not reused."""
    path = tmp_path / "schema.json"
    path.write_text("old", encoding="utf-8")

    def load_text_value(path: Path, encoding: str) -> object:
        return {"value": path.read_text(encoding=encoding)}

    with pytest.raises(pytest.fail.Exception, match=r"Expected updated cached value .* to be reused"):
        main_conftest.assert_path_cache_invalidates_after_write(
            load_text_value,
            path,
            "new",
            "new",
            expected_value_path=("value",),
            warmups=1,
        )


def test_builtin_parity_mock_call_preservation(mocker: MockerFixture) -> None:
    """Mock call history is restored after parity-only calls."""
    mocked_callable = mocker.Mock()
    mocked_callable("before")

    with _builtin_parity._preserve_mock_calls([mocked_callable, object()]):
        mocked_callable("during")

    assert mocked_callable.call_args == call("before")
    assert mocked_callable.call_args_list == [call("before")]
    assert mocked_callable.mock_calls == [call("before")]
    assert mocked_callable.call_count == 1


def test_builtin_parity_prance_mock_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prance parser mocks are preserved only when prance is imported."""
    monkeypatch.delitem(sys.modules, "prance", raising=False)
    assert _builtin_parity._parity_mocked_callables_to_preserve() == []

    base_parser = object()
    monkeypatch.setitem(sys.modules, "prance", SimpleNamespace(BaseParser=base_parser))

    assert _builtin_parity._parity_mocked_callables_to_preserve() == [base_parser]


def test_builtin_parity_cli_formatter_helpers(tmp_path: Path) -> None:
    """Pure CLI formatter parity helpers keep default formatter semantics."""
    assert _builtin_parity._extract_cli_formatters(None) is None
    assert _builtin_parity._extract_cli_formatters(["--formatters", "black", "isort", "--check"]) == [
        "black",
        "isort",
    ]
    assert _builtin_parity._uses_default_cli_formatters(None)
    assert _builtin_parity._uses_default_cli_formatters(["--formatters", "black", "isort"])
    assert not _builtin_parity._uses_default_cli_formatters(["--custom-formatters", "tests.custom"])
    assert not _builtin_parity._uses_default_cli_formatters(["--formatters", "builtin"])
    assert _builtin_parity._uses_check_mode(["--check"])
    assert not _builtin_parity._uses_check_mode(None)
    assert _builtin_parity._uses_default_api_formatters({})
    assert _builtin_parity._uses_default_api_formatters({"formatters": [Formatter.BLACK, Formatter.ISORT]})
    assert not _builtin_parity._uses_default_api_formatters({"formatters": [Formatter.BUILTIN]})
    assert not _builtin_parity._uses_default_api_formatters({"custom_formatters": ["tests.custom"]})
    assert _builtin_parity._builtin_formatter_extra_args(None) == ["--formatters", "builtin"]
    assert _builtin_parity._builtin_formatter_extra_args(["--disable-timestamp"]) == [
        "--disable-timestamp",
        "--formatters",
        "builtin",
    ]

    output_dir = tmp_path / "model"
    output_dir.mkdir()
    assert _builtin_parity._builtin_formatter_parity_output_path(output_dir) == tmp_path / "model_builtin_parity"
    output_file = tmp_path / "output.py"
    assert _builtin_parity._builtin_formatter_parity_output_path(output_file) == tmp_path / "output.builtin-parity.py"


def test_builtin_parity_clear_output_path(tmp_path: Path) -> None:
    """Stale parity output paths are removed for files and directories."""
    stale_file = tmp_path / "output.py"
    stale_file.write_text("stale\n", encoding="utf-8")
    _builtin_parity._clear_builtin_formatter_parity_output(stale_file)
    assert not stale_file.exists()

    stale_dir = tmp_path / "model"
    stale_dir.mkdir()
    (stale_dir / "output.py").write_text("stale\n", encoding="utf-8")
    _builtin_parity._clear_builtin_formatter_parity_output(stale_dir)
    assert not stale_dir.exists()


def test_default_formatter_cli_args(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Builtin formatter defaults apply only to generation commands without formatter settings."""
    monkeypatch.delenv("DATAMODEL_CODE_GENERATOR_TEST_DEFAULT_FORMATTER", raising=False)
    assert main_conftest._default_formatter_cli_args(["--input", "schema.json"]) == ["--input", "schema.json"]

    monkeypatch.setenv("DATAMODEL_CODE_GENERATOR_TEST_DEFAULT_FORMATTER", "builtin")
    assert main_conftest._default_formatter_cli_args(["--input", "schema.json"]) == [
        "--input",
        "schema.json",
        "--formatters",
        "builtin",
    ]
    assert main_conftest._default_formatter_cli_args(
        ["--input", "schema.json"],
        output_path=tmp_path / "output.py",
    ) == [
        "--input",
        "schema.json",
        "--formatters",
        "builtin",
    ]
    assert not (tmp_path / "pyproject.toml").exists()
    assert main_conftest._default_formatter_cli_args(["--input", "schema.json", "--formatters=isort"]) == [
        "--input",
        "schema.json",
        "--formatters=isort",
    ]
    assert main_conftest._default_formatter_cli_args(["--input", "schema.json"], is_generation_command=False) == [
        "--input",
        "schema.json",
    ]
    assert main_conftest._default_formatter_cli_args(
        ["--input", "schema.json"],
        copy_files=[(tmp_path / "source.toml", tmp_path / "pyproject.toml")],
        output_path=tmp_path / "output.py",
    ) == ["--input", "schema.json"]
    (tmp_path / "pyproject.toml").write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")
    assert main_conftest._default_formatter_cli_args(
        ["--input", "schema.json"],
        output_path=tmp_path / "output.py",
    ) == ["--input", "schema.json"]


def test_builtin_default_formatter_config(tmp_path: Path) -> None:
    """Builtin formatter config is present only while the generation helper runs."""
    output_file = tmp_path / "output.py"
    with main_conftest._builtin_default_formatter_config(output_file, enabled=True):
        assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == (
            "[tool.datamodel-codegen]\nbuiltin-format-line-length = 88\n"
        )
    assert not (tmp_path / "pyproject.toml").exists()

    with main_conftest._builtin_default_formatter_config(tmp_path, enabled=True):
        assert (tmp_path / "pyproject.toml").is_file()
    assert not (tmp_path / "pyproject.toml").exists()

    existing_config = "[tool.black]\nline-length = 60\n"
    (tmp_path / "pyproject.toml").write_text(existing_config, encoding="utf-8")
    with main_conftest._builtin_default_formatter_config(output_file, enabled=True):
        assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == existing_config
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == existing_config


def test_default_formatter_main_generation_detection() -> None:
    """Raw main helpers identify only generation commands for builtin defaults."""
    assert main_conftest._is_main_generation_command(["--input", "schema.json"])
    assert main_conftest._is_main_generation_command(["--url=https://example.com/schema.json"])
    assert not main_conftest._is_main_generation_command(["--input", "schema.json", "--generate-prompt"])
    assert not main_conftest._is_main_generation_command(["--input", "schema.json", "--output-format=json"])
    assert not main_conftest._is_main_generation_command(["--version"])
    assert main_conftest._get_cli_output_path(["--output", "model.py"]) == Path("model.py")
    assert main_conftest._get_cli_output_path(["--output=model.py"]) == Path("model.py")
    assert main_conftest._get_cli_output_path(["--input", "schema.json"]) is None


def test_default_formatter_generate_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """API generation helpers add builtin only when formatter settings are absent."""
    generate_kwargs: dict[str, object] = {}
    monkeypatch.delenv("DATAMODEL_CODE_GENERATOR_TEST_DEFAULT_FORMATTER", raising=False)
    assert main_conftest._default_formatter_generate_options(generate_kwargs) == generate_kwargs

    monkeypatch.setenv("DATAMODEL_CODE_GENERATOR_TEST_DEFAULT_FORMATTER", "builtin")
    assert main_conftest._default_formatter_generate_options(generate_kwargs) == {
        "formatters": [Formatter.BUILTIN],
        "builtin_format_line_length": 88,
    }

    explicit_kwargs = {"formatters": [Formatter.BLACK]}
    assert main_conftest._default_formatter_generate_options(explicit_kwargs) == explicit_kwargs

    (tmp_path / "pyproject.toml").write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")
    assert main_conftest._default_formatter_generate_options({}, output_path=tmp_path / "output.py") == {}


def test_builtin_parity_generated_python_comparison(tmp_path: Path) -> None:
    """Generated Python comparison ignores command header differences."""
    expected_file = tmp_path / "expected.py"
    actual_file = tmp_path / "actual.py"
    expected_file.write_text("#   command:   datamodel-codegen expected\nvalue = 1\n", encoding="utf-8")
    actual_file.write_text("#   command:   datamodel-codegen actual\nvalue = 1\n", encoding="utf-8")

    _builtin_parity._assert_same_generated_python(expected_file, actual_file)

    expected_dir = tmp_path / "expected"
    actual_dir = tmp_path / "actual"
    expected_dir.mkdir()
    actual_dir.mkdir()
    (expected_dir / "model.py").write_text("#   command:   datamodel-codegen expected\nvalue = 1\n", encoding="utf-8")
    (actual_dir / "model.py").write_text("#   command:   datamodel-codegen actual\nvalue = 1\n", encoding="utf-8")

    _builtin_parity._assert_same_generated_python(expected_dir, actual_dir)


def test_builtin_cli_formatter_parity_file_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CLI parity reruns file input with the builtin formatter."""
    monkeypatch.setenv("DATAMODEL_CODE_GENERATOR_CHECK_BUILTIN_FORMATTER_PARITY", "1")
    output_path = tmp_path / "output.py"
    output_path.write_text("#   command:   datamodel-codegen expected\nvalue = 1\n", encoding="utf-8")

    def fake_run_main(
        input_path: Path,
        builtin_output_path: Path,
        input_file_type: str | None,
        *,
        extra_args: list[str] | None = None,
        copy_files: list[tuple[Path, Path]] | None = None,
    ) -> Exit:
        assert input_path == tmp_path / "schema.json"
        assert input_file_type is None
        assert extra_args == ["--formatters", "builtin"]
        assert copy_files is None
        builtin_output_path.write_text("#   command:   datamodel-codegen actual\nvalue = 1\n", encoding="utf-8")
        return Exit.OK

    monkeypatch.setattr(main_conftest, "_run_main", fake_run_main)

    _builtin_parity._assert_builtin_cli_formatter_parity(
        input_path=tmp_path / "schema.json",
        output_path=output_path,
        input_file_type=None,
        extra_args=None,
        copy_files=None,
        stdin_path=None,
        monkeypatch=None,
        context=main_conftest._builtin_cli_formatter_parity_context(),
    )

    assert not (tmp_path / "output.builtin-parity.py").exists()


def test_builtin_cli_formatter_parity_stdin_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CLI parity supports stdin-based tests without changing output."""
    monkeypatch.setenv("DATAMODEL_CODE_GENERATOR_CHECK_BUILTIN_FORMATTER_PARITY", "1")
    stdin_path = tmp_path / "schema.json"
    stdin_path.write_text("{}\n", encoding="utf-8")
    output_path = tmp_path / "output.py"
    output_path.write_text("#   command:   datamodel-codegen expected\nvalue = 1\n", encoding="utf-8")

    def fake_main(args: list[str]) -> Exit:
        output_index = args.index("--output") + 1
        Path(args[output_index]).write_text("#   command:   datamodel-codegen actual\nvalue = 1\n", encoding="utf-8")
        return Exit.OK

    monkeypatch.setattr(_builtin_parity, "main", fake_main)

    _builtin_parity._assert_builtin_cli_formatter_parity(
        input_path=None,
        output_path=output_path,
        input_file_type=None,
        extra_args=None,
        copy_files=None,
        stdin_path=stdin_path,
        monkeypatch=monkeypatch,
        context=main_conftest._builtin_cli_formatter_parity_context(),
    )

    assert not (tmp_path / "output.builtin-parity.py").exists()


def test_builtin_generate_formatter_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Generate parity reruns API output with the builtin formatter."""
    monkeypatch.setenv("DATAMODEL_CODE_GENERATOR_CHECK_BUILTIN_FORMATTER_PARITY", "1")
    input_path = tmp_path / "schema.json"
    output_path = tmp_path / "output.py"
    output_path.write_text("#   command:   datamodel-codegen expected\nvalue = 1\n", encoding="utf-8")

    def fake_generate(input_: Path, **options: object) -> None:
        assert input_ == input_path
        assert options["formatters"] == [Formatter.BUILTIN]
        output = options["output"]
        assert isinstance(output, Path)
        output.write_text("#   command:   datamodel-codegen actual\nvalue = 1\n", encoding="utf-8")

    monkeypatch.setattr(_builtin_parity, "generate", fake_generate)

    _builtin_parity._assert_builtin_generate_formatter_parity(
        input_=input_path,
        output_path=output_path,
        generate_options={"output": output_path},
    )

    assert not (tmp_path / "output.builtin-parity.py").exists()


def test_builtin_generate_formatter_parity_preserves_warnings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Generate parity preserves expected warning assertions."""
    monkeypatch.setenv("DATAMODEL_CODE_GENERATOR_CHECK_BUILTIN_FORMATTER_PARITY", "1")
    input_path = tmp_path / "schema.json"
    output_path = tmp_path / "output.py"
    output_path.write_text("#   command:   datamodel-codegen expected\nvalue = 1\n", encoding="utf-8")

    def fake_generate(input_: Path, **options: object) -> None:
        import warnings

        assert input_ == input_path
        output = options["output"]
        assert isinstance(output, Path)
        output.write_text("#   command:   datamodel-codegen actual\nvalue = 1\n", encoding="utf-8")
        warnings.warn("expected warning", UserWarning, stacklevel=2)

    monkeypatch.setattr(_builtin_parity, "generate", fake_generate)

    _builtin_parity._assert_builtin_generate_formatter_parity(
        input_=input_path,
        output_path=output_path,
        generate_options={"output": output_path},
        expected_warnings=["expected warning"],
    )

    assert not (tmp_path / "output.builtin-parity.py").exists()
