"""Tests to track CLI documentation coverage.

These tests verify that options intended to be documented have:
1. A cli_doc marker in tests
2. An entry in CLI_OPTION_META

The DOCUMENTED_OPTIONS set defines which options should be documented.
This allows gradual expansion of documentation coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from datamodel_code_generator.cli_options import (
    CLI_OPTION_META,
    EXCLUDED_FROM_DOCS,
    get_all_canonical_options,
    get_canonical_option,
)

COLLECTION_PATH = Path(__file__).parent / ".cli_doc_collection.json"

# Options that should be documented (gradually expand this set)
# Options in this set MUST have:
#   1. A cli_doc marker in tests
#   2. An entry in CLI_OPTION_META
DOCUMENTED_OPTIONS: frozenset[str] = frozenset({
    "--frozen-dataclasses",
    # Add more as cli_doc markers are added to tests...
})


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

    def test_documented_options_have_cli_doc_markers(  # noqa: PLR6301
        self, collected_options: set[str]
    ) -> None:
        """Verify that DOCUMENTED_OPTIONS have cli_doc markers in tests."""
        missing = DOCUMENTED_OPTIONS - collected_options
        if missing:
            pytest.fail(
                "Options in DOCUMENTED_OPTIONS but missing cli_doc marker:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(missing))
                + "\n\nAdd @pytest.mark.cli_doc(...) to tests for these options."
            )

    def test_documented_options_have_meta(self) -> None:  # noqa: PLR6301
        """Verify that DOCUMENTED_OPTIONS have CLI_OPTION_META entries."""
        missing = DOCUMENTED_OPTIONS - set(CLI_OPTION_META.keys())
        if missing:
            pytest.fail(
                "Options in DOCUMENTED_OPTIONS but missing CLI_OPTION_META:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(missing))
                + "\n\nAdd entries to CLI_OPTION_META in cli_options.py."
            )

    def test_documented_options_not_excluded(self) -> None:  # noqa: PLR6301
        """Verify that DOCUMENTED_OPTIONS are not in EXCLUDED_FROM_DOCS."""
        overlap = DOCUMENTED_OPTIONS & EXCLUDED_FROM_DOCS
        if overlap:
            pytest.fail(
                "Options in both DOCUMENTED_OPTIONS and EXCLUDED_FROM_DOCS:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(overlap))
            )

    def test_collection_schema_version(  # noqa: PLR6301
        self, collection_data: dict[str, Any]
    ) -> None:
        """Verify that collection data has expected schema version."""
        version = collection_data.get("schema_version")
        assert version is not None, "Collection data missing 'schema_version'"
        assert version == 1, f"Unexpected schema version: {version}"


class TestCoverageStats:  # pragma: no cover
    """Informational tests for coverage statistics."""

    @pytest.mark.skip(reason="Informational: run with -v --no-skip to see stats")
    def test_show_coverage_stats(  # noqa: PLR6301
        self, collected_options: set[str]
    ) -> None:
        """Display documentation coverage statistics."""
        all_options = get_all_canonical_options()
        documentable = all_options - EXCLUDED_FROM_DOCS
        undocumented = documentable - collected_options

        print(f"\nUndocumented options ({len(undocumented)}):")  # noqa: T201
        for opt in sorted(undocumented):
            print(f"  {opt}")  # noqa: T201

    @pytest.mark.skip(reason="Informational: run with -v --no-skip to see stats")
    def test_show_documented_options(  # noqa: PLR6301
        self, collected_options: set[str]
    ) -> None:
        """Display currently documented options."""
        print(f"\nDocumented options ({len(collected_options)}):")  # noqa: T201
        for opt in sorted(collected_options):
            meta = CLI_OPTION_META.get(opt)
            category = meta.category.value if meta else "General Options"
            print(f"  {opt} ({category})")  # noqa: T201
