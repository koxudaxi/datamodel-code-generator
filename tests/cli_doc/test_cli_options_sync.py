"""Tests to ensure CLI_OPTION_META stays in sync with argparse.

These tests verify that:
1. All options in CLI_OPTION_META exist in argparse
2. All options in MANUAL_DOCS exist in argparse
3. There's no overlap between CLI_OPTION_META and MANUAL_DOCS
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import pytest

from datamodel_code_generator import cli_options
from datamodel_code_generator.arguments import arg_parser as argument_parser
from datamodel_code_generator.cli_options import (
    CLI_OPTION_META,
    MANUAL_DOCS,
    OPTION_RELATION_KINDS,
    OPTION_TOPIC_ALLOWED_GROUPS,
    CLIOptionMeta,
    OptionCategory,
    OptionGroup,
    OptionTopic,
    _canonical_option_key,
    get_all_argparse_options,
    get_all_canonical_options,
    get_canonical_option,
    get_option_meta,
    is_excluded_from_docs,
    is_manual_doc,
)
from scripts import build_cli_docs
from scripts.build_cli_docs import (
    CLIDocExample,
    CLIDocOption,
    _documented_related_option,
    _format_option_link,
    generate_option_section,
    scan_docs_for_cli_option_tags,
)

if TYPE_CHECKING:
    from collections.abc import Collection

_T = TypeVar("_T")


def _fail_if_not_equal(actual: _T, expected: _T, context: str) -> None:
    if actual != expected:
        pytest.fail(f"{context}: expected {expected!r}, got {actual!r}")


def _fail_if_missing(item: _T, collection: Collection[_T], context: str) -> None:
    if item not in collection:
        pytest.fail(f"{context}: expected {item!r} in {collection!r}")


def _fail_if_present(item: _T, collection: Collection[_T], context: str) -> None:
    if item in collection:
        pytest.fail(f"{context}: expected {item!r} not to be present in {collection!r}")


def test_get_canonical_option() -> None:
    """Test that get_canonical_option normalizes option aliases."""
    assert get_canonical_option("--help") == "--help"
    assert get_canonical_option("-h") == "--help"
    assert get_canonical_option("--input") == "--input"
    assert get_canonical_option("--unknown-option") == "--unknown-option"


def test_is_manual_doc() -> None:
    """Test that is_manual_doc detects manual documentation options."""
    assert is_manual_doc("--help") is True
    assert is_manual_doc("-h") is True
    assert is_manual_doc("--input") is False
    assert is_manual_doc("--unknown-option") is False


def test_is_excluded_from_docs() -> None:
    """Test that is_excluded_from_docs remains compatible with manual docs."""
    assert is_excluded_from_docs("--help") is True
    assert is_excluded_from_docs("-h") is True
    assert is_excluded_from_docs("--input") is False
    assert is_excluded_from_docs("--unknown-option") is False


def test_get_option_meta() -> None:
    """Test that get_option_meta returns explicit, canonical, and empty metadata."""
    assert get_option_meta("--use-annotated") is CLI_OPTION_META["--use-annotated"]
    assert get_option_meta("--treat-dot-as-module") is CLI_OPTION_META["--no-treat-dot-as-module"]
    assert get_option_meta("--help") is None
    assert get_option_meta("-h") is None
    assert get_option_meta("--unknown-option") is None


def test_get_option_meta_returns_default_for_known_argparse_option(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_option_meta auto-categorizes known argparse options without metadata."""
    option = "--future-option"

    def get_future_options() -> frozenset[str]:
        return frozenset({option})

    monkeypatch.setattr(cli_options, "get_all_canonical_options", get_future_options)

    assert get_option_meta(option) == CLIOptionMeta(name=option, category=OptionCategory.GENERAL)


def test_documented_related_option_prefers_existing_generated_section() -> None:
    """Related links should target generated sections, not argparse's longest alias."""
    documented_options = frozenset({
        "--collapse-root-models",
        "--no-use-union-operator",
        "--snake-case-field",
    })

    _fail_if_not_equal(
        _documented_related_option("--collapse-root-models", documented_options),
        "--collapse-root-models",
        "--collapse-root-models related option target",
    )
    _fail_if_not_equal(
        _documented_related_option("--snake-case-field", documented_options),
        "--snake-case-field",
        "--snake-case-field related option target",
    )
    _fail_if_not_equal(
        _documented_related_option("--use-union-operator", documented_options),
        "--no-use-union-operator",
        "--use-union-operator related option target",
    )


def test_related_page_tags_prefer_existing_generated_section() -> None:
    """Related page tags should keep links on generated positive BooleanOptionalAction sections."""
    documented_options = frozenset({
        "--collapse-root-models",
        "--disable-warnings",
        "--reuse-model",
        "--reuse-scope",
        "--shared-module-name",
        "--use-type-alias",
    })

    option_related_pages = scan_docs_for_cli_option_tags(documented_options)

    _fail_if_missing(
        ("model-reuse.md", "Model Reuse and Deduplication"),
        option_related_pages["--collapse-root-models"],
        "--collapse-root-models related page",
    )
    _fail_if_present(
        "--no-collapse-root-models",
        option_related_pages,
        "--no-collapse-root-models related page key",
    )


def test_format_option_link_uses_current_category_anchor() -> None:
    """Recipe links should stay on-page when the option belongs to the current category."""
    documented_options = frozenset({"--input", "--target-python-version", "--unknown-option"})

    assert _format_option_link("--input", documented_options, current_category=OptionCategory.BASE) == (
        "[`--input`](#input)"
    )
    assert (
        _format_option_link(
            "--target-python-version",
            documented_options,
            current_category=OptionCategory.TYPING,
        )
        == "[`--target-python-version`](model-customization.md#target-python-version)"
    )
    assert _format_option_link("--unknown-option", documented_options) == "`--unknown-option`"


def test_related_option_links_use_current_category_anchor() -> None:
    """Related option links should stay on-page when the option belongs to the current category."""
    option = build_cli_docs.CLIDocOption(
        option_name="--input",
        examples=[
            build_cli_docs.CLIDocExample(
                node_id="tests/test_cli_doc.py::test_input",
                option_description="Specify the input schema file path.",
                cli_args=["--input", "schema.json"],
                related_options=["--input-file-type", "--target-python-version"],
                is_primary=True,
            )
        ],
    )

    section = build_cli_docs.generate_option_section(
        "--input",
        option,
        documented_options=frozenset({"--input", "--input-file-type", "--target-python-version"}),
    )

    _fail_if_missing(
        "**Related:** [`--input-file-type`](#input-file-type), "
        "[`--target-python-version`](model-customization.md#target-python-version)",
        section,
        "--input related option links",
    )


def test_category_recipe_options_have_registered_metadata() -> None:
    """Generated recipes should not point at stale CLI option names."""
    for category, recipes in build_cli_docs.CATEGORY_RECIPES.items():
        assert isinstance(category, OptionCategory)
        assert recipes
        for recipe in recipes:
            assert recipe.options
            for option in recipe.options:
                assert get_option_meta(option) is not None


def test_category_recipes_render_before_option_details(monkeypatch: pytest.MonkeyPatch) -> None:
    """Recipe sections should sit between the category option table and detailed option sections."""
    monkeypatch.setattr(
        build_cli_docs,
        "CATEGORY_RECIPES",
        {
            OptionCategory.BASE: (
                build_cli_docs.CategoryRecipe(
                    title="Read a schema",
                    description="Choose the schema and destination.",
                    options=("--input",),
                ),
            )
        },
    )
    option = build_cli_docs.CLIDocOption(
        option_name="--input",
        examples=[
            build_cli_docs.CLIDocExample(
                node_id="tests/test_cli_doc.py::test_input",
                option_description="Specify the input schema file path.",
                cli_args=["--input", "schema.json"],
                is_primary=True,
            )
        ],
    )

    page = build_cli_docs.generate_category_page(
        OptionCategory.BASE,
        {"--input": option},
        documented_options=frozenset({"--input"}),
    )

    assert "Recipes" in page
    assert page.index("Recipes") < page.index("## `--input`")
    assert "**Options:** [`--input`](#input)" in page


def test_category_page_omits_recipes_without_category_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Categories without recipe data should keep the previous option-table-to-details shape."""
    monkeypatch.setattr(build_cli_docs, "CATEGORY_RECIPES", {})
    option = build_cli_docs.CLIDocOption(
        option_name="--input",
        examples=[
            build_cli_docs.CLIDocExample(
                node_id="tests/test_cli_doc.py::test_input",
                option_description="Specify the input schema file path.",
                cli_args=["--input", "schema.json"],
                is_primary=True,
            )
        ],
    )

    page = build_cli_docs.generate_category_page(
        OptionCategory.BASE,
        {"--input": option},
        documented_options=frozenset({"--input"}),
    )

    assert "Recipes" not in page
    assert page.index("---") < page.index("## `--input`")


def test_option_section_renders_implies_and_requires_metadata() -> None:
    """Generated option docs should include relationship metadata from CLIOptionMeta."""
    section = generate_option_section(
        "--use-missing-sentinel",
        CLIDocOption(
            option_name="--use-missing-sentinel",
            examples=[
                CLIDocExample(
                    node_id="tests/cli_doc/test_cli_options_sync.py::test_use_missing_sentinel",
                    option_description="Use missing sentinel.",
                    cli_args=["--use-missing-sentinel"],
                    is_primary=True,
                ),
            ],
        ),
        documented_options=frozenset({
            "--output-model-type",
            "--target-pydantic-version",
            "--use-missing-sentinel",
        }),
    )

    assert "**Option relationships:**" in section
    assert (
        "- **Implies:** [`--target-pydantic-version`](model-customization.md#target-pydantic-version) = `2.12`"
        in section
    )
    assert (
        "- **Requires:** [`--output-model-type`](model-customization.md#output-model-type) = "
        "`pydantic_v2.BaseModel` - `--use-missing-sentinel` is only supported for "
        "`--output-model-type pydantic_v2.BaseModel`." in section
    )


def test_option_section_renders_conditional_requires_metadata() -> None:
    """Relationship metadata should include source option value conditions."""
    section = generate_option_section(
        "--reuse-scope",
        CLIDocOption(
            option_name="--reuse-scope",
            examples=[
                CLIDocExample(
                    node_id="tests/cli_doc/test_cli_options_sync.py::test_reuse_scope",
                    option_description="Scope reuse.",
                    cli_args=["--reuse-scope", "tree"],
                    is_primary=True,
                ),
            ],
        ),
        documented_options=frozenset({"--reuse-model", "--reuse-scope"}),
    )

    assert (
        "- **Requires:** When `--reuse-scope=tree`, "
        "[`--reuse-model`](model-customization.md#reuse-model) enabled - "
        "`--reuse-scope=tree` has no effect without `--reuse-model`." in section
    )


def test_option_section_renders_conflicts_metadata() -> None:
    """Generated option docs should include conflict metadata from CLIOptionMeta."""
    section = generate_option_section(
        "--custom-file-header",
        CLIDocOption(
            option_name="--custom-file-header",
            examples=[
                CLIDocExample(
                    node_id="tests/cli_doc/test_cli_options_sync.py::test_custom_file_header",
                    option_description="Custom header.",
                    cli_args=["--custom-file-header", "# Header"],
                    is_primary=True,
                ),
            ],
        ),
        documented_options=frozenset({"--custom-file-header", "--custom-file-header-path"}),
    )

    assert (
        "- **Conflicts:** [`--custom-file-header-path`](template-customization.md#custom-file-header-path) - "
        "`--custom-file-header` can not be used with `--custom-file-header-path`." in section
    )


class TestCLIOptionMetaSync:
    """Synchronization tests for CLI_OPTION_META."""

    def test_all_registered_options_exist_in_argparse(self) -> None:
        """Verify that all options in CLI_OPTION_META exist in argparse."""
        # Use all argparse options (including aliases) because CLI_OPTION_META
        # may contain both --use-* and --no-use-* variants for BooleanOptionalAction
        argparse_options = get_all_argparse_options()
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

    def test_option_relations_reference_argparse_options(self) -> None:
        """Verify that option relation metadata points at real argparse options."""
        argparse_options = get_all_argparse_options()
        missing = [
            f"  {source} {relation_kind} {relation.option}"
            for source, meta in CLI_OPTION_META.items()
            for relation_kind in OPTION_RELATION_KINDS
            for relation in getattr(meta, relation_kind)
            if relation.option not in argparse_options
        ]

        if missing:
            pytest.fail(
                "CLI option relation targets missing from argparse:\n"
                + "\n".join(sorted(missing))
                + "\n\nRemove the relation or add the target option to arguments.py."
            )

    def test_option_topic_and_group_are_known_and_non_empty(self) -> None:
        """Verify that optional topic/group metadata uses known non-empty values."""
        for attr, enum_type in (("topic", OptionTopic), ("group", OptionGroup)):
            for option, meta in CLI_OPTION_META.items():
                if (value := getattr(meta, attr)) is None:
                    continue
                if not isinstance(value, enum_type):
                    pytest.fail(f"{option} {attr} must be an {enum_type.__name__}, got {value!r}")
                if not value.value:
                    pytest.fail(f"{option} {attr} value must not be empty")

    def test_option_topic_groups_are_allowed(self) -> None:
        """Verify that topic metadata only uses groups allowed for that topic."""
        for option, meta in CLI_OPTION_META.items():
            if (topic := meta.topic) is None:
                continue
            if (group := meta.group) is None:
                pytest.fail(f"{option} topic {topic.value!r} must also set a group")
            if (allowed_groups := OPTION_TOPIC_ALLOWED_GROUPS.get(topic)) is None:
                pytest.fail(f"{option} topic has no allowed groups: {topic.value!r}")
            _fail_if_missing(
                group,
                allowed_groups,
                f"{option} group for topic {topic.value!r}",
            )

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
