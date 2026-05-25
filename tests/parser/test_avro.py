"""Tests for Avro schema parser internals."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from datamodel_code_generator import Error
from datamodel_code_generator.parser.avro import (
    _AvroSchemaConverter,
    _Name,
    _namespace_name,
    _to_class_title,
    is_avro_schema_data,
    is_avro_schema_text,
)
from datamodel_code_generator.parser.base import Source


def _source(raw_data: dict[str, Any] | None = None, text: str = "") -> Source:
    return Source(path=Path(), text=text, raw_data=raw_data)


def test_avro_schema_detection_edges() -> None:
    """Detect Avro schemas without confusing JSON Schema unions for Avro unions."""
    assert is_avro_schema_data("string")
    assert not is_avro_schema_data(1)
    assert not is_avro_schema_data({"type": ["null", "string"]})
    assert is_avro_schema_data({"type": {"type": "record", "name": "Nested", "fields": []}})
    assert is_avro_schema_data({"type": "enum", "name": "Suit", "symbols": ["SPADES"]})
    assert is_avro_schema_data({"type": "fixed", "name": "Md5", "size": 16})
    assert is_avro_schema_data({"type": "map", "values": "string"})
    assert is_avro_schema_data(["null", {"type": "record", "name": "UnionRecord", "fields": []}, "example.Ref"])
    assert is_avro_schema_data([["null", "string"]])
    assert is_avro_schema_data([{"type": ["null", "string"]}])
    assert is_avro_schema_data([{"type": {"type": "string"}}])
    assert is_avro_schema_data([{"type": "enum", "name": "UnionEnum", "symbols": ["A"]}])
    assert is_avro_schema_data([{"type": "fixed", "name": "UnionFixed", "size": 8}])
    assert is_avro_schema_data([{"type": "array", "items": "string"}])
    assert is_avro_schema_data([{"type": "map", "values": "string"}])
    assert is_avro_schema_data([{"type": "example.Ref"}])
    assert not is_avro_schema_data([1])
    assert not is_avro_schema_data(["Custom"])
    assert not is_avro_schema_data([{"not": "a schema"}])
    assert not is_avro_schema_text("{")
    assert is_avro_schema_text('"string"')


def test_avro_name_helpers() -> None:
    """Normalize Avro names and namespaces into JSON Schema definition titles."""
    assert _to_class_title("bad-name") == "BadName"
    assert _namespace_name(None) == "NoNamespace"
    assert _namespace_name("!!!") == "Namespace"


def test_avro_convert_wraps_root_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep a generated root $ref importable by adding the standard title."""
    converter = _AvroSchemaConverter()

    def convert_ref(*args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG001
        return {"$ref": "#/definitions/Reference"}

    monkeypatch.setattr(converter, "_convert_schema", convert_ref)

    assert converter.convert(_source({})) == {
        "$ref": "#/definitions/Reference",
        "title": "Model",
        "$schema": "http://json-schema.org/draft-07/schema#",
    }


def test_avro_collect_named_schema_edges() -> None:
    """Collect nested named schemas and reject invalid Avro named declarations."""
    converter = _AvroSchemaConverter()
    converter._collect_named_schemas(1)
    converter._collect_named_schemas({"type": [{"type": "record", "name": "FromUnion", "fields": []}]})
    converter._collect_named_schemas({"type": {"type": "record", "name": "FromObject", "fields": []}})
    converter._collect_named_schemas({"type": "record", "name": "SkipInvalidNested", "fields": [1]})
    assert set(converter.named_schemas) == {"FromUnion", "FromObject", "SkipInvalidNested"}

    with pytest.raises(Error, match="requires a string name"):
        _AvroSchemaConverter()._collect_named_schemas({"type": "record", "fields": []})

    with pytest.raises(Error, match="Duplicate Avro named type"):
        _AvroSchemaConverter()._collect_named_schemas([
            {"type": "record", "name": "Duplicate", "fields": []},
            {"type": "record", "name": "Duplicate", "fields": []},
        ])

    with pytest.raises(Error, match="fields must be a list"):
        _AvroSchemaConverter()._collect_named_schemas({"type": "record", "name": "Broken", "fields": {}})


def test_avro_definition_name_suffix_collision() -> None:
    """Avoid definition title collisions after Avro names are converted to Python class names."""
    converter = _AvroSchemaConverter()
    converter._collect_named_schemas([
        {"type": "record", "name": "A", "fields": []},
        {"type": "record", "name": "a", "fields": []},
    ])
    converter._prepare_definition_names()

    assert set(converter.definition_names.values()) == {"A", "A2"}


def test_avro_convert_schema_branch_edges() -> None:
    """Cover Avro schema object forms that are rare in end-to-end fixtures."""
    converter = _AvroSchemaConverter()

    with pytest.raises(Error, match="Unsupported Avro schema value"):
        converter._convert_schema(1, namespace=None)

    nullable = converter._convert_schema({"type": ["null", "string"], "doc": "Nullable value"}, namespace=None)
    assert nullable == {
        "anyOf": [{"type": "null"}, {"type": "string"}],
        "description": "Nullable value",
    }

    uuid = converter._convert_schema({"type": {"type": "string", "logicalType": "uuid"}}, namespace=None)
    assert uuid == {"type": "string", "format": "uuid", "x-avro-logicalType": "uuid"}

    decimal_string = converter._convert_schema({"type": "string", "logicalType": "decimal"}, namespace=None)
    assert decimal_string == {"type": "string", "x-avro-logicalType": "decimal"}

    decimal_bytes = converter._convert_schema({"type": "bytes", "logicalType": "decimal"}, namespace=None)
    assert decimal_bytes == {"type": "string", "format": "decimal", "x-avro-logicalType": "decimal"}

    with pytest.raises(Error, match="requires a string, object, or union type"):
        converter._convert_schema({}, namespace=None)


def test_avro_root_enum_fixed_and_reference_edges() -> None:
    """Build root enum/fixed schemas and resolve references by fullname."""
    enum_schema = _AvroSchemaConverter().convert(
        _source({"type": "enum", "name": "Suit", "symbols": ["SPADES"], "default": "SPADES"})
    )
    assert enum_schema["title"] == "Suit"
    assert enum_schema["default"] == "SPADES"
    assert _AvroSchemaConverter()._convert_enum({"symbols": ["SPADES"]}, "NoDefault") == {
        "type": "string",
        "enum": ["SPADES"],
        "x-avro-fullname": "NoDefault",
    }

    fixed_schema = _AvroSchemaConverter().convert(
        _source({"type": "fixed", "name": "example.Md5", "size": 16, "logicalType": "duration"})
    )
    assert fixed_schema["title"] == "Md5"
    assert fixed_schema["x-avro-fullname"] == "example.Md5"
    assert fixed_schema["format"] == "duration"

    converter = _AvroSchemaConverter()
    converter.convert(
        _source(
            text='[{"type": "record", "name": "Known", "fields": []}, {"type": "Known"}]',
        )
    )
    assert set(converter.definitions) == {"Known"}
    assert converter._build_definition("Known")["title"] == "Known"

    with pytest.raises(Error, match="Unknown Avro named type reference"):
        _AvroSchemaConverter()._convert_type_name("missing.Type", namespace=None)

    with pytest.raises(Error, match="Unknown Avro named type reference"):
        _AvroSchemaConverter()._convert_type_name("Missing", namespace=None)

    assert _AvroSchemaConverter()._resolve_fullname("Missing", namespace="example") == "Missing"


def test_avro_record_field_and_error_edges() -> None:
    """Preserve record field metadata and reject malformed record fields."""
    record_schema = _AvroSchemaConverter().convert(
        _source({
            "type": "record",
            "name": "Order",
            "doc": "Order doc",
            "aliases": ["Purchase"],
            "fields": [
                {
                    "name": "id",
                    "type": "string",
                    "doc": "Identifier",
                    "aliases": ["order_id"],
                    "order": "ignore",
                    "default": "0",
                }
            ],
        })
    )
    field_schema = record_schema["properties"]["id"]
    assert record_schema["description"] == "Order doc"
    assert record_schema["x-avro-aliases"] == ["Purchase"]
    assert field_schema["description"] == "Identifier"
    assert field_schema["x-avro-aliases"] == ["order_id"]
    assert field_schema["x-avro-order"] == "ignore"
    assert field_schema["default"] == "0"

    converter = _AvroSchemaConverter()
    converter.names["Broken"] = _Name(fullname="Broken", namespace=None, name="Broken")
    with pytest.raises(Error, match="fields must be a list"):
        converter._convert_record({"fields": {}}, "Broken")

    with pytest.raises(Error, match="field requires a string name"):
        _AvroSchemaConverter().convert(
            _source({"type": "record", "name": "BrokenField", "fields": [{"type": "string"}]})
        )

    with pytest.raises(Error, match="enum symbols must be a list of strings"):
        _AvroSchemaConverter()._convert_enum({"symbols": [1]}, "BadEnum")

    with pytest.raises(Error, match="fixed size must be an integer"):
        _AvroSchemaConverter()._convert_fixed({"size": "large"}, "BadFixed")

    with pytest.raises(Error, match="requires a string name"):
        _AvroSchemaConverter()._convert_schema({"type": "enum", "symbols": []}, namespace=None)
