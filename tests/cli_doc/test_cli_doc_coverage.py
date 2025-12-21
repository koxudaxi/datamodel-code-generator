"""Tests to track CLI documentation coverage.

These tests verify that all CLI options (defined in arguments.py) have
a cli_doc marker in tests (unless in MANUAL_DOCS).

This ensures that every CLI option has corresponding test documentation.
"""

from __future__ import annotations

from typing import Any

import pytest

from datamodel_code_generator.cli_options import (
    CLI_OPTION_META,
    MANUAL_DOCS,
    get_all_canonical_options,
    get_canonical_option,
)


@pytest.fixture(scope="module")
def collected_options(request: pytest.FixtureRequest) -> set[str]:  # pragma: no cover
    """Extract canonical options from collected cli_doc markers.

    Uses config._cli_doc_items populated by conftest.py during test collection.
    """
    items: list[dict[str, Any]] = getattr(request.config, "_cli_doc_items", [])
    options: set[str] = set()
    for item in items:
        marker_options = item.get("marker_kwargs", {}).get("options", [])
        if not isinstance(marker_options, list):
            continue
        options.update(get_canonical_option(opt) for opt in marker_options if isinstance(opt, str))
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
