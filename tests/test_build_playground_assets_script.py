"""Tests for generated browser playground assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from datamodel_code_generator.arguments import arg_parser
from scripts import build_playground_assets
from tests.conftest import assert_output

EXPECTED_PLAYGROUND_ASSETS_PATH = Path(__file__).resolve().parent / "data" / "expected" / "playground_assets"


def test_option_metadata_docs_urls() -> None:
    """Playground option metadata links back to generated CLI docs."""
    actions = arg_parser._actions
    option_targets = build_playground_assets._option_target_index(actions)
    output = [
        _metadata_docs_summary("--output-model-type", actions, option_targets),
        _metadata_docs_summary("--capitalise-enum-members", actions, option_targets),
    ]

    assert_output(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        EXPECTED_PLAYGROUND_ASSETS_PATH / "option_docs_urls.txt",
    )


def _metadata_docs_summary(
    option: str,
    actions: list[Any],
    option_targets: dict[str, dict[str, str]],
) -> dict[str, str]:
    action = next(action for action in actions if option in action.option_strings)
    metadata = cast(
        "dict[str, Any]",
        build_playground_assets._option_metadata(action, option_targets),
    )
    return {
        "name": metadata["name"],
        "docs_url": metadata["docs_url"],
    }
