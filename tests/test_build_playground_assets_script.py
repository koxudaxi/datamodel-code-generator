from __future__ import annotations

from datamodel_code_generator.arguments import arg_parser
from scripts import build_playground_assets


def test_option_metadata_includes_docs_url() -> None:
    actions = arg_parser._actions  # noqa: SLF001
    action = next(action for action in actions if "--output-model-type" in action.option_strings)
    metadata = build_playground_assets._option_metadata(
        action,
        build_playground_assets._option_target_index(actions),
    )

    assert metadata is not None
    assert metadata["docs_url"] == "/cli-reference/model-customization/#output-model-type"


def test_option_metadata_docs_url_canonicalizes_regular_alias() -> None:
    actions = arg_parser._actions  # noqa: SLF001
    action = next(action for action in actions if "--capitalise-enum-members" in action.option_strings)
    metadata = build_playground_assets._option_metadata(
        action,
        build_playground_assets._option_target_index(actions),
    )

    assert metadata is not None
    assert metadata["name"] == "--capitalise-enum-members"
    assert metadata["docs_url"] == "/cli-reference/field-customization/#capitalize-enum-members"
