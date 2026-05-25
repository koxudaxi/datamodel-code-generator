"""XML Schema parser implementation.

Converts W3C XML Schema (XSD) documents into the JSON Schema shape consumed by
the existing JSON Schema parser.
"""

from __future__ import annotations

import copy
import io
import re
from pathlib import Path  # noqa: TC003 - used by runtime path resolution
from typing import TYPE_CHECKING, Any, NamedTuple, cast
from xml.etree import ElementTree as ET  # noqa: S405

from typing_extensions import Unpack

from datamodel_code_generator import Error, YamlValue
from datamodel_code_generator.parser.base import Source, title_to_class_name
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

if TYPE_CHECKING:
    from collections.abc import Iterator
    from urllib.parse import ParseResult

    from datamodel_code_generator._types import JSONSchemaParserConfigDict
    from datamodel_code_generator.config import JSONSchemaParserConfig

XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XML_SCHEMA_TAG = f"{{{XML_SCHEMA_NAMESPACE}}}schema"
UNBOUNDED = "unbounded"
INTERNAL_OCCURS_ARRAY = "x-xsd-occurs-array"

JsonSchema = dict[str, Any]
QNameKey = tuple[str | None, str]
PYTHON_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


STRING_SCHEMA: JsonSchema = {"type": "string"}
INTEGER_SCHEMA: JsonSchema = {"type": "integer"}
NUMBER_SCHEMA: JsonSchema = {"type": "number"}
BOOLEAN_SCHEMA: JsonSchema = {"type": "boolean"}


class _OccurrenceContext(NamedTuple):
    required: bool = True
    repeating: bool = False
    min_items: int | None = None
    max_items: int | None = None


DEFAULT_OCCURRENCE = _OccurrenceContext()

BUILTIN_TYPE_SCHEMAS: dict[str, JsonSchema] = {
    "anySimpleType": {},
    "anyAtomicType": {},
    "anyType": {},
    "anyURI": {"type": "string", "format": "uri"},
    "base64Binary": {"type": "string", "format": "byte"},
    "boolean": BOOLEAN_SCHEMA,
    "byte": {"type": "integer", "minimum": -128, "maximum": 127},
    "date": {"type": "string", "format": "date"},
    "dateTime": {"type": "string", "format": "date-time"},
    "decimal": NUMBER_SCHEMA,
    "double": NUMBER_SCHEMA,
    "duration": {"type": "string", "format": "duration"},
    "dayTimeDuration": {"type": "string", "format": "duration"},
    "ENTITIES": {"type": "array", "items": STRING_SCHEMA},
    "ENTITY": STRING_SCHEMA,
    "float": NUMBER_SCHEMA,
    "gDay": {"type": "string"},
    "gMonth": {"type": "string"},
    "gMonthDay": {"type": "string"},
    "gYear": {"type": "string"},
    "gYearMonth": {"type": "string"},
    "hexBinary": STRING_SCHEMA,
    "ID": STRING_SCHEMA,
    "IDREF": STRING_SCHEMA,
    "IDREFS": {"type": "array", "items": STRING_SCHEMA},
    "int": {"type": "integer", "minimum": -2147483648, "maximum": 2147483647},
    "integer": INTEGER_SCHEMA,
    "language": STRING_SCHEMA,
    "long": {"type": "integer", "minimum": -9223372036854775808, "maximum": 9223372036854775807},
    "Name": STRING_SCHEMA,
    "NCName": STRING_SCHEMA,
    "negativeInteger": {"type": "integer", "maximum": -1},
    "NMTOKEN": STRING_SCHEMA,
    "NMTOKENS": {"type": "array", "items": STRING_SCHEMA},
    "nonNegativeInteger": {"type": "integer", "minimum": 0},
    "nonPositiveInteger": {"type": "integer", "maximum": 0},
    "normalizedString": STRING_SCHEMA,
    "NOTATION": STRING_SCHEMA,
    "positiveInteger": {"type": "integer", "minimum": 1},
    "QName": STRING_SCHEMA,
    "short": {"type": "integer", "minimum": -32768, "maximum": 32767},
    "string": STRING_SCHEMA,
    "time": {"type": "string", "format": "time"},
    "token": STRING_SCHEMA,
    "unsignedByte": {"type": "integer", "minimum": 0, "maximum": 255},
    "unsignedInt": {"type": "integer", "minimum": 0, "maximum": 4294967295},
    "unsignedLong": {"type": "integer", "minimum": 0, "maximum": 18446744073709551615},
    "unsignedShort": {"type": "integer", "minimum": 0, "maximum": 65535},
    "yearMonthDuration": {"type": "string", "format": "duration"},
    "dateTimeStamp": {"type": "string", "format": "date-time"},
}


def is_xml_schema_text(text: str) -> bool:
    """Return whether text is an XML Schema document."""
    try:
        root = ET.fromstring(text)  # noqa: S314
    except ET.ParseError:
        return False
    return root.tag == XML_SCHEMA_TAG


def _local_name(tag_or_qname: str) -> str:
    if "}" in tag_or_qname:
        return tag_or_qname.rsplit("}", maxsplit=1)[-1]
    return tag_or_qname.rsplit(":", maxsplit=1)[-1]


def _namespace(tag: str) -> str | None:
    if tag.startswith("{"):
        return tag[1:].split("}", maxsplit=1)[0]
    return None


def _is_xsd_element(element: ET.Element, *names: str) -> bool:
    return _namespace(element.tag) == XML_SCHEMA_NAMESPACE and _local_name(element.tag) in names


def _xsd_children(element: ET.Element, *names: str) -> Iterator[ET.Element]:
    for child in element:
        if _is_xsd_element(child, *names):
            yield child


def _first_xsd_child(element: ET.Element, *names: str) -> ET.Element | None:
    return next(_xsd_children(element, *names), None)


def _documentation(element: ET.Element) -> str | None:
    docs: list[str] = []
    for annotation in _xsd_children(element, "annotation"):
        for documentation in _xsd_children(annotation, "documentation"):
            text = "".join(documentation.itertext()).strip()
            if text:
                docs.append(text)
    return "\n\n".join(docs) or None


def _copy_schema(schema: JsonSchema) -> JsonSchema:
    return copy.deepcopy(schema)


def _to_class_title(name: str) -> str:
    if PYTHON_NAME_PATTERN.match(name):
        return f"{name[:1].upper()}{name[1:]}"
    return title_to_class_name(name)


def _safe_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _safe_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


class _XMLSchemaConverter:
    def __init__(self, base_path: Path, encoding: str) -> None:
        self.base_path = base_path
        self.encoding = encoding
        self.namespaces: dict[str, str] = {}
        self.target_namespace: str | None = None
        self.simple_types: dict[QNameKey, ET.Element] = {}
        self.complex_types: dict[QNameKey, ET.Element] = {}
        self.elements: dict[QNameKey, ET.Element] = {}
        self.attributes: dict[QNameKey, ET.Element] = {}
        self.groups: dict[QNameKey, ET.Element] = {}
        self.attribute_groups: dict[QNameKey, ET.Element] = {}
        self.default_open_content: ET.Element | None = None
        self.substitution_groups: dict[QNameKey, set[QNameKey]] = {}
        self.substitution_members: set[QNameKey] = set()
        self.referenced_elements: set[QNameKey] = set()
        self.local_elements: set[QNameKey] = set()
        self._loaded_locations: set[tuple[Path, str | None]] = set()
        self._element_namespaces: dict[int, dict[str, str]] = {}
        self._building_definitions: set[QNameKey] = set()
        self._built_definitions: dict[QNameKey, JsonSchema] = {}
        self._definitions: dict[str, JsonSchema] = {}
        self._definition_names: dict[QNameKey, str] = {}

    def convert(self, source: Source) -> dict[str, YamlValue]:
        root = self._parse_schema(source.text, self.base_path / source.path)
        self._collect_schema(root, source_path=self.base_path / source.path, is_root=True)

        self._prepare_definition_names()
        self._definitions = self._build_definitions()
        global_elements = [
            (key, element)
            for key, element in self.elements.items()
            if key in self.local_elements
            and element.get("name")
            and element.get("abstract") != "true"
            and key not in self.substitution_members
        ]

        if len(global_elements) == 1:
            root_key, root_element = global_elements[0]
            root_name = root_element.get("name") or "Model"
            root_type_name = _local_name(root_element.get("type", ""))
            root_definition_name = self._definition_name(root_key)
            if root_type_name == root_name and root_definition_name in self._definitions:
                schema = _copy_schema(self._definitions[root_definition_name])
                schema.setdefault("title", _to_class_title(root_name))
                if not self._has_definition_ref(root_key):
                    self._definitions.pop(root_definition_name)
            else:
                schema = self._convert_global_element_as_root(root_element, root_name)
        else:
            properties: dict[str, JsonSchema] = {}
            for _key, element in global_elements:
                name = cast("str", element.get("name"))
                properties[name] = self._convert_global_element_as_property(element)
            schema = {
                "title": "Model",
                "type": "object",
                "properties": properties,
                "required": list(properties),
            }

        if self._definitions:
            schema["definitions"] = self._definitions
        schema.setdefault("$schema", "http://json-schema.org/draft-07/schema#")
        self._strip_internal_metadata(schema)
        return schema

    def _parse_schema(self, text: str, source_path: Path) -> ET.Element:
        try:
            root: ET.Element | None = None
            active_namespaces: dict[str, str] = {}
            namespace_stack: list[tuple[str, str | None]] = []
            for event, payload in ET.iterparse(io.StringIO(text), events=("start", "start-ns", "end-ns")):  # noqa: S314
                match event:
                    case "start-ns":
                        prefix, uri = cast("tuple[str, str]", payload)
                        namespace_stack.append((prefix, active_namespaces.get(prefix)))
                        active_namespaces[prefix] = uri
                        self.namespaces.setdefault(prefix, uri)
                    case "end-ns":
                        prefix, previous_uri = namespace_stack.pop()
                        if previous_uri is None:
                            active_namespaces.pop(prefix, None)
                        else:
                            active_namespaces[prefix] = previous_uri
                    case "start":
                        element = cast("ET.Element", payload)
                        if root is None:
                            root = element
                        self._element_namespaces[id(element)] = active_namespaces.copy()
                    case _:  # pragma: no cover
                        pass
        except ET.ParseError as exc:
            msg = f"Invalid XML Schema document {source_path}: {exc}"
            raise Error(msg) from exc
        if root is None:  # pragma: no cover
            msg = f"Invalid XML Schema document {source_path}: empty document"
            raise Error(msg)
        if root.tag != XML_SCHEMA_TAG:
            msg = f"XML Schema root element must be xs:schema: {source_path}"
            raise Error(msg)
        if target_namespace := root.get("targetNamespace"):
            self.target_namespace = target_namespace
        return root

    def _collect_schema(
        self,
        root: ET.Element,
        source_path: Path,
        *,
        is_root: bool = False,
        namespace_override: str | None = None,
    ) -> None:
        source_dir = source_path.parent if source_path.name else self.base_path
        schema_namespace = root.get("targetNamespace") or namespace_override
        for child in _xsd_children(root, "include", "import", "redefine", "override"):
            schema_location = child.get("schemaLocation")
            if not schema_location:
                continue
            location = (source_dir / schema_location).resolve()
            if not location.is_file():
                continue
            included_root = self._parse_schema(location.read_text(encoding=self.encoding), location)
            child_namespace_override = (
                schema_namespace
                if _local_name(child.tag) in {"include", "redefine", "override"}
                and included_root.get("targetNamespace") is None
                else None
            )
            load_key = (location, child_namespace_override)
            if load_key not in self._loaded_locations:
                self._loaded_locations.add(load_key)
                self._collect_schema(included_root, location, namespace_override=child_namespace_override)
            if _is_xsd_element(child, "redefine", "override"):
                self._collect_schema_declarations(child, schema_namespace, replace=True)

        for child in root:
            if _namespace(child.tag) != XML_SCHEMA_NAMESPACE:
                continue
            self._collect_schema_declaration(child, schema_namespace, is_root=is_root)
        for child in root.iter():
            if _is_xsd_element(child, "element") and (ref := child.get("ref")):
                self.referenced_elements.add(self._qname_key(ref, child))

    def _collect_schema_declarations(self, owner: ET.Element, schema_namespace: str | None, *, replace: bool) -> None:
        for child in owner:
            if _namespace(child.tag) == XML_SCHEMA_NAMESPACE:
                self._collect_schema_declaration(child, schema_namespace, replace=replace)

    def _collect_schema_declaration(
        self,
        child: ET.Element,
        schema_namespace: str | None,
        *,
        is_root: bool = False,
        replace: bool = False,
    ) -> None:
        if _is_xsd_element(child, "defaultOpenContent"):
            self.default_open_content = child
            return
        name = child.get("name")
        if not name:
            return
        key = (schema_namespace, name)
        name_to_registry = {
            "simpleType": self.simple_types,
            "complexType": self.complex_types,
            "element": self.elements,
            "attribute": self.attributes,
            "group": self.groups,
            "attributeGroup": self.attribute_groups,
        }
        local_name = _local_name(child.tag)
        registry = name_to_registry.get(local_name)
        if registry is None:
            return
        if local_name == "element":
            if is_root:
                self.local_elements.add(key)
            if substitution_group := child.get("substitutionGroup"):
                head_key = self._qname_key(substitution_group, child)
                self.substitution_groups.setdefault(head_key, set()).add(key)
                self.substitution_members.add(key)
        if replace:
            registry[key] = child
        else:
            registry.setdefault(key, child)

    def _prepare_definition_names(self) -> None:
        keys = set(self.simple_types) | set(self.complex_types) | set(self.elements)
        keys_by_local: dict[str, list[QNameKey]] = {}
        for key in keys:
            keys_by_local.setdefault(key[1], []).append(key)

        used_names: set[str] = set()
        for local, local_keys in sorted(keys_by_local.items()):
            sorted_keys = sorted(local_keys, key=self._sort_key)
            for key in sorted_keys:
                name = local if len(sorted_keys) == 1 else f"{self._namespace_name(key[0])}{_to_class_title(local)}"
                candidate = name
                suffix = 2
                while candidate in used_names:
                    candidate = f"{name}{suffix}"
                    suffix += 1
                self._definition_names[key] = candidate
                used_names.add(candidate)

    def _build_definitions(self) -> dict[str, JsonSchema]:
        definitions: dict[str, JsonSchema] = {}
        for key in sorted(self.simple_types, key=self._sort_key):
            definitions[self._definition_name(key)] = self._build_definition(key)
        for key in sorted(self.complex_types, key=self._sort_key):
            definitions[self._definition_name(key)] = self._build_definition(key)
        for key in sorted(self._resolved_referenced_elements(), key=self._sort_key):
            name = self._definition_name(key)
            if name not in definitions:
                definitions[name] = self._build_definition(key)
        return definitions

    def _build_definition(self, key: QNameKey) -> JsonSchema:
        if key in self._built_definitions:
            return self._built_definitions[key]
        if key in self._building_definitions:  # pragma: no cover
            return {"$ref": self._ref_for_key(key)}
        self._building_definitions.add(key)
        simple_type = self.simple_types.get(key)
        complex_type = self.complex_types.get(key)
        element = self.elements.get(key)
        if simple_type is not None:
            schema = self._convert_simple_type(simple_type)
        elif complex_type is not None:
            schema = self._convert_complex_type(complex_type)
        elif element is not None:
            schema = self._convert_element(element)
        else:  # pragma: no cover
            schema = {}
        name = self._definition_name(key)
        schema.setdefault("title", _to_class_title(name))
        self._building_definitions.remove(key)
        self._built_definitions[key] = schema
        self._definitions[name] = schema
        return schema

    def _has_definition_ref(self, key: QNameKey) -> bool:
        ref = self._ref_for_key(key)
        return any(self._contains_ref(schema, ref) for schema in self._definitions.values())

    def _contains_ref(self, value: Any, ref: str) -> bool:
        if isinstance(value, dict):
            return value.get("$ref") == ref or any(self._contains_ref(item, ref) for item in value.values())
        if isinstance(value, list):
            return any(self._contains_ref(item, ref) for item in value)
        return False

    def _convert_global_element_as_root(self, element: ET.Element, name: str) -> JsonSchema:
        schema = self._convert_element(element)
        if "$ref" in schema:
            schema = {"title": _to_class_title(name), "allOf": [schema]}
        else:
            schema.setdefault("title", _to_class_title(name))
        return schema

    def _convert_global_element_as_property(self, element: ET.Element) -> JsonSchema:
        schema = self._convert_element(element)
        if "$ref" in schema:
            return schema
        name = cast("str", element.get("name"))
        schema.setdefault("title", _to_class_title(name))
        return schema

    def _convert_element(self, element: ET.Element) -> JsonSchema:
        if ref := element.get("ref"):
            key = self._resolve_key(ref, self.elements, element=element)
            schema = self._schema_for_substitution_group(key) or {"$ref": self._ref_for_key(key)}
        elif type_name := element.get("type"):
            schema = self._schema_for_qname(type_name, element)
        elif (simple_type := _first_xsd_child(element, "simpleType")) is not None:
            schema = self._convert_simple_type(simple_type)
        elif (complex_type := _first_xsd_child(element, "complexType")) is not None:
            schema = self._convert_complex_type(complex_type)
        else:
            schema = {}

        if alternative_schema := self._schema_for_alternatives(element, schema):
            schema = alternative_schema
        schema = self._apply_common_element_metadata(element, _copy_schema(schema))
        return self._apply_occurs(element, schema)

    def _schema_for_alternatives(self, element: ET.Element, fallback_schema: JsonSchema) -> JsonSchema | None:
        schemas = [
            schema
            for alternative in _xsd_children(element, "alternative")
            if (schema := self._convert_alternative(alternative))
        ]
        if not schemas:
            return None
        if fallback_schema and fallback_schema not in schemas:
            schemas.append(fallback_schema)
        return schemas[0] if len(schemas) == 1 else {"anyOf": schemas}

    def _convert_alternative(self, alternative: ET.Element) -> JsonSchema:
        if type_name := alternative.get("type"):
            return self._schema_for_qname(type_name, alternative)
        if (simple_type := _first_xsd_child(alternative, "simpleType")) is not None:
            return self._convert_simple_type(simple_type)
        if (complex_type := _first_xsd_child(alternative, "complexType")) is not None:
            return self._convert_complex_type(complex_type)
        return {}

    def _apply_common_element_metadata(self, element: ET.Element, schema: JsonSchema) -> JsonSchema:
        if documentation := _documentation(element):
            schema["description"] = documentation
        if "default" in element.attrib:
            schema["default"] = self._parse_literal(str(element.get("default")), schema)
        if "fixed" in element.attrib:
            schema["const"] = self._parse_literal(str(element.get("fixed")), schema)
        if element.get("nillable") == "true":
            schema = self._make_nullable(schema)
        if element.get("abstract") == "true":
            schema["x-xsd-abstract"] = True
        return schema

    def _make_nullable(self, schema: JsonSchema) -> JsonSchema:  # noqa: PLR6301
        schema = _copy_schema(schema)
        schema_type = schema.get("type")
        if isinstance(schema_type, str):
            schema["type"] = [schema_type, "null"]
            return schema
        if "anyOf" in schema:
            schema["anyOf"] = [*schema["anyOf"], {"type": "null"}]
            return schema
        return {"anyOf": [schema, {"type": "null"}]}

    def _apply_occurs(self, element: ET.Element, schema: JsonSchema) -> JsonSchema:  # noqa: PLR6301
        min_occurs_value = element.get("minOccurs")
        min_occurs = (_safe_int(min_occurs_value) or 0) if min_occurs_value else 1
        max_occurs = element.get("maxOccurs")
        if max_occurs is None or max_occurs == "1":
            return schema
        array_schema: JsonSchema = {"type": "array", "items": schema}
        if min_occurs:
            array_schema["minItems"] = min_occurs
        if max_occurs != UNBOUNDED:
            max_items = _safe_int(max_occurs)
            if max_items is not None:
                array_schema["maxItems"] = max_items
        array_schema[INTERNAL_OCCURS_ARRAY] = True
        return array_schema

    def _convert_simple_type(self, simple_type: ET.Element) -> JsonSchema:
        if (restriction := _first_xsd_child(simple_type, "restriction")) is not None:
            base_schema = self._restriction_base_schema(restriction)
            schema = self._apply_restriction_facets(restriction, base_schema)
        elif (list_element := _first_xsd_child(simple_type, "list")) is not None:
            item_type = list_element.get("itemType")
            item_schema = self._schema_for_qname(item_type, list_element) if item_type else {}
            if (inline_item_type := _first_xsd_child(list_element, "simpleType")) is not None:
                item_schema = self._convert_simple_type(inline_item_type)
            schema = {"type": "array", "items": item_schema}
        elif (union_element := _first_xsd_child(simple_type, "union")) is not None:
            schemas = []
            member_types = (union_element.get("memberTypes") or "").split()
            schemas.extend(self._schema_for_qname(member_type, union_element) for member_type in member_types)
            schemas.extend(self._convert_simple_type(child) for child in _xsd_children(union_element, "simpleType"))
            schema = {"anyOf": schemas} if schemas else {}
        else:
            schema = _copy_schema(STRING_SCHEMA)

        if documentation := _documentation(simple_type):
            schema = _copy_schema(schema)
            schema["description"] = documentation
        return schema

    def _restriction_base_schema(self, restriction: ET.Element) -> JsonSchema:
        if base := restriction.get("base"):
            key = self._resolve_key(base, self.simple_types, element=restriction)
            if key in self.simple_types and key not in self._building_definitions:
                return self._convert_simple_type(self.simple_types[key])
            return self._schema_for_qname(base, restriction)
        if (simple_type := _first_xsd_child(restriction, "simpleType")) is not None:
            return self._convert_simple_type(simple_type)
        return _copy_schema(STRING_SCHEMA)

    def _apply_restriction_facets(self, restriction: ET.Element, schema: JsonSchema) -> JsonSchema:  # noqa: PLR0912
        schema = _copy_schema(schema)
        enum_values: list[Any] = []
        for facet in restriction:
            if _namespace(facet.tag) != XML_SCHEMA_NAMESPACE:
                continue
            name = _local_name(facet.tag)
            value = facet.get("value")
            if value is None:
                continue
            match name:
                case "enumeration":
                    enum_values.append(self._parse_literal(value, schema))
                case "pattern":
                    schema["pattern"] = value
                case "length":
                    self._set_length(schema, value, same=True)
                case "minLength":
                    self._set_length(schema, value, same=False, minimum=True)
                case "maxLength":
                    self._set_length(schema, value, same=False, minimum=False)
                case "minInclusive":
                    schema["minimum"] = self._parse_number(value, schema)
                case "maxInclusive":
                    schema["maximum"] = self._parse_number(value, schema)
                case "minExclusive":
                    schema["exclusiveMinimum"] = self._parse_number(value, schema)
                case "maxExclusive":
                    schema["exclusiveMaximum"] = self._parse_number(value, schema)
                case "totalDigits":
                    schema["x-xsd-totalDigits"] = _safe_int(value)
                case "fractionDigits":
                    schema["x-xsd-fractionDigits"] = _safe_int(value)
        if enum_values:
            schema["enum"] = enum_values
        return schema

    def _set_length(self, schema: JsonSchema, value: str, *, same: bool, minimum: bool = True) -> None:  # noqa: PLR6301
        length = _safe_int(value)
        if length is None:
            return
        min_key, max_key = ("minItems", "maxItems") if schema.get("type") == "array" else ("minLength", "maxLength")
        if same:
            schema[min_key] = length
            schema[max_key] = length
        elif minimum:
            schema[min_key] = length
        else:
            schema[max_key] = length

    def _parse_literal(self, value: str, schema: JsonSchema) -> Any:  # noqa: PLR6301
        schema_type = schema.get("type")
        if schema_type == "integer":
            return integer if (integer := _safe_int(value)) is not None else value
        if schema_type == "number":
            return number if (number := _safe_float(value)) is not None else value
        if schema_type == "boolean":
            return value in {"true", "1"}
        return value

    def _parse_number(self, value: str, schema: JsonSchema) -> int | float | str:  # noqa: PLR6301
        if schema.get("type") == "integer":
            return integer if (integer := _safe_int(value)) is not None else value
        return number if (number := _safe_float(value)) is not None else value

    def _convert_complex_type(self, complex_type: ET.Element) -> JsonSchema:
        if (complex_content := _first_xsd_child(complex_type, "complexContent")) is not None:
            return self._convert_complex_content(complex_content, complex_type)
        if (simple_content := _first_xsd_child(complex_type, "simpleContent")) is not None:
            return self._convert_simple_content(simple_content, complex_type)

        schema: JsonSchema = {"type": "object", "properties": {}}
        self._apply_open_content(complex_type, schema)
        self._apply_model_group(complex_type, schema)
        self._apply_attributes(complex_type, schema)
        self._apply_mixed_content(complex_type, schema)
        if documentation := _documentation(complex_type):
            schema["description"] = documentation
        return schema

    def _convert_complex_content(self, complex_content: ET.Element, owner: ET.Element) -> JsonSchema:
        child = _first_xsd_child(complex_content, "extension", "restriction")
        if child is None:
            return self._convert_complex_type_without_content(owner)

        schema: JsonSchema = {"type": "object", "properties": {}}
        self._apply_open_content(child, schema)
        self._apply_model_group(child, schema)
        self._apply_attributes(child, schema)
        self._apply_mixed_content(complex_content, schema, owner)
        if _local_name(child.tag) == "extension" and (base := child.get("base")):
            return {"allOf": [self._schema_for_qname(base, child), schema]}
        return schema

    def _convert_complex_type_without_content(self, complex_type: ET.Element) -> JsonSchema:
        schema: JsonSchema = {"type": "object", "properties": {}}
        self._apply_open_content(complex_type, schema)
        self._apply_model_group(complex_type, schema)
        self._apply_attributes(complex_type, schema)
        self._apply_mixed_content(complex_type, schema)
        return schema

    def _apply_open_content(self, owner: ET.Element, schema: JsonSchema) -> None:
        open_content = _first_xsd_child(owner, "openContent")
        if open_content is not None:
            if open_content.get("mode", "interleave") != "none" and _first_xsd_child(open_content, "any") is not None:
                schema["additionalProperties"] = True
            return
        if (
            self.default_open_content is not None
            and _first_xsd_child(self.default_open_content, "any") is not None
            and (self._has_explicit_content(owner) or self.default_open_content.get("appliesToEmpty") in {"true", "1"})
        ):
            schema["additionalProperties"] = True

    @staticmethod
    def _has_explicit_content(owner: ET.Element) -> bool:
        return _first_xsd_child(owner, "sequence", "all", "choice", "group") is not None

    def _convert_simple_content(self, simple_content: ET.Element, owner: ET.Element) -> JsonSchema:
        child = _first_xsd_child(simple_content, "extension", "restriction")
        if child is None:
            value_schema = _copy_schema(STRING_SCHEMA)
        elif base := child.get("base"):
            value_schema = self._schema_for_qname(base, child)
        elif (simple_type := _first_xsd_child(child, "simpleType")) is not None:
            value_schema = self._convert_simple_type(simple_type)
        else:
            value_schema = _copy_schema(STRING_SCHEMA)
        if child is not None and _local_name(child.tag) == "restriction":
            value_schema = self._apply_restriction_facets(child, value_schema)

        schema: JsonSchema = {"type": "object", "properties": {"value": value_schema}, "required": ["value"]}
        self._apply_attributes(owner, schema)
        if child is not None:
            self._apply_attributes(child, schema)
        return schema

    def _apply_model_group(
        self,
        owner: ET.Element,
        schema: JsonSchema,
        *,
        occurrence: _OccurrenceContext = DEFAULT_OCCURRENCE,
    ) -> None:
        for child in owner:
            if _is_xsd_element(child, "sequence", "all", "choice"):
                self._apply_particle(
                    child,
                    schema,
                    occurrence=occurrence,
                )
            elif _is_xsd_element(child, "group"):
                self._apply_group(
                    child,
                    schema,
                    occurrence=occurrence,
                )

    def _apply_particle(
        self,
        particle: ET.Element,
        schema: JsonSchema,
        *,
        occurrence: _OccurrenceContext,
    ) -> None:
        if particle.get("maxOccurs") == "0":
            return
        is_choice = _local_name(particle.tag) == "choice"
        particle_required = occurrence.required and particle.get("minOccurs", "1") != "0" and not is_choice
        particle_repeating = self._is_repeating(particle)
        repeating = occurrence.repeating or particle_repeating
        min_items = self._combine_min_items(
            occurrence.min_items,
            particle.get("minOccurs") if occurrence.min_items is not None or particle_repeating else None,
        )
        child_min_items = min_items if particle_required and not is_choice else None
        max_items = self._combine_max_items(
            occurrence.max_items,
            particle.get("maxOccurs") if particle_repeating else None,
        )
        child_occurrence = _OccurrenceContext(
            required=particle_required,
            repeating=repeating,
            min_items=child_min_items,
            max_items=max_items,
        )
        for child in particle:
            if _is_xsd_element(child, "element"):
                self._add_property_from_element(
                    child,
                    schema,
                    occurrence=child_occurrence,
                )
            elif _is_xsd_element(child, "sequence", "all", "choice"):
                self._apply_particle(
                    child,
                    schema,
                    occurrence=child_occurrence,
                )
            elif _is_xsd_element(child, "group"):
                self._apply_group(
                    child,
                    schema,
                    occurrence=child_occurrence,
                )
            elif _is_xsd_element(child, "any") and child.get("maxOccurs") != "0":
                schema["additionalProperties"] = True

    def _apply_group(
        self,
        group: ET.Element,
        schema: JsonSchema,
        *,
        occurrence: _OccurrenceContext,
    ) -> None:
        if group.get("maxOccurs") == "0":
            return
        group_required = occurrence.required and group.get("minOccurs", "1") != "0"
        group_repeating = self._is_repeating(group)
        repeating = occurrence.repeating or group_repeating
        min_items = self._combine_min_items(
            occurrence.min_items,
            group.get("minOccurs") if occurrence.min_items is not None or group_repeating else None,
        )
        child_min_items = min_items if group_required else None
        max_items = self._combine_max_items(occurrence.max_items, group.get("maxOccurs") if group_repeating else None)
        child_occurrence = _OccurrenceContext(
            required=group_required,
            repeating=repeating,
            min_items=child_min_items,
            max_items=max_items,
        )
        ref = group.get("ref")
        if not ref:
            self._apply_particle(
                group,
                schema,
                occurrence=child_occurrence,
            )
            return
        target = self.groups.get(self._resolve_key(ref, self.groups, element=group))
        if target is not None:
            self._apply_model_group(
                target,
                schema,
                occurrence=child_occurrence,
            )

    def _add_property_from_element(
        self,
        element: ET.Element,
        schema: JsonSchema,
        *,
        occurrence: _OccurrenceContext,
    ) -> None:
        if element.get("maxOccurs") == "0":
            return
        name = element.get("name") or _local_name(element.get("ref", ""))
        if not name:
            return
        properties = schema.setdefault("properties", {})
        property_schema = self._convert_element(element)
        if occurrence.repeating:
            property_schema = self._repeat_property_schema(
                property_schema,
                min_items=occurrence.min_items,
                max_items=occurrence.max_items,
            )
        properties[name] = property_schema
        if occurrence.required and element.get("minOccurs", "1") != "0":
            schema.setdefault("required", []).append(name)

    def _apply_attributes(self, owner: ET.Element, schema: JsonSchema) -> None:
        for child in owner:
            if _is_xsd_element(child, "attribute"):
                self._add_attribute(child, schema)
            elif _is_xsd_element(child, "attributeGroup"):
                self._apply_attribute_group(child, schema)
            elif _is_xsd_element(child, "anyAttribute"):
                schema["additionalProperties"] = True

    def _apply_attribute_group(self, attribute_group: ET.Element, schema: JsonSchema) -> None:
        ref = attribute_group.get("ref")
        if not ref:
            self._apply_attributes(attribute_group, schema)
            return
        target = self.attribute_groups.get(self._resolve_key(ref, self.attribute_groups, element=attribute_group))
        if target is not None:
            self._apply_attributes(target, schema)

    def _add_attribute(self, attribute: ET.Element, schema: JsonSchema) -> None:
        if attribute.get("use") == "prohibited":
            return
        ref = attribute.get("ref")
        source_attribute = (
            self.attributes.get(self._resolve_key(ref, self.attributes, element=attribute)) if ref else None
        )
        if source_attribute is None:
            source_attribute = attribute
        name = attribute.get("name") or source_attribute.get("name") or _local_name(ref or "")
        if not name:
            return
        if type_name := attribute.get("type") or source_attribute.get("type"):
            attribute_schema = self._schema_for_qname(type_name, attribute)
        else:
            simple_type = _first_xsd_child(attribute, "simpleType")
            if simple_type is None:
                simple_type = _first_xsd_child(source_attribute, "simpleType")
            attribute_schema = self._convert_simple_type(simple_type) if simple_type is not None else STRING_SCHEMA
        attribute_schema = _copy_schema(attribute_schema)
        if documentation := _documentation(attribute) or _documentation(source_attribute):
            attribute_schema["description"] = documentation
        default = attribute.get("default")
        if default is None and "default" not in attribute.attrib:
            default = source_attribute.get("default")
        if default is not None:
            attribute_schema["default"] = self._parse_literal(default, attribute_schema)
        fixed = attribute.get("fixed")
        if fixed is None and "fixed" not in attribute.attrib:
            fixed = source_attribute.get("fixed")
        if fixed is not None:
            attribute_schema["const"] = self._parse_literal(fixed, attribute_schema)
        schema.setdefault("properties", {})[name] = attribute_schema
        if (attribute.get("use") or source_attribute.get("use")) == "required":
            schema.setdefault("required", []).append(name)

    @staticmethod
    def _apply_mixed_content(
        owner: ET.Element,
        schema: JsonSchema,
        *additional_owners: ET.Element,
    ) -> None:
        if not any(candidate.get("mixed") == "true" for candidate in (owner, *additional_owners)):
            return
        schema.setdefault("properties", {}).setdefault("value", _copy_schema(STRING_SCHEMA))

    def _schema_for_substitution_group(self, head_key: QNameKey) -> JsonSchema | None:
        member_keys = self.substitution_groups.get(head_key)
        if not member_keys:
            return None
        schemas = []
        head_element = self.elements.get(head_key)
        if head_element is not None and head_element.get("abstract") != "true":
            schemas.append({"$ref": self._ref_for_key(head_key)})
        schemas.extend({"$ref": self._ref_for_key(key)} for key in sorted(member_keys, key=self._sort_key))
        return {"anyOf": schemas} if len(schemas) > 1 else schemas[0]

    @staticmethod
    def _is_repeating(element: ET.Element) -> bool:
        max_occurs = element.get("maxOccurs")
        return max_occurs is not None and max_occurs != "1"

    def _combine_max_items(self, parent_max_items: int | None, max_occurs: str | None) -> int | None:  # noqa: PLR6301
        if max_occurs is None:
            return parent_max_items
        if max_occurs == UNBOUNDED:
            return None
        max_items = _safe_int(max_occurs)
        if max_items is None:
            return parent_max_items
        return parent_max_items * max_items if parent_max_items is not None else max_items

    def _combine_min_items(self, parent_min_items: int | None, min_occurs: str | None) -> int | None:  # noqa: PLR6301
        if min_occurs is None:
            return parent_min_items
        min_items = _safe_int(min_occurs)
        if min_items is None:
            return parent_min_items
        return parent_min_items * min_items if parent_min_items is not None else min_items

    def _repeat_property_schema(
        self,
        schema: JsonSchema,
        *,
        min_items: int | None,
        max_items: int | None,
    ) -> JsonSchema:
        if schema.get("type") != "array" or not schema.get(INTERNAL_OCCURS_ARRAY):
            array_schema: JsonSchema = {"type": "array", "items": schema, INTERNAL_OCCURS_ARRAY: True}
        else:
            array_schema = _copy_schema(schema)
        if min_items is not None:
            self._set_repeated_bound(array_schema, "minItems", min_items)
        if max_items is not None:
            self._set_repeated_bound(array_schema, "maxItems", max_items)
        return array_schema

    @staticmethod
    def _set_repeated_bound(schema: JsonSchema, key: str, value: int) -> None:
        current = schema.get(key)
        schema[key] = current * value if isinstance(current, int) else value

    def _strip_internal_metadata(self, value: Any) -> None:
        if isinstance(value, dict):
            value.pop(INTERNAL_OCCURS_ARRAY, None)
            for item in value.values():
                self._strip_internal_metadata(item)
        elif isinstance(value, list):
            for item in value:
                self._strip_internal_metadata(item)

    def _schema_for_qname(self, qname: str | None, element: ET.Element | None = None) -> JsonSchema:
        if not qname:  # pragma: no cover
            return {}
        local = _local_name(qname)
        namespace = self._qname_namespace(qname, element)
        is_unprefixed_builtin = namespace is None and local in BUILTIN_TYPE_SCHEMAS
        key = self._resolve_key(qname, self.simple_types, self.complex_types, self.elements, element=element)
        is_user_defined = key in self.simple_types or key in self.complex_types or key in self.elements
        if namespace == XML_SCHEMA_NAMESPACE or (is_unprefixed_builtin and not is_user_defined):
            return _copy_schema(BUILTIN_TYPE_SCHEMAS.get(local, STRING_SCHEMA))
        if is_user_defined:
            return {"$ref": self._ref_for_key(key)}
        return _copy_schema(BUILTIN_TYPE_SCHEMAS.get(local, {}))

    def _qname_namespace(self, qname: str, element: ET.Element | None = None) -> str | None:
        if ":" not in qname:
            return None
        prefix = qname.split(":", maxsplit=1)[0]
        return self._namespaces_for(element).get(prefix)

    def _qname_key(self, qname: str, element: ET.Element | None = None) -> QNameKey:
        return (self._qname_namespace(qname, element), _local_name(qname))

    def _resolve_key(
        self,
        qname: str | QNameKey,
        *registries: dict[QNameKey, ET.Element],
        element: ET.Element | None = None,
    ) -> QNameKey:
        key = qname if isinstance(qname, tuple) else self._qname_key(qname, element)
        if any(key in registry for registry in registries):
            return key
        namespace, local = key
        if namespace is not None:
            return key
        matches = {candidate for registry in registries for candidate in registry if candidate[1] == local}
        if len(matches) == 1:
            return next(iter(matches))
        return key

    def _resolved_referenced_elements(self) -> set[QNameKey]:
        resolved = {self._resolve_key(ref, self.elements) for ref in self.referenced_elements}
        for ref in tuple(resolved):
            resolved.update(self.substitution_groups.get(ref, set()))
        return resolved

    def _definition_name(self, key: QNameKey) -> str:
        return self._definition_names.get(key, key[1])

    def _ref_for_key(self, key: QNameKey) -> str:
        return self._definition_ref(self._definition_name(key))

    def _namespaces_for(self, element: ET.Element | None) -> dict[str, str]:
        if element is None:  # pragma: no cover
            return self.namespaces
        return self._element_namespaces.get(id(element), self.namespaces)

    @staticmethod
    def _namespace_name(namespace: str | None) -> str:
        if not namespace:
            return "NoNamespace"
        parts = re.findall(r"[A-Za-z0-9]+", namespace)
        return "".join(_to_class_title(part) for part in parts) or "Namespace"

    @staticmethod
    def _sort_key(key: QNameKey) -> tuple[str, str]:
        namespace, local = key
        return namespace or "", local

    @staticmethod
    def _definition_ref(name: str) -> str:
        return f"#/definitions/{name}"


class XMLSchemaParser(JsonSchemaParser):
    """Parse XML Schema documents by converting them to JSON Schema first."""

    def __init__(
        self,
        source: str | Path | list[Path] | ParseResult,
        *,
        config: JSONSchemaParserConfig | None = None,
        **options: Unpack[JSONSchemaParserConfigDict],
    ) -> None:
        """Initialize the XML Schema parser with JSON Schema parser configuration."""
        super().__init__(source=source, config=config, **options)

    def parse_raw(self) -> None:
        """Parse all XML Schema input sources into data models."""
        for source, path_parts in self._get_context_source_path_parts():
            converter = _XMLSchemaConverter(base_path=self.base_path, encoding=self.encoding)
            raw_obj = converter.convert(source)
            source.raw_data = raw_obj
            if source.path.parts:
                self.remote_object_cache[str(self.base_path / source.path)] = raw_obj
            self.raw_obj = raw_obj
            title = str(raw_obj.get("title") or "Model")
            obj_name = self.class_name or title
            self._parse_file(raw_obj, obj_name, path_parts)

        self._resolve_unparsed_json_pointer()
        self._generate_forced_base_models()


__all__ = ["XMLSchemaParser", "is_xml_schema_text"]
