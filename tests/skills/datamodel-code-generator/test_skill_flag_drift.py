"""Tests for the datamodel-code-generator agent skill documentation."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

SKILL_DIR = Path(__file__).parents[3] / "skills" / "datamodel-code-generator"
SKILL_FILES = [
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "references" / "workflows.md",
    SKILL_DIR / "references" / "cli-options.md",
    SKILL_DIR / "references" / "troubleshooting.md",
]
FLAG_RE = re.compile(r"(?<![\w-])--[a-zA-Z0-9][a-zA-Z0-9-]*")
NON_DATAMODEL_FLAGS = frozenset({"--from", "--with"})


def _read_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        pytest.fail(f"{path} is missing YAML frontmatter")
    frontmatter = yaml.safe_load(match.group(1))
    if not isinstance(frontmatter, dict):
        pytest.fail(f"{path} frontmatter must be a mapping")
    return frontmatter


def _documented_flags() -> dict[str, set[Path]]:
    flags: dict[str, set[Path]] = {}
    for path in SKILL_FILES:
        text = path.read_text(encoding="utf-8")
        for flag in FLAG_RE.findall(text):
            flags.setdefault(flag, set()).add(path)
    return flags


def test_skill_frontmatter_validates() -> None:
    """Validate the skill frontmatter and referenced files."""
    frontmatter = _read_frontmatter(SKILL_DIR / "SKILL.md")
    name = frontmatter.get("name")
    description = frontmatter.get("description")

    assert name == SKILL_DIR.name
    assert re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", name)
    assert isinstance(description, str)
    assert description.strip()
    assert len(description) <= 1024
    assert frontmatter.get("license") == "MIT"
    assert frontmatter.get("metadata") == {"status": "experimental"}
    for path in SKILL_FILES:
        assert path.is_file()


def test_skill_documented_flags_exist_in_cli_help() -> None:
    """Documented datamodel-codegen flags must exist in current CLI help."""
    result = subprocess.run(
        ["datamodel-codegen", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"datamodel-codegen --help failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    help_text = result.stdout
    unknown = {
        flag: sorted(str(path.relative_to(SKILL_DIR.parents[1])) for path in paths)
        for flag, paths in _documented_flags().items()
        if flag not in NON_DATAMODEL_FLAGS and flag not in help_text
    }

    assert unknown == {}
