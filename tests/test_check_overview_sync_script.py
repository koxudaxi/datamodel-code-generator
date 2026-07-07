"""Tests for README/docs overview synchronization checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts import check_overview_sync
from tests.conftest import assert_output

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_overview_sync.py"
EXPECTED_OVERVIEW_SYNC_PATH = Path(__file__).resolve().parent / "data" / "expected" / "overview_sync"


def test_check_overview_sync_reports_current_files_are_synchronized() -> None:
    """The committed README and docs overview blocks stay in sync."""
    result = subprocess.run([sys.executable, str(SCRIPT)], check=True, capture_output=True, text=True)

    assert_output(result.stdout, EXPECTED_OVERVIEW_SYNC_PATH / "check_current.txt")


def test_compare_snapshots_reports_changed_fields() -> None:
    """Snapshot comparison reports only fields that differ."""
    readme = check_overview_sync.OverviewSnapshot(
        tagline="Generate Python data models from schema definitions in seconds.",
        badges=("badge",),
        hero_alt="hero",
        privacy_note="privacy",
        feature_bullets=("- feature",),
    )
    docs = check_overview_sync.OverviewSnapshot(
        tagline="Generate Python data models from schema definitions in seconds.",
        badges=("badge",),
        hero_alt="hero",
        privacy_note="updated privacy",
        feature_bullets=("- feature",),
    )

    assert_output(
        "\n".join((*check_overview_sync.compare_snapshots(readme, docs), "")),
        EXPECTED_OVERVIEW_SYNC_PATH / "changed_fields.txt",
    )


def test_extract_badges_matches_known_badge_hosts_only() -> None:
    """Badge extraction checks URL hosts instead of arbitrary substrings."""
    badges = check_overview_sync._extract_badges([
        "# datamodel-code-generator",
        "https://example.com/not-a-badge/img.shields.io",
        "[![PyPI](https://img.shields.io/pypi/v/datamodel-code-generator.svg)](https://pypi.org/project/datamodel-code-generator/)",
        "[![Codecov](https://codecov.io/gh/koxudaxi/datamodel-code-generator/branch/main/graph/badge.svg)](https://codecov.io/gh/koxudaxi/datamodel-code-generator)",
        "## ✨ What it does",
    ])

    assert_output("\n".join((*badges, "")), EXPECTED_OVERVIEW_SYNC_PATH / "badge_hosts.txt")
