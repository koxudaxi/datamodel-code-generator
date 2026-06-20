"""Tests for generated model metadata helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import jsonschema
import pytest
from inline_snapshot import snapshot

from datamodel_code_generator import _write_model_metadata
from datamodel_code_generator.model_metadata import model_metadata_json_schema
from datamodel_code_generator.parser.base import _module_name_from_module_path, _source_path_from_reference_path
from scripts.build_model_metadata_schema import build_model_metadata_schema

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.allow_direct_assert
def test_model_metadata_source_path_from_reference_path() -> None:
    """Convert reference paths to JSON Pointer source paths when possible."""
    assert {
        "root": _source_path_from_reference_path("schema.json#"),
        "definition": _source_path_from_reference_path("schema.json#/$defs/Foo~1Bar/Tilde~0Name"),
        "plain": _source_path_from_reference_path("Foo"),
        "anchor": _source_path_from_reference_path("schema.json#Foo"),
    } == snapshot({
        "root": [],
        "definition": ["$defs", "Foo/Bar", "Tilde~Name"],
        "plain": None,
        "anchor": None,
    })


@pytest.mark.allow_direct_assert
def test_model_metadata_module_name_from_module_path() -> None:
    """Convert generated module file paths to import-style module names."""
    assert {
        "root": _module_name_from_module_path(("__init__.py",)),
        "file": _module_name_from_module_path(("models", "user.py")),
        "package": _module_name_from_module_path(("models", "__init__.py")),
        "package_name": _module_name_from_module_path(("models", "submodule")),
    } == snapshot({
        "root": "",
        "file": "models.user",
        "package": "models",
        "package_name": "models.submodule",
    })


@pytest.mark.allow_direct_assert
def test_write_model_metadata_defaults_when_metadata_is_empty(tmp_path: Path) -> None:
    """Write an empty metadata payload when no parser metadata was collected."""
    metadata_path = tmp_path / "model-map.json"

    _write_model_metadata(metadata_path, None, "utf-8")

    assert json.loads(metadata_path.read_text(encoding="utf-8")) == snapshot({
        "version": 1,
        "models": [],
    })


@pytest.mark.allow_direct_assert
def test_model_metadata_json_schema_matches_typed_dict_contract() -> None:
    """Keep the static JSON Schema in sync with the TypedDict metadata contract."""
    schema = json.loads(model_metadata_json_schema())
    generated_schema = build_model_metadata_schema()

    jsonschema.validate(instance={"version": 1, "models": []}, schema=schema)
    assert schema == generated_schema
    assert schema["$schema"] == snapshot("https://json-schema.org/draft/2020-12/schema")
    assert schema["title"] == snapshot("ModelMetadata")
