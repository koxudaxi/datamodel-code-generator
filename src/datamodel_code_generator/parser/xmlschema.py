"""XML Schema parser implementation.

Converts W3C XML Schema (XSD) documents into the JSON Schema shape consumed by
the existing JSON Schema parser.
"""

from __future__ import annotations

import copy
import io
import re
from pathlib import Path  # noqa: TC003 - used by runtime path resolution
from typing import TYPE_CHECKING, Any, cast
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

JsonSchema = dict[str, Any]
PYTHON_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


STRING_SCHEMA: JsonSchema = {"type": "string"}
INTEGER_SCHEMA: JsonSchema = {"type": "integer"}
NUMBER_SCHEMA: JsonSchema = {"type": "number"}
BOOLEAN_SCHEMA: JsonSchema = {"type": "boolean"}

BUILTIN_TYPE_SCHEMAS: dict[str, JsonSchema] = {
    "anySimpleType": {},
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
}


def is_xml_schema_text(text: str) -> bool:
    """Return whether text is an XML Schema document."""
    if not text.lstrip().startswith("<"):
        return False
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


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
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
        self.simple_types: dict[str, ET.Element] = {}
        self.complex_types: dict[str, ET.Element] = {}
        self.elements: dict[str, ET.Element] = {}
        self.attributes: dict[str, ET.Element] = {}
        self.groups: dict[str, ET.Element] = {}
        self.attribute_groups: dict[str, ET.Element] = {}
        self.referenced_elements: set[str] = set()
        self._loaded_locations: set[Path] = set()
        self._building_definitions: set[str] = set()
        self._definitions: dict[str, JsonSchema] = {}

    def convert(self, source: Source) -> dict[str, YamlValue]:
        root = self._parse_schema(source.text, self.base_path / source.path)
        self._collect_schema(root, source_path=self.base_path / source.path)

        self._definitions = self._build_definitions()
        global_elements = [element for element in self.elements.values() if element.get("name")]

        if len(global_elements) == 1:
            root_element = global_elements[0]
            root_name = root_element.get("name") or "Model"
            root_type_name = _local_name(root_element.get("type", ""))
            if root_type_name == root_name and root_name in self._definitions:
                schema = _copy_schema(self._definitions[root_name])
                schema.setdefault("title", _to_class_title(root_name))
                if not self._has_definition_ref(root_name):
                    self._definitions.pop(root_name)
            else:
                schema = self._convert_global_element_as_root(root_element, root_name)
        else:
            properties: dict[str, JsonSchema] = {}
            for element in global_elements:
                name = element.get("name")
                if name:
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
        return schema

    def _parse_schema(self, text: str, source_path: Path) -> ET.Element:
        try:
            for _, namespace in ET.iterparse(io.StringIO(text), events=("start-ns",)):  # noqa: S314
                prefix, uri = cast("tuple[str, str]", namespace)
                self.namespaces.setdefault(prefix, uri)
            root = ET.fromstring(text)  # noqa: S314
        except ET.ParseError as exc:
            msg = f"Invalid XML Schema document {source_path}: {exc}"
            raise Error(msg) from exc
        if root.tag != XML_SCHEMA_TAG:
            msg = f"XML Schema root element must be xs:schema: {source_path}"
            raise Error(msg)
        if target_namespace := root.get("targetNamespace"):
            self.target_namespace = target_namespace
        return root

    def _collect_schema(self, root: ET.Element, source_path: Path) -> None:  # noqa: PLR0912
        source_dir = source_path.parent if source_path.name else self.base_path
        for child in _xsd_children(root, "include", "import", "redefine"):
            schema_location = child.get("schemaLocation")
            if not schema_location:
                continue
            location = (source_dir / schema_location).resolve()
            if location in self._loaded_locations or not location.is_file():
                continue
            self._loaded_locations.add(location)
            included_root = self._parse_schema(location.read_text(encoding=self.encoding), location)
            self._collect_schema(included_root, location)

        for child in root:
            name = child.get("name")
            if not name:
                continue
            if _is_xsd_element(child, "simpleType"):
                self.simple_types.setdefault(name, child)
            elif _is_xsd_element(child, "complexType"):
                self.complex_types.setdefault(name, child)
            elif _is_xsd_element(child, "element"):
                self.elements.setdefault(name, child)
            elif _is_xsd_element(child, "attribute"):
                self.attributes.setdefault(name, child)
            elif _is_xsd_element(child, "group"):
                self.groups.setdefault(name, child)
            elif _is_xsd_element(child, "attributeGroup"):
                self.attribute_groups.setdefault(name, child)
        for child in root.iter():
            if _namespace(child.tag) == XML_SCHEMA_NAMESPACE and (ref := child.get("ref")):
                self.referenced_elements.add(_local_name(ref))

    def _build_definitions(self) -> dict[str, JsonSchema]:
        definitions: dict[str, JsonSchema] = {}
        for name in sorted(self.simple_types):
            definitions[name] = self._build_definition(name)
        for name in sorted(self.complex_types):
            definitions[name] = self._build_definition(name)
        for name in sorted(self.referenced_elements):
            if name in self.elements and name not in definitions:
                definitions[name] = self._build_definition(name)
        return definitions

    def _build_definition(self, name: str) -> JsonSchema:
        if name in self._definitions:
            return self._definitions[name]
        if name in self._building_definitions:
            return {"$ref": self._definition_ref(name)}
        self._building_definitions.add(name)
        simple_type = self.simple_types.get(name)
        complex_type = self.complex_types.get(name)
        element = self.elements.get(name)
        if simple_type is not None:
            schema = self._convert_simple_type(simple_type)
        elif complex_type is not None:
            schema = self._convert_complex_type(complex_type)
        elif element is not None:
            schema = self._convert_element(element)
        else:
            schema = {}
        schema.setdefault("title", _to_class_title(name))
        self._building_definitions.remove(name)
        self._definitions[name] = schema
        return schema

    def _has_definition_ref(self, name: str) -> bool:
        ref = self._definition_ref(name)
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
        name = element.get("name")
        if name:
            schema.setdefault("title", _to_class_title(name))
        return schema

    def _convert_element(self, element: ET.Element) -> JsonSchema:
        ref = element.get("ref")
        if ref:
            schema = {"$ref": self._definition_ref(_local_name(ref))}
        elif type_name := element.get("type"):
            schema = self._schema_for_qname(type_name)
        else:
            simple_type = _first_xsd_child(element, "simpleType")
            complex_type = _first_xsd_child(element, "complexType")
            if simple_type is not None:
                schema = self._convert_simple_type(simple_type)
            elif complex_type is not None:
                schema = self._convert_complex_type(complex_type)
            else:
                schema = {}

        schema = self._apply_common_element_metadata(element, _copy_schema(schema))
        return self._apply_occurs(element, schema)

    def _apply_common_element_metadata(self, element: ET.Element, schema: JsonSchema) -> JsonSchema:
        if documentation := _documentation(element):
            schema["description"] = documentation
        if "default" in element.attrib:
            schema["default"] = self._parse_literal(str(element.get("default")), schema)
        if "fixed" in element.attrib:
            schema["const"] = self._parse_literal(str(element.get("fixed")), schema)
        if element.get("nillable") == "true":
            schema["nullable"] = True
        return schema

    def _apply_occurs(self, element: ET.Element, schema: JsonSchema) -> JsonSchema:  # noqa: PLR6301
        min_occurs = _safe_int(element.get("minOccurs")) or 0 if element.get("minOccurs") else 1
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
        return array_schema

    def _convert_simple_type(self, simple_type: ET.Element) -> JsonSchema:
        restriction = _first_xsd_child(simple_type, "restriction")
        list_element = _first_xsd_child(simple_type, "list")
        union_element = _first_xsd_child(simple_type, "union")
        if restriction is not None:
            base_schema = self._restriction_base_schema(restriction)
            schema = self._apply_restriction_facets(restriction, base_schema)
        elif list_element is not None:
            item_type = list_element.get("itemType")
            item_schema = self._schema_for_qname(item_type) if item_type else {}
            inline_item_type = _first_xsd_child(list_element, "simpleType")
            if inline_item_type is not None:
                item_schema = self._convert_simple_type(inline_item_type)
            schema = {"type": "array", "items": item_schema}
        elif union_element is not None:
            schemas = []
            member_types = (union_element.get("memberTypes") or "").split()
            schemas.extend(self._schema_for_qname(member_type) for member_type in member_types)
            schemas.extend(self._convert_simple_type(child) for child in _xsd_children(union_element, "simpleType"))
            schema = {"anyOf": schemas} if schemas else {}
        else:
            schema = STRING_SCHEMA

        if documentation := _documentation(simple_type):
            schema = _copy_schema(schema)
            schema["description"] = documentation
        return schema

    def _restriction_base_schema(self, restriction: ET.Element) -> JsonSchema:
        if base := restriction.get("base"):
            return self._schema_for_qname(base)
        simple_type = _first_xsd_child(restriction, "simpleType")
        if simple_type is not None:
            return self._convert_simple_type(simple_type)
        return STRING_SCHEMA

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
            if name == "enumeration":
                enum_values.append(self._parse_literal(value, schema))
            elif name == "pattern":
                schema["pattern"] = value
            elif name == "length":
                self._set_length(schema, value, same=True)
            elif name == "minLength":
                self._set_length(schema, value, same=False, minimum=True)
            elif name == "maxLength":
                self._set_length(schema, value, same=False, minimum=False)
            elif name == "minInclusive":
                schema["minimum"] = self._parse_number(value, schema)
            elif name == "maxInclusive":
                schema["maximum"] = self._parse_number(value, schema)
            elif name == "minExclusive":
                schema["exclusiveMinimum"] = self._parse_number(value, schema)
            elif name == "maxExclusive":
                schema["exclusiveMaximum"] = self._parse_number(value, schema)
            elif name == "totalDigits":
                schema["x-xsd-totalDigits"] = _safe_int(value)
            elif name == "fractionDigits":
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
            return _safe_int(value) if _safe_int(value) is not None else value
        if schema_type == "number":
            return _safe_float(value) if _safe_float(value) is not None else value
        if schema_type == "boolean":
            return value in {"true", "1"}
        return value

    def _parse_number(self, value: str, schema: JsonSchema) -> int | float | str:  # noqa: PLR6301
        if schema.get("type") == "integer":
            integer = _safe_int(value)
            return integer if integer is not None else value
        number = _safe_float(value)
        return number if number is not None else value

    def _convert_complex_type(self, complex_type: ET.Element) -> JsonSchema:
        complex_content = _first_xsd_child(complex_type, "complexContent")
        simple_content = _first_xsd_child(complex_type, "simpleContent")
        if complex_content is not None:
            return self._convert_complex_content(complex_content, complex_type)
        if simple_content is not None:
            return self._convert_simple_content(simple_content, complex_type)

        schema: JsonSchema = {"type": "object", "properties": {}}
        self._apply_model_group(complex_type, schema)
        self._apply_attributes(complex_type, schema)
        if documentation := _documentation(complex_type):
            schema["description"] = documentation
        return schema

    def _convert_complex_content(self, complex_content: ET.Element, owner: ET.Element) -> JsonSchema:
        child = _first_xsd_child(complex_content, "extension", "restriction")
        if child is None:
            return self._convert_complex_type_without_content(owner)

        schema: JsonSchema = {"type": "object", "properties": {}}
        self._apply_model_group(child, schema)
        self._apply_attributes(child, schema)
        if _local_name(child.tag) == "extension" and (base := child.get("base")):
            return {"allOf": [self._schema_for_qname(base), schema]}
        return schema

    def _convert_complex_type_without_content(self, complex_type: ET.Element) -> JsonSchema:
        schema: JsonSchema = {"type": "object", "properties": {}}
        self._apply_model_group(complex_type, schema)
        self._apply_attributes(complex_type, schema)
        return schema

    def _convert_simple_content(self, simple_content: ET.Element, owner: ET.Element) -> JsonSchema:
        child = _first_xsd_child(simple_content, "extension", "restriction")
        value_schema = (
            self._schema_for_qname(child.get("base")) if child is not None and child.get("base") else STRING_SCHEMA
        )
        if child is not None and _local_name(child.tag) == "restriction":
            value_schema = self._apply_restriction_facets(child, value_schema)

        schema: JsonSchema = {"type": "object", "properties": {"value": value_schema}, "required": ["value"]}
        self._apply_attributes(owner, schema)
        if child is not None:
            self._apply_attributes(child, schema)
        return schema

    def _apply_model_group(self, owner: ET.Element, schema: JsonSchema) -> None:
        for child in owner:
            if _is_xsd_element(child, "sequence", "all", "choice"):
                self._apply_particle(child, schema, parent_required=True)
            elif _is_xsd_element(child, "group"):
                self._apply_group(child, schema, parent_required=True)

    def _apply_particle(self, particle: ET.Element, schema: JsonSchema, *, parent_required: bool) -> None:
        particle_required = (
            parent_required and particle.get("minOccurs", "1") != "0" and _local_name(particle.tag) != "choice"
        )
        for child in particle:
            if _is_xsd_element(child, "element"):
                self._add_property_from_element(child, schema, required=particle_required)
            elif _is_xsd_element(child, "sequence", "all", "choice"):
                self._apply_particle(child, schema, parent_required=particle_required)
            elif _is_xsd_element(child, "group"):
                self._apply_group(child, schema, parent_required=particle_required)
            elif _is_xsd_element(child, "any"):
                schema["additionalProperties"] = True

    def _apply_group(self, group: ET.Element, schema: JsonSchema, *, parent_required: bool) -> None:
        ref = group.get("ref")
        if not ref:
            self._apply_particle(group, schema, parent_required=parent_required)
            return
        target = self.groups.get(_local_name(ref))
        if target is not None:
            self._apply_model_group(target, schema)

    def _add_property_from_element(self, element: ET.Element, schema: JsonSchema, *, required: bool) -> None:
        name = element.get("name") or _local_name(element.get("ref", ""))
        if not name:
            return
        properties = schema.setdefault("properties", {})
        properties[name] = self._convert_element(element)
        if required and element.get("minOccurs", "1") != "0":
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
        target = self.attribute_groups.get(_local_name(ref))
        if target is not None:
            self._apply_attributes(target, schema)

    def _add_attribute(self, attribute: ET.Element, schema: JsonSchema) -> None:
        if attribute.get("use") == "prohibited":
            return
        ref = attribute.get("ref")
        source_attribute = self.attributes.get(_local_name(ref)) if ref else None
        if source_attribute is None:
            source_attribute = attribute
        name = attribute.get("name") or source_attribute.get("name") or _local_name(ref or "")
        if not name:
            return
        if type_name := attribute.get("type") or source_attribute.get("type"):
            attribute_schema = self._schema_for_qname(type_name)
        else:
            simple_type = _first_xsd_child(attribute, "simpleType")
            if simple_type is None:
                simple_type = _first_xsd_child(source_attribute, "simpleType")
            attribute_schema = self._convert_simple_type(simple_type) if simple_type is not None else STRING_SCHEMA
        attribute_schema = _copy_schema(attribute_schema)
        if documentation := _documentation(attribute) or _documentation(source_attribute):
            attribute_schema["description"] = documentation
        if default := attribute.get("default") or source_attribute.get("default"):
            attribute_schema["default"] = self._parse_literal(default, attribute_schema)
        if fixed := attribute.get("fixed") or source_attribute.get("fixed"):
            attribute_schema["const"] = self._parse_literal(fixed, attribute_schema)
        schema.setdefault("properties", {})[name] = attribute_schema
        if (attribute.get("use") or source_attribute.get("use")) == "required":
            schema.setdefault("required", []).append(name)

    def _schema_for_qname(self, qname: str | None) -> JsonSchema:
        if not qname:
            return {}
        local = _local_name(qname)
        namespace = self._qname_namespace(qname)
        is_unprefixed_builtin = namespace is None and local in BUILTIN_TYPE_SCHEMAS
        is_user_defined = local in self.simple_types or local in self.complex_types or local in self.elements
        if namespace == XML_SCHEMA_NAMESPACE or (is_unprefixed_builtin and not is_user_defined):
            return _copy_schema(BUILTIN_TYPE_SCHEMAS.get(local, STRING_SCHEMA))
        if is_user_defined:
            return {"$ref": self._definition_ref(local)}
        return _copy_schema(BUILTIN_TYPE_SCHEMAS.get(local, {}))

    def _qname_namespace(self, qname: str) -> str | None:
        if ":" not in qname:
            return None
        prefix = qname.split(":", maxsplit=1)[0]
        return self.namespaces.get(prefix)

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
        for source, _path_parts in self._get_context_source_path_parts():
            converter = _XMLSchemaConverter(base_path=self.base_path, encoding=self.encoding)
            raw_obj = converter.convert(source)
            self.raw_obj = raw_obj
            title = str(raw_obj.get("title") or "Model")
            obj_name = self.class_name or title
            self._parse_file(raw_obj, obj_name, [])

        self._resolve_unparsed_json_pointer()
        self._generate_forced_base_models()


__all__ = ["XMLSchemaParser", "is_xml_schema_text"]
