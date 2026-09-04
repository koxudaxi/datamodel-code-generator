"""Skip remote release analysis for changes that cannot affect released behavior."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable  # ruff: ignore[typing-only-standard-library-import] - fast runtime import
from pathlib import Path

FILE_CHANGE_KEYS = frozenset({"path", "previous_path"})
SAFE_EXACT_PATHS = frozenset({
    ".github/workflows/codeql.yaml",
    ".github/workflows/release-draft.yaml",
    "scripts/prepare_release_draft_analysis.py",
    "tox.ini",
})
SAFE_ROOTS = frozenset({"tests"})
SAFE_REASONING = "Only release automation or tests changed, so generated output and public interfaces are unaffected."


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line paths supplied by the release workflow."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed-files-path", required=True, type=Path)
    parser.add_argument("--expected-changed-files", required=True, type=int)
    parser.add_argument("--analysis-path", required=True, type=Path)
    parser.add_argument("--github-output-path", required=True, type=Path)
    return parser.parse_args(argv)


def _is_safe_path(path: str) -> bool:
    """Return whether one exact changed path cannot affect released behavior."""
    if not path or path != path.strip():
        return False
    if path in SAFE_EXACT_PATHS:
        return True
    match path.split("/", 1):
        case [root, relative_path] if root in SAFE_ROOTS and relative_path:
            return True
    return False


def _paths_from_record(raw_record: str) -> tuple[str, ...] | None:
    """Parse one exact GitHub API file record without ambiguous framing."""
    if not (record := raw_record.strip()):
        return None
    try:
        file_change = json.loads(record)
    except json.JSONDecodeError:
        return None
    if not isinstance(file_change, dict) or file_change.keys() != FILE_CHANGE_KEYS:
        return None
    match file_change:
        case {"path": str(path), "previous_path": None}:
            return (path,)
        case {"path": str(path), "previous_path": str(previous_path)}:
            return path, previous_path
    return None


def _count_safe_file_changes(changed_files: Iterable[str]) -> int | None:
    """Count safely framed file records, or reject the stream immediately."""
    file_count = 0
    for raw_record in changed_files:
        if not (paths := _paths_from_record(raw_record)) or not all(map(_is_safe_path, paths)):
            return None
        file_count += 1
    return file_count


def _requires_claude(changed_files_path: Path, expected_changed_files: int) -> bool:
    """Return whether any changed path needs semantic release analysis."""
    if expected_changed_files <= 0:
        return True
    try:
        with changed_files_path.open(encoding="utf-8") as changed_files:
            file_count = _count_safe_file_changes(changed_files)
    except (OSError, UnicodeError):
        return True
    return file_count is None or file_count != expected_changed_files


def main(argv: list[str] | None = None) -> None:
    """Write the workflow route and, for safe changes, a trusted analysis."""
    args = _parse_args(argv)
    requires_claude = _requires_claude(args.changed_files_path, args.expected_changed_files)
    if not requires_claude:
        args.analysis_path.write_text(
            json.dumps({
                "has_breaking_changes": False,
                "breaking_changes_content": "",
                "reasoning": SAFE_REASONING,
            })
            + "\n",
            encoding="utf-8",
        )
    with args.github_output_path.open("a", encoding="utf-8") as github_output:
        github_output.write(f"requires_claude={str(requires_claude).lower()}\n")


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    main()
