"""Tests to ensure CLI_OPTION_META stays in sync with argparse.

These tests verify that:
1. All options in CLI_OPTION_META exist in argparse
2. All options in MANUAL_DOCS exist in argparse
3. There's no overlap between CLI_OPTION_META and MANUAL_DOCS
"""

from __future__ import annotations

import pytest

from datamodel_code_generator.arguments import arg_parser as argument_parser
from datamodel_code_generator.cli_options import (
    CLI_OPTION_META,
    MANUAL_DOCS,
    _canonical_option_key,
    get_all_canonical_options,
    get_canonical_option,
)


def test_get_canonical_option() -> None:
    """Test that get_canonical_option normalizes option aliases."""
    assert get_canonical_option("--help") == "--help"
    assert get_canonical_option("-h") == "--help"
    assert get_canonical_option("--input") == "--input"
    assert get_canonical_option("--unknown-option") == "--unknown-option"


class TestCLIOptionMetaSync:  # pragma: no cover
    """Synchronization tests for CLI_OPTION_META."""

    def test_all_registered_options_exist_in_argparse(self) -> None:
        """Verify that all options in CLI_OPTION_META exist in argparse."""
        argparse_options = get_all_canonical_options()
        registered = set(CLI_OPTION_META.keys())

        orphan = registered - argparse_options
        if orphan:
            pytest.fail(
                "Options in CLI_OPTION_META but not in argparse:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(orphan))
                + "\n\nRemove them from CLI_OPTION_META or add them to arguments.py."
            )

    def test_manual_doc_options_exist_in_argparse(self) -> None:
        """Verify that all options in MANUAL_DOCS exist in argparse."""
        argparse_options = get_all_canonical_options()

        orphan = MANUAL_DOCS - argparse_options
        if orphan:
            pytest.fail(
                "Options in MANUAL_DOCS but not in argparse:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(orphan))
                + "\n\nRemove them from MANUAL_DOCS or add them to arguments.py."
            )

    def test_no_overlap_between_meta_and_manual(self) -> None:
        """Verify that CLI_OPTION_META and MANUAL_DOCS don't overlap."""
        overlap = set(CLI_OPTION_META.keys()) & MANUAL_DOCS
        if overlap:
            pytest.fail(
                "Options in both CLI_OPTION_META and MANUAL_DOCS:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(overlap))
                + "\n\nAn option should be in one or the other, not both."
            )

    def test_meta_names_match_keys(self) -> None:
        """Verify that CLIOptionMeta.name matches the dict key."""
        mismatches = []
        for key, meta in CLI_OPTION_META.items():
            if key != meta.name:
                mismatches.append(f"  Key '{key}' != meta.name '{meta.name}'")

        if mismatches:
            pytest.fail("CLIOptionMeta.name mismatches:\n" + "\n".join(mismatches))

    def test_all_argparse_options_are_documented_or_excluded(self) -> None:
        """Verify that all argparse options are either documented or explicitly excluded.

        This test fails when a new CLI option is added to arguments.py
        but not added to CLI_OPTION_META or MANUAL_DOCS.
        """
        argparse_options = get_all_canonical_options()
        documented = set(CLI_OPTION_META.keys())
        manual = MANUAL_DOCS
        covered = documented | manual
        missing = argparse_options - covered

        if missing:
            pytest.fail(
                "CLI options in argparse but not in CLI_OPTION_META or MANUAL_DOCS:\n"
                + "\n".join(f"  - {opt}" for opt in sorted(missing))
                + "\n\nAdd entries to CLI_OPTION_META in cli_options.py, "
                "or add to MANUAL_DOCS if they should have manual documentation."
            )

    def test_canonical_option_determination_is_stable(self) -> None:
        """Verify that canonical option determination is deterministic.

        The canonical option should be the longest option string for each action.
        If multiple options have the same length, the lexicographically last one
        should be chosen for stability.
        """
        for action in argument_parser._actions:
            if not action.option_strings:
                continue

            sorted_opts = sorted(action.option_strings, key=_canonical_option_key)
            canonical = sorted_opts[-1]

            re_sorted = sorted(action.option_strings, key=_canonical_option_key)
            assert sorted_opts == re_sorted, f"Canonical determination is not stable for {action.option_strings}"
            assert canonical == re_sorted[-1], f"Canonical mismatch for {action.option_strings}"
