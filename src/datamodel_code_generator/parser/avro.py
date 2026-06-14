"""Apache Avro schema parser implementation.

Converts Avro JSON schemas into the JSON Schema shape consumed by the existing
JSON Schema parser while preserving Avro named type and logical type semantics.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from typing_extensions import Unpack

from datamodel_code_generator import Error, YamlValue, load_yaml
from datamodel_code_generator.parser import _avro_detection
from datamodel_code_generator.parser._avro_detection import (
    NAMED_TYPES,
    PRIMITIVE_TYPES,
)
from datamodel_code_generator.parser._avro_detection import (
    is_avro_schema_data as _is_avro_schema_data,
)
from datamodel_code_generator.parser._convert_common import _copy_schema, _namespace_name, _unique_name
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

if TYPE_CHECKING:
    from pathlib import Path
    from urllib.parse import ParseResult

    from datamodel_code_generator._types import AvroParserConfigDict
    from datamodel_code_generator.config import AvroParserConfig
    from datamodel_code_generator.parser.base import Source

JsonSchema = dict[str, Any]

NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

STRING_SCHEMA: JsonSchema = {"type": "string"}
NULL_SCHEMA: JsonSchema = {"type": "null"}
BOOLEAN_SCHEMA: JsonSchema = {"type": "boolean"}
BYTES_SCHEMA: JsonSchema = {"type": "string", "format": "binary"}

PRIMITIVE_SCHEMAS: dict[str, JsonSchema] = {
    "null": NULL_SCHEMA,
    "boolean": BOOLEAN_SCHEMA,
    "int": {"type": "integer", "format": "int32"},
    "long": {"type": "integer", "format": "int64"},
    "float": {"type": "number", "format": "float"},
    "double": {"type": "number", "format": "double"},
    "bytes": BYTES_SCHEMA,
    "string": STRING_SCHEMA,
}


def is_avro_schema_data(data: YamlValue) -> bool:
    """Return whether loaded data appears to be an Avro schema."""
    return _is_avro_schema_data(data)


def __getattr__(name: str) -> Any:
    """Return compatibility constants moved to the lightweight detector."""
    match name:
        case "COMPLEX_TYPES":
            return _avro_detection.COMPLEX_TYPES
        case "JSON_SCHEMA_MARKER_KEYS":
            return _avro_detection.JSON_SCHEMA_MARKER_KEYS
    raise AttributeError(name)


class _Name(NamedTuple):
    fullname: str
    namespace: str | None
    name: str


def _to_class_title(name: str) -> str:
    return f"{name[:1].upper()}{name[1:]}"


def _is_valid_name(name: str) -> bool:
    return bool(NAME_PATTERN.fullmatch(name))


def _is_valid_fullname(name: str) -> bool:
    return all(_is_valid_name(part) for part in name.split("."))


def _is_valid_namespace(namespace: str) -> bool:
    return not namespace or _is_valid_fullname(namespace)


class _AvroSchemaConverter:
    def __init__(self) -> None:
        self.named_schemas: dict[str, JsonSchema] = {}
        self.names: dict[str, _Name] = {}
        self.definition_names: dict[str, str] = {}
        self.definitions: dict[str, JsonSchema] = {}
        self._building_definitions: set[str] = set()

    def convert_raw(self, raw_obj: YamlValue) -> dict[str, YamlValue]:
        self._collect_named_schemas(raw_obj)
        self._prepare_definition_names()
        schema = self._convert_schema(raw_obj, namespace=None, root=True)
        schema.setdefault("title", "Model")
        if self.definitions:
            schema["definitions"] = self.definitions
        schema.setdefault("$schema", "http://json-schema.org/draft-07/schema#")
        return cast("dict[str, YamlValue]", schema)

    def convert(self, source: Source) -> dict[str, YamlValue]:
        raw_obj = source.raw_data if source.raw_data is not None else load_yaml(source.text)
        return self.convert_raw(raw_obj)

    def _collect_named_schemas(self, schema: YamlValue, namespace: str | None = None) -> None:
        match schema:
            case [*_] as union:
                self._collect_schema_items(union, namespace)
                return
            case dict() as schema:
                pass
            case _:
                return

        type_value = schema.get("type")
        match type_value:
            case [*_] as union:
                self._collect_schema_items(union, namespace)
                return
            case dict() as nested_schema:
                self._collect_named_schemas(nested_schema, namespace)
                return
            case str() as type_name:
                child_namespace = self._register_named_schema(schema, type_name, namespace)
                self._collect_schema_children(schema, type_name, child_namespace)

    def _collect_schema_items(self, schemas: list[YamlValue], namespace: str | None) -> None:
        for schema in schemas:
            self._collect_named_schemas(schema, namespace)

    def _register_named_schema(self, schema: JsonSchema, type_name: str, namespace: str | None) -> str | None:
        if type_name not in NAMED_TYPES:
            return namespace

        name = schema.get("name")
        if not isinstance(name, str):
            msg = f"Avro {type_name} schema requires a string name"
            raise Error(msg)
        if not _is_valid_fullname(name):
            msg = f"Invalid Avro {type_name} name: {name}"
            raise Error(msg)
        if name.rsplit(".", maxsplit=1)[-1] in PRIMITIVE_TYPES:
            msg = f"Avro primitive type names may not be redefined: {name}"
            raise Error(msg)
        namespace_value = schema.get("namespace")
        if "." not in name and isinstance(namespace_value, str) and not _is_valid_namespace(namespace_value):
            msg = f"Invalid Avro namespace: {namespace_value}"
            raise Error(msg)
        name_info = self._make_name(name, schema.get("namespace"), namespace)
        if (existing := self.named_schemas.get(name_info.fullname)) is not None and existing is not schema:
            msg = f"Duplicate Avro named type: {name_info.fullname}"
            raise Error(msg)
        self.named_schemas[name_info.fullname] = schema
        self.names[name_info.fullname] = name_info
        return name_info.namespace

    def _collect_schema_children(self, schema: JsonSchema, type_name: str, namespace: str | None) -> None:
        match type_name:
            case "record":
                fields = schema.get("fields", [])
                if not isinstance(fields, list):
                    msg = f"Avro record fields must be a list: {schema.get('name')}"
                    raise Error(msg)
                for field in fields:
                    if isinstance(field, dict):
                        self._collect_named_schemas(field.get("type"), namespace)
            case "array":
                self._collect_named_schemas(schema.get("items"), namespace)
            case "map":
                self._collect_named_schemas(schema.get("values"), namespace)

    def _prepare_definition_names(self) -> None:
        fullnames_by_local: dict[str, list[str]] = {}
        for fullname, name_info in self.names.items():
            fullnames_by_local.setdefault(name_info.name.rsplit(".", maxsplit=1)[-1], []).append(fullname)

        used_names: set[str] = set()
        for local, fullnames in sorted(fullnames_by_local.items()):
            for fullname in sorted(fullnames):
                name_info = self.names[fullname]
                name = (
                    _to_class_title(local)
                    if len(fullnames) == 1
                    else f"{_namespace_name(name_info.namespace, _to_class_title)}{_to_class_title(local)}"
                )
                candidate = _unique_name(name, used_names)
                self.definition_names[fullname] = candidate
                used_names.add(candidate)

    def _convert_schema(
        self,
        schema: YamlValue,
        namespace: str | None,
        *,
        root: bool = False,
    ) -> JsonSchema:
        match schema:
            case str() as type_name:
                return self._convert_type_name(type_name, namespace)
            case [*_] as union:
                return self._convert_union(union, namespace)
            case dict() as schema:
                return self._convert_schema_dict(schema, namespace, root=root)

        msg = f"Unsupported Avro schema value: {schema!r}"
        raise Error(msg)

    def _convert_schema_dict(
        self,
        schema: JsonSchema,
        namespace: str | None,
        *,
        root: bool,
    ) -> JsonSchema:
        match schema.get("type"):
            case [*_] as union:
                converted = self._convert_union(union, namespace)
                self._copy_common_metadata(schema, converted)
                return converted
            case dict() as nested_schema:
                converted = self._convert_schema(nested_schema, namespace, root=root)
                self._copy_common_metadata(schema, converted)
                return converted
            case str() as type_name:
                return self._convert_schema_object(schema, type_name, namespace, root=root)
            case _:
                msg = f"Avro schema object requires a string, object, or union type: {schema!r}"
                raise Error(msg)

    def _convert_schema_object(
        self,
        schema: JsonSchema,
        type_name: str,
        namespace: str | None,
        *,
        root: bool,
    ) -> JsonSchema:
        match type_name:
            case type_name if type_name in PRIMITIVE_TYPES:
                converted = _copy_schema(PRIMITIVE_SCHEMAS[type_name])
                self._copy_common_metadata(schema, converted)
                return self._apply_logical_type(schema, converted, avro_type=type_name)
            case "record" | "enum" | "fixed":
                fullname = self._fullname_from_named_schema(schema, namespace)
                if root:
                    return self._build_definition(fullname, as_root=True)
                self._ensure_definition(fullname)
                return {"$ref": self._ref(fullname)}
            case "array":
                converted = {"type": "array", "items": self._convert_schema(schema.get("items"), namespace)}
                self._copy_common_metadata(schema, converted)
                return converted
            case "map":
                converted = {
                    "type": "object",
                    "additionalProperties": self._convert_schema(schema.get("values"), namespace),
                }
                self._copy_common_metadata(schema, converted)
                return converted
        return self._convert_type_name(type_name, namespace)

    def _convert_type_name(self, name: str, namespace: str | None) -> JsonSchema:
        if name in PRIMITIVE_TYPES:
            return _copy_schema(PRIMITIVE_SCHEMAS[name])
        fullname = self._resolve_fullname(name, namespace)
        self._ensure_definition(fullname)
        return {"$ref": self._ref(fullname)}

    def _convert_union(self, union: list[YamlValue], namespace: str | None) -> JsonSchema:
        self._validate_union(union)
        return {"anyOf": [self._convert_schema(item, namespace) for item in union]}

    @staticmethod
    def _validate_union(union: list[YamlValue]) -> None:
        seen_unnamed_types: set[str] = set()
        for item in union:
            if isinstance(item, list):
                msg = "Avro unions may not immediately contain other unions"
                raise Error(msg)
            if isinstance(item, str):
                union_type = item if item in PRIMITIVE_TYPES else None
            elif isinstance(item, dict):
                type_value = item.get("type")
                if isinstance(type_value, list):
                    msg = "Avro unions may not immediately contain other unions"
                    raise Error(msg)
                union_type = type_value if isinstance(type_value, str) and type_value not in NAMED_TYPES else None
            else:
                msg = f"Unsupported Avro union value: {item!r}"
                raise Error(msg)

            if union_type is None or union_type in NAMED_TYPES:
                continue
            if union_type in seen_unnamed_types:
                msg = f"Avro unions may not contain duplicate unnamed type: {union_type}"
                raise Error(msg)
            seen_unnamed_types.add(union_type)

    def _ensure_definition(self, fullname: str) -> None:
        definition_key = self.definition_names.get(fullname)
        if (
            definition_key is None or definition_key not in self.definitions
        ) and fullname not in self._building_definitions:
            self._build_definition(fullname)

    def _build_definition(self, fullname: str, *, as_root: bool = False) -> JsonSchema:
        raw_schema = self.named_schemas.get(fullname)
        if raw_schema is None:
            msg = f"Unknown Avro named type reference: {fullname}"
            raise Error(msg)
        definition_key = self.definition_names[fullname]

        self._building_definitions.add(fullname)
        type_value = raw_schema.get("type")
        if type_value == "record":
            converted = self._convert_record(raw_schema, fullname)
        elif type_value == "enum":
            converted = self._convert_enum(raw_schema, fullname)
        elif type_value == "fixed":
            converted = self._convert_fixed(raw_schema, fullname)
        else:  # pragma: no cover
            msg = f"Unsupported Avro named type: {type_value!r}"
            raise Error(msg)
        converted.setdefault("title", definition_key)
        self._building_definitions.remove(fullname)
        self.definitions[definition_key] = converted
        return _copy_schema(converted) if as_root else converted

    def _convert_record(self, schema: JsonSchema, fullname: str) -> JsonSchema:
        name_info = self.names[fullname]
        fields = schema.get("fields", [])

        properties: dict[str, JsonSchema] = {}
        required: list[str] = []
        for field in fields:
            if not isinstance(field, dict) or not isinstance(field.get("name"), str):
                msg = f"Avro record field requires a string name: {fullname}"
                raise Error(msg)
            field_name = cast("str", field["name"])
            if not _is_valid_name(field_name):
                msg = f"Invalid Avro record field name: {fullname}.{field_name}"
                raise Error(msg)
            if field_name in properties:
                msg = f"Duplicate Avro record field name: {fullname}.{field_name}"
                raise Error(msg)
            field_schema = self._convert_schema(field.get("type"), name_info.namespace)
            if "doc" in field and isinstance(field["doc"], str):
                field_schema["description"] = field["doc"]
            self._copy_aliases(field, field_schema)
            if "order" in field:
                field_schema["x-avro-order"] = field["order"]
            required.append(field_name)
            properties[field_name] = field_schema

        converted: JsonSchema = {"type": "object", "properties": properties}
        if required:
            converted["required"] = required
        self._copy_common_metadata(schema, converted)
        converted["x-avro-name"] = name_info.name
        if name_info.namespace:
            converted["x-avro-namespace"] = name_info.namespace
        converted["x-avro-fullname"] = fullname
        return converted

    def _convert_enum(self, schema: JsonSchema, fullname: str) -> JsonSchema:
        symbols = schema.get("symbols")
        if not isinstance(symbols, list) or not all(isinstance(symbol, str) for symbol in symbols):
            msg = f"Avro enum symbols must be a list of strings: {fullname}"
            raise Error(msg)
        seen_symbols: set[str] = set()
        for symbol in symbols:
            if not _is_valid_name(symbol):
                msg = f"Invalid Avro enum symbol: {fullname}.{symbol}"
                raise Error(msg)
            if symbol in seen_symbols:
                msg = f"Duplicate Avro enum symbol: {fullname}.{symbol}"
                raise Error(msg)
            seen_symbols.add(symbol)
        converted: JsonSchema = {"type": "string", "enum": list(symbols)}
        self._copy_common_metadata(schema, converted)
        converted["x-avro-fullname"] = fullname
        return converted

    def _convert_fixed(self, schema: JsonSchema, fullname: str) -> JsonSchema:
        size = schema.get("size")
        if not isinstance(size, int):
            msg = f"Avro fixed size must be an integer: {fullname}"
            raise Error(msg)
        converted: JsonSchema = {
            "type": "string",
            "format": "binary",
            "minLength": size,
            "maxLength": size,
            "x-avro-fullname": fullname,
        }
        self._copy_common_metadata(schema, converted)
        return self._apply_logical_type(schema, converted, avro_type="fixed")

    @staticmethod
    def _copy_common_metadata(source: JsonSchema, target: JsonSchema) -> None:
        if isinstance(doc := source.get("doc"), str):
            target["description"] = doc
        _AvroSchemaConverter._copy_aliases(source, target)
        if isinstance(logical_type := source.get("logicalType"), str):
            target["x-avro-logicalType"] = logical_type

    @staticmethod
    def _copy_aliases(source: JsonSchema, target: JsonSchema) -> None:
        if "aliases" not in source:
            return
        aliases = source["aliases"]
        target["x-avro-aliases"] = list(aliases) if isinstance(aliases, list) else aliases

    def _apply_logical_type(self, source: JsonSchema, target: JsonSchema, *, avro_type: str) -> JsonSchema:
        logical_type = source.get("logicalType")
        if not isinstance(logical_type, str):
            return target

        updates: JsonSchema | None = None
        match logical_type:
            case "decimal" if avro_type in {"bytes", "fixed"}:
                updates = self._decimal_schema(source)
                updates["x-avro-logicalType"] = logical_type
            case "big-decimal" if avro_type == "bytes":
                updates = self._decimal_schema(source)
                updates["x-avro-logicalType"] = logical_type
            case "uuid" if avro_type in {"string", "fixed"}:
                updates = {"type": "string", "format": "uuid", "x-avro-logicalType": logical_type}
            case "date" if avro_type == "int":
                updates = {"type": "string", "format": "date", "x-avro-logicalType": logical_type}
            case "time-millis" if avro_type == "int":
                updates = {"type": "string", "format": "time", "x-avro-logicalType": logical_type}
            case "time-micros" if avro_type == "long":
                updates = {"type": "string", "format": "time", "x-avro-logicalType": logical_type}
            case "timestamp-millis" | "timestamp-micros" | "timestamp-nanos" if avro_type == "long":
                updates = {"type": "string", "format": "date-time", "x-avro-logicalType": logical_type}
            case "local-timestamp-millis" | "local-timestamp-micros" | "local-timestamp-nanos" if avro_type == "long":
                updates = {"type": "string", "format": "date-time-local", "x-avro-logicalType": logical_type}
            case "duration" if avro_type == "fixed":
                updates = {"type": "string", "format": "duration", "x-avro-logicalType": logical_type}
            case _:
                return target
        converted = _copy_schema(target)
        converted.update(updates)
        return converted

    @staticmethod
    def _decimal_schema(source: JsonSchema) -> JsonSchema:
        converted: JsonSchema = {"type": "string", "format": "decimal", "x-avro-logicalType": "decimal"}
        if isinstance(source.get("precision"), int):
            converted["x-avro-precision"] = source["precision"]
        if isinstance(source.get("scale"), int):
            converted["x-avro-scale"] = source["scale"]
        return converted

    def _fullname_from_named_schema(self, schema: JsonSchema, namespace: str | None) -> str:
        name = schema.get("name")
        assert isinstance(name, str)
        return self._make_name(name, schema.get("namespace"), namespace).fullname

    @staticmethod
    def _make_name(name: str, namespace: Any, enclosing_namespace: str | None) -> _Name:
        if "." in name:
            fullname = name
            resolved_namespace = name.rsplit(".", maxsplit=1)[0]
        else:
            resolved_namespace = namespace if isinstance(namespace, str) else enclosing_namespace
            fullname = f"{resolved_namespace}.{name}" if resolved_namespace else name
        return _Name(fullname=fullname, namespace=resolved_namespace, name=name)

    def _resolve_fullname(self, name: str, namespace: str | None) -> str:
        if name in self.named_schemas:
            return name
        if "." in name:
            return name
        if namespace and (namespaced := f"{namespace}.{name}") in self.named_schemas:
            return namespaced
        return name

    def _ref(self, fullname: str) -> str:
        return f"#/definitions/{self.definition_names[fullname]}"


class AvroParser(JsonSchemaParser):
    """Parse Apache Avro schemas with the existing JSON Schema model builder.

    Avro is converted before parsing, but the generated models still rely on
    JsonSchemaParser's reference resolution, model construction, formatting,
    and configuration surface. The Avro-specific state is kept in a short-lived
    converter per source so named type resolution cannot leak between inputs.
    """

    _config_class_name = "AvroParserConfig"

    def __init__(
        self,
        source: str | Path | list[Path] | ParseResult,
        *,
        config: AvroParserConfig | None = None,
        **options: Unpack[AvroParserConfigDict],
    ) -> None:
        """Initialize the Avro parser with JSON Schema parser configuration."""
        super().__init__(source=source, config=config, **options)

    def parse_raw(self) -> None:
        """Parse all Avro schema input sources into data models."""
        self._parse_converted_sources(_AvroSchemaConverter)


def convert_avro_schema_data(data: YamlValue) -> dict[str, YamlValue]:
    """Convert in-memory Avro schema data to the JSON Schema shape used by the parser."""
    return _AvroSchemaConverter().convert_raw(data)


__all__ = ["AvroParser", "convert_avro_schema_data", "is_avro_schema_data"]
