"""Tests for docs example generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts import build_docs_examples
from tests.conftest import assert_output

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_docs_examples.py"
EXPECTED_DOCS_EXAMPLES_PATH = ROOT / "tests" / "data" / "expected" / "docs_examples"


def test_build_docs_examples_check_is_up_to_date() -> None:
    """Generated docs examples are committed."""
    subprocess.run([sys.executable, str(SCRIPT), "--check"], check=True)


def test_docs_examples_registry() -> None:
    """Docs example registry exposes stable generated section IDs."""
    output = "".join(f"{example.example_id}: {example.path.name}\n" for example in build_docs_examples.docs_examples())

    assert_output(output, EXPECTED_DOCS_EXAMPLES_PATH / "docs_examples_registry.txt")


def test_reuse_scope_tree_example() -> None:
    """Directory examples render a stable tree and representative files."""
    assert_output(
        build_docs_examples.render_reuse_scope_tree_example(),
        EXPECTED_DOCS_EXAMPLES_PATH / "reuse_scope_tree_example.txt",
    )
