"""Apache Avro schema parser implementation.

Converts Avro JSON schemas into the JSON Schema shape consumed by the existing
JSON Schema parser while preserving Avro named type and logical type semantics.
"""

from __future__ import annotations

import copy
import re
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from typing_extensions import Unpack

from datamodel_code_generator import Error, YamlValue, load_yaml
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

if TYPE_CHECKING:
    from pathlib import Path
    from urllib.parse import ParseResult

    from datamodel_code_generator._types import AvroParserConfigDict
    from datamodel_code_generator.config import AvroParserConfig
    from datamodel_code_generator.parser.base import Source

JsonSchema = dict[str, Any]

PRIMITIVE_TYPES = frozenset({"null", "boolean", "int", "long", "float", "double", "bytes", "string"})
NAMED_TYPES = frozenset({"record", "enum", "fixed"})
COMPLEX_TYPES = NAMED_TYPES | {"array", "map"}
PYTHON_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

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


def _is_avro_union_item(item: YamlValue) -> bool:  # noqa: PLR0911
    if isinstance(item, str):
        return item in PRIMITIVE_TYPES or "." in item
    if isinstance(item, list):
        return bool(item) and all(_is_avro_union_item(child) for child in item)
    if not isinstance(item, dict):
        return False

    type_value = item.get("type")
    if isinstance(type_value, list):
        return bool(type_value) and all(_is_avro_union_item(child) for child in type_value)
    if isinstance(type_value, dict):
        return _is_avro_union_item(type_value)
    if not isinstance(type_value, str):
        return False
    if type_value in PRIMITIVE_TYPES:
        return True
    if type_value == "record":
        return isinstance(item.get("name"), str) and isinstance(item.get("fields"), list)
    if type_value == "enum":
        return isinstance(item.get("name"), str) and isinstance(item.get("symbols"), list)
    if type_value == "fixed":
        return isinstance(item.get("name"), str) and isinstance(item.get("size"), int)
    if type_value == "array":
        return "items" in item
    if type_value == "map":
        return "values" in item
    return "." in type_value


class _Name(NamedTuple):
    fullname: str
    namespace: str | None
    name: str


def is_avro_schema_data(data: YamlValue) -> bool:  # noqa: PLR0911
    """Return whether loaded data appears to be an Avro schema."""
    if isinstance(data, list):
        return bool(data) and all(_is_avro_union_item(item) for item in data)
    if not isinstance(data, dict):
        return isinstance(data, str) and data in PRIMITIVE_TYPES

    if any(key in data for key in ("$schema", "$defs", "definitions", "properties", "allOf", "anyOf", "oneOf")):
        return False

    type_value = data.get("type")
    if isinstance(type_value, list):
        return False
    if isinstance(type_value, dict):
        return is_avro_schema_data(type_value)
    if not isinstance(type_value, str):
        return False
    if type_value == "record":
        return isinstance(data.get("name"), str) and isinstance(data.get("fields"), list)
    if type_value == "enum":
        return isinstance(data.get("name"), str) and isinstance(data.get("symbols"), list)
    if type_value == "fixed":
        return isinstance(data.get("name"), str) and isinstance(data.get("size"), int)
    if type_value == "map":
        return "values" in data
    if type_value in PRIMITIVE_TYPES:
        return any(key in data for key in ("logicalType", "namespace", "aliases"))
    return type_value not in COMPLEX_TYPES and "." in type_value


def _copy_schema(schema: JsonSchema) -> JsonSchema:
    return copy.deepcopy(schema)


def _to_class_title(name: str) -> str:
    return f"{name[:1].upper()}{name[1:]}"


def _namespace_name(namespace: str | None) -> str:
    if not namespace:
        return "NoNamespace"
    parts = re.findall(r"[A-Za-z0-9]+", namespace)
    return "".join(_to_class_title(part) for part in parts) or "Namespace"


class _AvroSchemaConverter:
    def __init__(self) -> None:
        self.named_schemas: dict[str, JsonSchema] = {}
        self.names: dict[str, _Name] = {}
        self.definition_names: dict[str, str] = {}
        self.definitions: dict[str, JsonSchema] = {}
        self._building_definitions: set[str] = set()

    def convert(self, source: Source) -> dict[str, YamlValue]:
        raw_obj = source.raw_data if source.raw_data is not None else load_yaml(source.text)
        self._collect_named_schemas(raw_obj)
        self._prepare_definition_names()
        schema = self._convert_schema(raw_obj, namespace=None, root=True)
        schema.setdefault("title", "Model")
        if self.definitions:
            schema["definitions"] = self.definitions
        schema.setdefault("$schema", "http://json-schema.org/draft-07/schema#")
        return cast("dict[str, YamlValue]", schema)

    def _collect_named_schemas(self, schema: YamlValue, namespace: str | None = None) -> None:  # noqa: PLR0912
        if isinstance(schema, str):
            return
        if isinstance(schema, list):
            for item in schema:
                self._collect_named_schemas(item, namespace)
            return
        if not isinstance(schema, dict):
            return

        type_value = schema.get("type")
        if isinstance(type_value, list):
            self._collect_named_schemas(type_value, namespace)
            return
        if isinstance(type_value, dict):
            self._collect_named_schemas(type_value, namespace)
            return

        child_namespace = namespace
        if isinstance(type_value, str) and type_value in NAMED_TYPES:
            name = schema.get("name")
            if not isinstance(name, str):
                msg = f"Avro {type_value} schema requires a string name"
                raise Error(msg)
            name_info = self._make_name(name, schema.get("namespace"), namespace)
            existing = self.named_schemas.get(name_info.fullname)
            if existing is not None and existing is not schema:
                msg = f"Duplicate Avro named type: {name_info.fullname}"
                raise Error(msg)
            self.named_schemas[name_info.fullname] = schema
            self.names[name_info.fullname] = name_info
            child_namespace = name_info.namespace

        if type_value == "record":
            fields = schema.get("fields", [])
            if not isinstance(fields, list):
                msg = f"Avro record fields must be a list: {schema.get('name')}"
                raise Error(msg)
            for field in fields:
                if isinstance(field, dict):
                    self._collect_named_schemas(field.get("type"), child_namespace)
        elif type_value == "array":
            self._collect_named_schemas(schema.get("items"), child_namespace)
        elif type_value == "map":
            self._collect_named_schemas(schema.get("values"), child_namespace)

    def _prepare_definition_names(self) -> None:
        fullnames_by_local: dict[str, list[str]] = {}
        for fullname, name_info in self.names.items():
            fullnames_by_local.setdefault(name_info.name.rsplit(".", maxsplit=1)[-1], []).append(fullname)

        used_names: set[str] = set()
        for local, fullnames in sorted(fullnames_by_local.items()):
            for fullname in sorted(fullnames):
                name_info = self.names[fullname]
                if len(fullnames) == 1:
                    name = _to_class_title(local)
                else:
                    name = f"{_namespace_name(name_info.namespace)}{_to_class_title(local)}"
                candidate = name
                suffix = 2
                while candidate in used_names:
                    candidate = f"{name}{suffix}"
                    suffix += 1
                self.definition_names[fullname] = candidate
                used_names.add(candidate)

    def _convert_schema(  # noqa: PLR0911, PLR0912
        self,
        schema: YamlValue,
        namespace: str | None,
        *,
        root: bool = False,
    ) -> JsonSchema:
        if isinstance(schema, str):
            return self._convert_type_name(schema, namespace)
        if isinstance(schema, list):
            return self._convert_union(schema, namespace)
        if not isinstance(schema, dict):
            msg = f"Unsupported Avro schema value: {schema!r}"
            raise Error(msg)

        type_value = schema.get("type")
        if isinstance(type_value, list):
            converted = self._convert_union(type_value, namespace)
            self._copy_common_metadata(schema, converted)
            return converted
        if isinstance(type_value, dict):
            converted = self._convert_schema(type_value, namespace, root=root)
            self._copy_common_metadata(schema, converted)
            return converted
        if not isinstance(type_value, str):
            msg = f"Avro schema object requires a string, object, or union type: {schema!r}"
            raise Error(msg)

        if type_value in PRIMITIVE_TYPES:
            converted = _copy_schema(PRIMITIVE_SCHEMAS[type_value])
            self._copy_common_metadata(schema, converted)
            return self._apply_logical_type(schema, converted, avro_type=type_value)
        if type_value == "record":
            fullname = self._fullname_from_named_schema(schema, namespace)
            if root:
                return self._build_definition(fullname, as_root=True)
            self._ensure_definition(fullname)
            return {"$ref": self._ref(fullname)}
        if type_value == "enum":
            fullname = self._fullname_from_named_schema(schema, namespace)
            if root:
                return self._build_definition(fullname, as_root=True)
            self._ensure_definition(fullname)
            return {"$ref": self._ref(fullname)}
        if type_value == "array":
            converted = {"type": "array", "items": self._convert_schema(schema.get("items"), namespace)}
            self._copy_common_metadata(schema, converted)
            return converted
        if type_value == "map":
            converted = {
                "type": "object",
                "additionalProperties": self._convert_schema(schema.get("values"), namespace),
            }
            self._copy_common_metadata(schema, converted)
            return converted
        if type_value == "fixed":
            fullname = self._fullname_from_named_schema(schema, namespace)
            if root:
                return self._build_definition(fullname, as_root=True)
            self._ensure_definition(fullname)
            return {"$ref": self._ref(fullname)}
        return self._convert_type_name(type_value, namespace)

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
        definition_key = self.definition_names.get(fullname)
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
            field_schema = self._convert_schema(field.get("type"), name_info.namespace)
            if "doc" in field and isinstance(field["doc"], str):
                field_schema["description"] = field["doc"]
            if "aliases" in field:
                field_schema["x-avro-aliases"] = field["aliases"]
            if "order" in field:
                field_schema["x-avro-order"] = field["order"]
            if "default" in field:
                field_schema["default"] = field["default"]
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
        converted: JsonSchema = {"type": "string", "enum": symbols}
        self._copy_common_metadata(schema, converted)
        if "default" in schema:
            converted["default"] = schema["default"]
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
        if isinstance(source.get("doc"), str):
            target["description"] = source["doc"]
        if "aliases" in source:
            target["x-avro-aliases"] = source["aliases"]
        if isinstance(source.get("logicalType"), str):
            target["x-avro-logicalType"] = source["logicalType"]

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
        if namespace:
            namespaced = f"{namespace}.{name}"
            if namespaced in self.named_schemas:
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
        for source, path_parts in self._get_context_source_path_parts():
            raw_obj = _AvroSchemaConverter().convert(source)
            source.raw_data = raw_obj
            if source.path.parts:
                self.remote_object_cache[str(self.base_path / source.path)] = raw_obj
            self.raw_obj = raw_obj
            title = str(raw_obj.get("title") or "Model")
            obj_name = self.class_name or title
            self._parse_file(raw_obj, obj_name, path_parts)

        self._resolve_unparsed_json_pointer()
        self._generate_forced_base_models()


__all__ = ["AvroParser", "is_avro_schema_data"]
