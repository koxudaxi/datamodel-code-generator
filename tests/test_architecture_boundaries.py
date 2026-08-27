"""Tests for cross-layer architecture guardrails."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from scripts import check_architecture_boundaries
from tests.conftest import assert_output

ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = Path(__file__).parent / "data" / "architecture_boundaries"
EXPECTED_ROOT = Path(__file__).parent / "data" / "expected" / "architecture_boundaries"


def test_source_tree_respects_architecture_boundaries() -> None:
    """Keep production dependencies within declared capabilities and bounded legacy exceptions."""
    violations = check_architecture_boundaries.check_paths([ROOT / "src" / "datamodel_code_generator"])

    assert_output(
        check_architecture_boundaries.format_report(violations),
        EXPECTED_ROOT / "clean.txt",
    )


def test_architecture_boundary_detector_reports_cross_layer_dependencies() -> None:
    """Cover static, relative, dynamic, semantic, and private import violations."""
    files: list[tuple[Path, check_architecture_boundaries.Layer]] = [
        (FIXTURE_ROOT / "parser" / "forbidden.py", "parser"),
        (FIXTURE_ROOT / "config" / "forbidden.py", "config"),
        (FIXTURE_ROOT / "input_model" / "forbidden.py", "input-model"),
        (FIXTURE_ROOT / "shared" / "forbidden.py", "shared"),
    ]
    violations = check_architecture_boundaries.check_files(files, allowlist={})

    assert_output(
        check_architecture_boundaries.format_report(violations),
        EXPECTED_ROOT / "violations.txt",
    )


def test_architecture_boundary_detector_reports_stale_allowlist_entries() -> None:
    """Require legacy exceptions to disappear when their matching debt is removed."""
    clean_fixture = FIXTURE_ROOT / "stale" / "clean.py"
    stale_key = check_architecture_boundaries.BoundaryKey(
        "tests/data/architecture_boundaries/stale/clean.py",
        "missing_legacy_hook",
        "backend-import",
        "datamodel_code_generator.model.pydantic_v2",
    )
    violations = check_architecture_boundaries.check_files(
        [(clean_fixture, "parser")],
        allowlist={
            stale_key: check_architecture_boundaries.AllowlistEntry("fixture for stale-entry reporting"),
        },
    )

    assert_output(
        check_architecture_boundaries.format_report(violations),
        EXPECTED_ROOT / "stale_allowlist.txt",
    )


def test_architecture_boundary_allowlist_contract_and_file_discovery(tmp_path: Path) -> None:
    """Cover invalid allowlist metadata, outside paths, and direct file targets."""

    def allowlist_error(reason: str, count: int, expected: str) -> str:
        with pytest.raises(ValueError, match=expected) as error:
            check_architecture_boundaries.AllowlistEntry(reason, count)
        return str(error.value)

    messages = [
        allowlist_error("", 1, "architecture boundary allowlist entries require a reason"),
        allowlist_error("bounded fixture", 0, "architecture boundary allowlist counts must be positive"),
    ]

    clean_fixture = FIXTURE_ROOT / "stale" / "clean.py"
    direct_files = check_architecture_boundaries.iter_python_files(
        [clean_fixture, clean_fixture.with_suffix(".txt")],
    )
    outside_path = tmp_path / "outside.py"
    outside_path_preserved = check_architecture_boundaries._display_path(outside_path) == outside_path.as_posix()
    messages.extend(
        (
            f"direct Python files: {len(direct_files)}",
            f"outside path preserved: {outside_path_preserved}",
        ),
    )

    assert_output("\n".join(messages) + "\n", EXPECTED_ROOT / "allowlist_contract.txt")


def test_architecture_boundary_cli_reports_actionable_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exercise the clean CLI, an abnormal dependency, and the executable entry point."""
    success_code = check_architecture_boundaries.main([str(ROOT / "src" / "datamodel_code_generator")])
    clean_output = capsys.readouterr()

    legacy_key = check_architecture_boundaries.BoundaryKey(
        "src/datamodel_code_generator/parser/base.py",
        "__getattr__",
        "backend-import",
        "datamodel_code_generator.model.dataclass",
    )
    monkeypatch.delitem(check_architecture_boundaries.DEFAULT_ALLOWLIST, legacy_key)
    failure_code = check_architecture_boundaries.main([str(ROOT / "src" / "datamodel_code_generator" / "parser")])
    failure_output = capsys.readouterr()
    monkeypatch.undo()

    monkeypatch.setattr(sys, "argv", [str(ROOT / "scripts" / "check_architecture_boundaries.py")])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(ROOT / "scripts" / "check_architecture_boundaries.py"), run_name="__main__")
    entrypoint_output = capsys.readouterr()

    assert_output(
        (
            f"clean exit: {success_code}\n"
            f"clean stdout: {clean_output.out!r}\n"
            f"clean stderr: {clean_output.err!r}\n"
            f"failure exit: {failure_code}\n"
            f"{failure_output.err}"
            f"entrypoint exit: {exit_info.value.code}\n"
            f"entrypoint stdout: {entrypoint_output.out!r}\n"
            f"entrypoint stderr: {entrypoint_output.err!r}\n"
        ),
        EXPECTED_ROOT / "cli.txt",
    )
