"""Validate Claude release draft analysis before updating the draft release."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REMOVAL_PATTERNS = [
    re.compile(r"\b(?:removed|deleted|dropped)\b(?:(?!`).){0,80}`(?P<token>[^`\n]+)`", re.IGNORECASE),
    re.compile(r"`(?P<token>[^`\n]+)`(?:(?!`).){0,80}\b(?:removed|deleted|dropped)\b", re.IGNORECASE),
    re.compile(
        r"\bno longer\s+(?:supports?|accepts?|recognizes?|exports?|provides?|includes?|allows?|has)\b"
        r"(?:(?!`).){0,80}`(?P<token>[^`\n]+)`",
        re.IGNORECASE,
    ),
    re.compile(
        r"`(?P<token>[^`\n]+)`(?:(?!`).){0,80}\bno longer\s+"
        r"(?:available|exists|supported|accepted|recognized|exported|provided|included|allowed)\b",
        re.IGNORECASE,
    ),
]
UNREADABLE_DIFF_RE = re.compile(
    r"\b(?:unable|could not|can't|cannot)\b.{0,160}\b(?:read|access)\b.{0,160}"
    r"\b(?:prepared diff|analysis artifact|diff file|diff)\b",
    re.IGNORECASE | re.DOTALL,
)
TOKEN_BOUNDARY_CHARS = r"A-Za-z0-9_.:/-"


def _parse_args() -> argparse.Namespace:
    """Parse validator CLI arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-path", required=True, type=Path)
    parser.add_argument("--deleted-lines-path", required=True, type=Path)
    return parser.parse_args()


def _parse_claude_output(raw_output: str) -> dict[str, Any]:
    """Parse Claude's structured output as a JSON object."""
    if not raw_output:
        message = "Claude structured output is empty"
        raise SystemExit(message)
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        message = f"Invalid Claude structured output JSON: {exc}"
        raise SystemExit(message) from exc
    if isinstance(parsed, dict):
        return parsed
    message = "Claude structured output must be a JSON object"
    raise SystemExit(message)


def _as_bool(value: Any) -> bool:
    """Normalize Claude's boolean-like field values."""
    result = False
    match value:
        case bool():
            result = value
        case str() if value.lower() == "true":
            result = True
        case _:
            result = False
    return result


def _as_string(value: Any) -> str:
    """Normalize Claude's string-like field values."""
    return value if isinstance(value, str) else ""


def _normalize_token(token: str) -> str:
    """Normalize a claimed removed token for comparison."""
    stripped = token.strip()
    normalized = stripped
    match stripped:
        case value if value.endswith("()"):
            normalized = value[:-2]
        case value:
            normalized = value
    return normalized


def _iter_non_fenced_lines(text: str) -> list[str]:
    """Return lines outside Markdown code fences."""
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        lines.append(line)
    return lines


def _claimed_removed_tokens(line: str) -> set[str]:
    """Extract explicit removed-token claims from one non-fenced line."""
    tokens: set[str] = set()
    for pattern in REMOVAL_PATTERNS:
        for match in pattern.finditer(line):
            if normalized := _normalize_token(match.group("token")):
                tokens.add(normalized)
    return tokens


def _token_present(token: str, deleted_lines: str) -> bool:
    """Return whether token appears with non-token boundaries in deleted lines."""
    if not (normalized := _normalize_token(token)):
        return False
    pattern = re.compile(rf"(?<![{TOKEN_BOUNDARY_CHARS}]){re.escape(normalized)}(?![{TOKEN_BOUNDARY_CHARS}])")
    return bool(pattern.search(deleted_lines))


def _validate_removal_claims(breaking_changes_content: str, deleted_lines_path: Path) -> None:
    """Validate explicit removal claims against trusted deleted diff lines."""
    claims = [
        (line, token)
        for line in _iter_non_fenced_lines(breaking_changes_content)
        for token in _claimed_removed_tokens(line)
    ]
    if not claims:
        return

    deleted_lines = deleted_lines_path.read_text(encoding="utf-8") if deleted_lines_path.exists() else ""
    if not deleted_lines.strip():
        print(
            "Release draft analysis claimed removals, but the exact PR diff has no deleted lines:",
            file=sys.stderr,
        )
        print(breaking_changes_content, file=sys.stderr)
        raise SystemExit(1)

    invalid_claims = [
        f"{line}\n  Missing deleted token: {token}"
        for line, token in claims
        if not _token_present(token, deleted_lines)
    ]
    if not invalid_claims:
        return

    print("Release draft analysis claimed removals that are not present in the exact PR diff:", file=sys.stderr)
    print("\n".join(invalid_claims), file=sys.stderr)
    raise SystemExit(1)


def _validate_diff_was_read(reasoning: str) -> None:
    """Fail if Claude says it could not read the prepared diff."""
    if not (reasoning and UNREADABLE_DIFF_RE.search(reasoning)):
        return
    print("Release draft analysis could not read the prepared diff; refusing to update the draft.", file=sys.stderr)
    print(reasoning, file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    """Validate Claude output and persist the normalized analysis JSON artifact."""
    args = _parse_args()
    claude_output = _parse_claude_output(os.environ.get("CLAUDE_OUTPUT", ""))
    has_breaking_changes = _as_bool(claude_output.get("has_breaking_changes", False))
    breaking_changes_content = _as_string(claude_output.get("breaking_changes_content", ""))
    reasoning = _as_string(claude_output.get("reasoning", ""))

    _validate_diff_was_read(reasoning)
    if has_breaking_changes:
        _validate_removal_claims(breaking_changes_content, args.deleted_lines_path)

    args.analysis_path.write_text(
        json.dumps(
            {
                "has_breaking_changes": has_breaking_changes,
                "breaking_changes_content": breaking_changes_content,
                "reasoning": reasoning,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
