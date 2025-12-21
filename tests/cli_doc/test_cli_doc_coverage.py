"""Tests to track CLI documentation coverage.

These tests verify that all CLI options (defined in arguments.py) have
a cli_doc marker in tests (unless in MANUAL_DOCS).

This ensures that every CLI option has corresponding test documentation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from datamodel_code_generator.cli_options import (
    CLI_OPTION_META,
    MANUAL_DOCS,
    get_all_canonical_options,
    get_canonical_option,
)

COLLECTION_PATH = Path(__file__).parent / ".cli_doc_collection.json"


@pytest.fixture(scope="module")
def collection_data() -> dict[str, Any]:  # pragma: no cover
    """Load the CLI doc collection data."""
    if not COLLECTION_PATH.exists():
        pytest.skip(f"CLI doc collection not found at {COLLECTION_PATH}. Run: pytest --collect-cli-docs -p no:xdist")

    with Path(COLLECTION_PATH).open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def collected_options(collection_data: dict[str, Any]) -> set[str]:  # pragma: no cover
    """Extract canonical options from collection data."""
    options: set[str] = set()
    for item in collection_data.get("items", []):
        options.update(get_canonical_option(opt) for opt in item["marker_kwargs"].get("options", []))
    return options


class TestCLIDocCoverage:  # pragma: no cover
    """Documentation coverage tests."""

    def test_all_options_have_cli_doc_markers(self, collected_options: set[str]) -> None:
        """Verify that all CLI options (except MANUAL_DOCS) have cli_doc markers."""
        all_options = get_all_canonical_options()
        documentable_options = all_options - MANUAL_DOCS
        missing = documentable_options - collected_options
        if missing:
            pytest.fail(
                "CLI options missing cli_doc marker:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(missing))
                + "\n\nAdd @pytest.mark.cli_doc(...) to tests for these options."
            )

    def test_meta_options_not_manual(self) -> None:
        """Verify that CLI_OPTION_META options are not in MANUAL_DOCS."""
        meta_options = set(CLI_OPTION_META.keys())
        overlap = meta_options & MANUAL_DOCS
        if overlap:
            pytest.fail(
                "Options in both CLI_OPTION_META and MANUAL_DOCS:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(overlap))
            )

    def test_collection_schema_version(self, collection_data: dict[str, Any]) -> None:
        """Verify that collection data has expected schema version."""
        version = collection_data.get("schema_version")
        assert version is not None, "Collection data missing 'schema_version'"
        assert version == 1, f"Unexpected schema version: {version}"


class TestCoverageStats:  # pragma: no cover
    """Informational tests for coverage statistics."""

    @pytest.mark.skip(reason="Informational: run with -v --no-skip to see stats")
    def test_show_coverage_stats(self, collected_options: set[str]) -> None:
        """Display documentation coverage statistics."""
        all_options = get_all_canonical_options()
        documentable = all_options - MANUAL_DOCS
        undocumented = documentable - collected_options

        print(f"\nUndocumented options ({len(undocumented)}):")  # noqa: T201
        for opt in sorted(undocumented):
            print(f"  {opt}")  # noqa: T201

    @pytest.mark.skip(reason="Informational: run with -v --no-skip to see stats")
    def test_show_documented_options(self, collected_options: set[str]) -> None:
        """Display currently documented options."""
        print(f"\nDocumented options ({len(collected_options)}):")  # noqa: T201
        for opt in sorted(collected_options):
            meta = CLI_OPTION_META.get(opt)
            category = meta.category.value if meta else "General Options"
            print(f"  {opt} ({category})")  # noqa: T201
