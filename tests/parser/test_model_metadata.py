"""Tests for generated model metadata helpers."""

from __future__ import annotations

import json
from pathlib import Path

from datamodel_code_generator.model_metadata import dump_model_metadata
from datamodel_code_generator.parser.base import _module_name_from_module_path, _source_path_from_reference_path
from tests.conftest import assert_output

EXPECTED_MODEL_METADATA_PATH = Path(__file__).parents[1] / "data" / "expected" / "parser" / "model_metadata"


def _dump_json_payload(value: object) -> str:
    return f"{json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)}\n"


def test_dump_model_metadata_accepts_empty_payload() -> None:
    """None metadata is emitted as an empty metadata payload."""
    assert_output(
        f"{dump_model_metadata(None)}\n",
        EXPECTED_MODEL_METADATA_PATH / "empty_model_metadata.txt",
    )


def test_model_metadata_path_helpers() -> None:
    """Reference paths and module paths are normalized for metadata output."""
    assert_output(
        _dump_json_payload({
            "module_names": {
                "package_file": _module_name_from_module_path(("models", "user.py")),
                "package_init": _module_name_from_module_path(("models", "__init__.py")),
                "package_name": _module_name_from_module_path(("models", "user")),
                "root_init": _module_name_from_module_path(("__init__.py",)),
                "single_file": _module_name_from_module_path(("models.py",)),
            },
            "source_paths": {
                "empty_fragment": _source_path_from_reference_path("schema.json#"),
                "escaped_fragment": _source_path_from_reference_path("schema.json#/$defs/foo~1bar/tilde~0key"),
                "no_fragment": _source_path_from_reference_path("User"),
                "relative_fragment": _source_path_from_reference_path("schema.json#User"),
            },
        }),
        EXPECTED_MODEL_METADATA_PATH / "path_helpers.txt",
    )
