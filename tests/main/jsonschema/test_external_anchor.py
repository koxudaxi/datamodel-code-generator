"""Regression coverage for external JSON Schema anchors."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import Error
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from datamodel_code_generator.reference import ModelResolver
from tests.conftest import assert_output
from tests.main.conftest import JSON_SCHEMA_DATA_PATH, run_main_and_assert
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH, assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


def test_main_jsonschema_external_anchor_with_legacy_shorthand(output_file: Path) -> None:
    """Resolve external anchors without regressing legacy shorthand JSON pointers."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_anchor" / "root.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="external_anchor.py",
        extra_args=["--disable-timestamp", "--target-python-version", "3.10"],
        force_exec_validation=True,
    )


def test_main_jsonschema_malformed_external_ref_is_wrapped(
    capsys: pytest.CaptureFixture[str], output_file: Path
) -> None:
    """Report malformed external references as generator errors."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "external_ref_errors" / "malformed.json",
        output_path=output_file,
        input_file_type="jsonschema",
        expected_exit=Exit.ERROR,
    )
    assert_output(capsys.readouterr().err, EXPECTED_JSON_SCHEMA_PATH / "malformed_external_ref.txt")


def test_jsonschema_malformed_anchor_ref_is_rejected_during_type_resolution() -> None:
    """Reject multi-fragment external refs before fetching their external target."""
    source = JSON_SCHEMA_DATA_PATH / "external_ref_errors" / "malformed_anchor.json"
    ref = json.loads(source.read_text(encoding="utf-8"))["properties"]["value"]["$ref"]
    parser = JsonSchemaParser(source, base_path=source.parent)

    with pytest.raises(Error) as exception_info:
        parser.get_ref_data_type(ref)

    assert_output(f"{exception_info.value}\n", EXPECTED_JSON_SCHEMA_PATH / "malformed_anchor_external_ref.txt")


def test_model_resolver_uses_cached_external_anchor_from_schema_fixture() -> None:
    """Reuse an external $anchor registered while parsing its schema document."""
    source = JSON_SCHEMA_DATA_PATH / "external_anchor" / "child.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    definition_name, definition = next(iter(document["$defs"].items()))
    anchor = definition["$anchor"]
    resolver = ModelResolver(base_url="https://example.test/root.json")
    resolver.set_current_root([source.name])
    resolver.add_id(f"#{anchor}", ["#", "$defs", definition_name])

    cached_result = resolver.resolve_ref(f"{source.name}#{anchor}")
    local_result = resolver.resolve_ref(f"#{anchor}")

    assert_output(f"{cached_result}\n{local_result}\n", EXPECTED_JSON_SCHEMA_PATH / "cached_external_anchor_ref.txt")
