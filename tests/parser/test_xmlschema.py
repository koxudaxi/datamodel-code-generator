"""Tests for XML Schema parser internals."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from datamodel_code_generator import Error, InputFileType, generate
from datamodel_code_generator.parser.base import Source
from datamodel_code_generator.parser.xmlschema import (
    XML_SCHEMA_NAMESPACE,
    _copy_schema,
    _local_name,
    _namespace,
    _safe_float,
    _safe_int,
    _to_class_title,
    _XMLSchemaConverter,
    is_xml_schema_text,
)


def convert_xmlschema(text: str, tmp_path: Path) -> dict[str, object]:
    """Convert an XML Schema string to the intermediate JSON Schema object."""
    converter = _XMLSchemaConverter(base_path=tmp_path, encoding="utf-8")
    return converter.convert(Source(path=Path("schema.xsd"), text=text))


def test_xmlschema_helpers(tmp_path: Path) -> None:
    """Test XML Schema helper functions."""
    assert not is_xml_schema_text("not xml")
    assert not is_xml_schema_text("<broken")
    assert not is_xml_schema_text("<root />")
    assert _local_name("{urn:test}name") == "name"
    assert _local_name("xs:string") == "string"
    assert _namespace("{urn:test}name") == "urn:test"
    assert _namespace("name") is None
    assert _safe_int(None) is None
    assert _safe_int("bad") is None
    assert _safe_float(None) is None
    assert _safe_float("bad") is None
    assert _to_class_title("alreadyName") == "AlreadyName"
    assert _to_class_title("not-a-python-name") == "NotAPythonName"
    schema = {"items": [{"type": "string"}]}
    copied = _copy_schema(schema)
    copied["items"][0]["type"] = "integer"
    assert schema["items"][0]["type"] == "string"
    assert _XMLSchemaConverter._definition_ref("Thing") == "#/definitions/Thing"

    converter = _XMLSchemaConverter(base_path=tmp_path, encoding="utf-8")
    assert converter._namespaces_for(None) is converter.namespaces
    assert converter._namespace_name(None) == "NoNamespace"
    root = converter._parse_schema(
        """<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:dup="https://example.com/one">
  <xs:annotation xmlns:dup="https://example.com/two"/>
</xs:schema>""",
        tmp_path / "schema.xsd",
    )
    assert root.tag == f"{{{XML_SCHEMA_NAMESPACE}}}schema"
    type_element = ET.Element(f"{{{XML_SCHEMA_NAMESPACE}}}simpleType")
    converter.simple_types["urn:a-b", "Thing"] = type_element
    converter.simple_types["urn:a_b", "Thing"] = type_element
    converter._prepare_definition_names()
    assert converter._definition_name(("urn:a-b", "Thing")) != converter._definition_name(("urn:a_b", "Thing"))


def test_xmlschema_parse_errors(tmp_path: Path) -> None:
    """Test XML Schema parser errors include useful messages."""
    converter = _XMLSchemaConverter(base_path=tmp_path, encoding="utf-8")
    with pytest.raises(Error, match="Invalid XML Schema document"):
        converter.convert(Source(path=Path("schema.xsd"), text="<xs:schema"))
    with pytest.raises(Error, match="XML Schema root element must be xs:schema"):
        converter.convert(Source(path=Path("schema.xsd"), text="<root />"))


def test_xmlschema_converter_all_branches(tmp_path: Path) -> None:
    """Convert an XML Schema document that exercises supported XSD constructs."""
    (tmp_path / "included.xsd").write_text(
        """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:tns="https://example.com/xsd" targetNamespace="https://example.com/xsd">
  <xs:simpleType name="IncludedCode">
    <xs:annotation><xs:documentation>Included code docs</xs:documentation></xs:annotation>
    <xs:restriction base="xs:string">
      <xs:length value="3"/>
      <xs:pattern value="[A-Z]+"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:attribute name="globalFlag" type="xs:boolean" fixed="true"/>
  <xs:group name="namedGroup">
    <xs:sequence>
      <xs:element name="fromGroup" type="xs:string"/>
    </xs:sequence>
  </xs:group>
  <xs:attributeGroup name="namedAttributes">
    <xs:attribute ref="tns:globalFlag"/>
  </xs:attributeGroup>
</xs:schema>
""",
        encoding="utf-8",
    )
    xsd = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:tns="https://example.com/xsd" targetNamespace="https://example.com/xsd">
  <xs:include />
  <xs:include schemaLocation="missing.xsd"/>
  <xs:include schemaLocation="included.xsd"/>
  <xs:include schemaLocation="included.xsd"/>

  <xs:simpleType name="TextAlias">
    <xs:annotation><xs:documentation> Text alias docs </xs:documentation></xs:annotation>
  </xs:simpleType>
  <xs:simpleType name="TokenList">
    <xs:list itemType="xs:token"/>
  </xs:simpleType>
  <xs:simpleType name="InlineTokenList">
    <xs:list>
      <xs:simpleType>
        <xs:restriction base="xs:string">
          <xs:enumeration value="a"/>
          <xs:enumeration value="b"/>
        </xs:restriction>
      </xs:simpleType>
    </xs:list>
  </xs:simpleType>
  <xs:simpleType name="MixedUnion">
    <xs:union memberTypes="xs:string tns:TokenList">
      <xs:simpleType>
        <xs:restriction>
          <xs:simpleType>
            <xs:restriction base="xs:int"/>
          </xs:simpleType>
          <xs:minInclusive value="1"/>
        </xs:restriction>
      </xs:simpleType>
    </xs:union>
  </xs:simpleType>
  <xs:simpleType name="NumericFacet">
    <xs:restriction base="xs:decimal">
      <xs:enumeration value="1.5"/>
      <xs:minInclusive value="1"/>
      <xs:maxInclusive value="9"/>
      <xs:minExclusive value="0"/>
      <xs:maxExclusive value="10"/>
      <xs:totalDigits value="3"/>
      <xs:fractionDigits value="1"/>
      <xs:whiteSpace value="collapse"/>
      <xs:pattern value="[0-9.]+"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:simpleType name="BooleanFacet">
    <xs:restriction base="xs:boolean">
      <xs:enumeration value="true"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:simpleType name="ArrayFacet">
    <xs:restriction base="tns:TokenList">
      <xs:minLength value="1"/>
      <xs:maxLength value="4"/>
    </xs:restriction>
  </xs:simpleType>

  <xs:element name="sharedElement" type="xs:string"/>

  <xs:complexType name="BaseType">
    <xs:annotation><xs:documentation>Base docs</xs:documentation></xs:annotation>
    <xs:sequence minOccurs="0">
      <xs:element ref="tns:sharedElement" minOccurs="0" maxOccurs="2" nillable="true" default="x"/>
      <xs:choice>
        <xs:element name="left" type="xs:string"/>
        <xs:element name="right" type="xs:string"/>
      </xs:choice>
      <xs:group ref="tns:namedGroup"/>
      <xs:any/>
    </xs:sequence>
    <xs:attribute name="localNumber" type="xs:int" default="1"/>
    <xs:attribute name="inlineAttribute">
      <xs:simpleType>
        <xs:restriction base="xs:string">
          <xs:maxLength value="8"/>
        </xs:restriction>
      </xs:simpleType>
    </xs:attribute>
    <xs:attribute ref="tns:globalFlag" use="required"/>
    <xs:attribute use="prohibited" name="blocked"/>
    <xs:attributeGroup ref="tns:namedAttributes"/>
    <xs:anyAttribute/>
  </xs:complexType>

  <xs:complexType name="ExtendedType">
    <xs:complexContent>
      <xs:extension base="tns:BaseType">
        <xs:sequence>
          <xs:element name="extra" type="xs:unknown" minOccurs="0" maxOccurs="3"/>
        </xs:sequence>
      </xs:extension>
    </xs:complexContent>
  </xs:complexType>
  <xs:complexType name="RestrictedType">
    <xs:complexContent>
      <xs:restriction>
        <xs:sequence>
          <xs:element name="only" type="xs:string"/>
        </xs:sequence>
      </xs:restriction>
    </xs:complexContent>
  </xs:complexType>
  <xs:complexType name="FallbackContent">
    <xs:complexContent/>
  </xs:complexType>
  <xs:complexType name="Amount">
    <xs:simpleContent>
      <xs:restriction base="xs:int">
        <xs:minInclusive value="1"/>
        <xs:attribute name="unit" type="xs:string"/>
      </xs:restriction>
    </xs:simpleContent>
  </xs:complexType>
  <xs:complexType name="TextWithAttrs">
    <xs:simpleContent>
      <xs:extension>
        <xs:attribute name="kind" fixed="plain"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>

  <xs:element name="first" type="tns:ExtendedType"/>
  <xs:element name="second">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="inlineChild">
          <xs:simpleType>
            <xs:restriction base="xs:string">
              <xs:minLength value="2"/>
            </xs:restriction>
          </xs:simpleType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""
    schema = convert_xmlschema(xsd, tmp_path)

    assert schema["title"] == "Model"
    assert schema["required"] == ["sharedElement", "first", "second"]
    definitions = schema["definitions"]
    assert definitions["IncludedCode"]["description"] == "Included code docs"
    assert definitions["IncludedCode"]["minLength"] == 3
    assert definitions["IncludedCode"]["maxLength"] == 3
    assert definitions["TextAlias"]["description"] == "Text alias docs"
    assert definitions["InlineTokenList"]["items"]["enum"] == ["a", "b"]
    assert definitions["MixedUnion"]["anyOf"][1] == {"$ref": "#/definitions/TokenList"}
    assert definitions["NumericFacet"]["enum"] == [1.5]
    assert definitions["NumericFacet"]["x-xsd-totalDigits"] == 3
    assert definitions["BooleanFacet"]["enum"] == [True]
    assert definitions["ArrayFacet"]["minItems"] == 1
    assert definitions["ArrayFacet"]["maxItems"] == 4

    base_type = definitions["BaseType"]
    assert base_type["description"] == "Base docs"
    assert base_type["additionalProperties"] is True
    assert base_type["properties"]["sharedElement"]["type"] == "array"
    assert base_type["properties"]["sharedElement"]["items"]["nullable"] is True
    assert base_type["properties"]["sharedElement"]["maxItems"] == 2
    assert "left" not in base_type["required"]
    assert "fromGroup" not in base_type["required"]
    assert base_type["properties"]["localNumber"]["default"] == 1
    assert base_type["properties"]["inlineAttribute"]["maxLength"] == 8
    assert base_type["properties"]["globalFlag"]["const"] is True
    assert "blocked" not in base_type["properties"]

    assert definitions["ExtendedType"]["allOf"][0] == {"$ref": "#/definitions/BaseType"}
    assert definitions["ExtendedType"]["allOf"][1]["properties"]["extra"]["maxItems"] == 3
    assert definitions["RestrictedType"]["properties"]["only"]["type"] == "string"
    assert definitions["FallbackContent"]["type"] == "object"
    assert definitions["Amount"]["properties"]["value"]["minimum"] == 1
    assert definitions["TextWithAttrs"]["properties"]["value"]["type"] == "string"
    assert definitions["TextWithAttrs"]["properties"]["kind"]["const"] == "plain"
    assert definitions["sharedElement"]["type"] == "string"
    assert schema["properties"]["first"] == {"$ref": "#/definitions/ExtendedType"}
    assert schema["properties"]["second"]["properties"]["inlineChild"]["minLength"] == 2


def test_xmlschema_single_root_same_name_without_recursive_ref(tmp_path: Path) -> None:
    """Inline the root definition when nothing else references it."""
    xsd = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:complexType name="Item">
    <xs:sequence>
      <xs:element name="name" type="xs:string"/>
    </xs:sequence>
  </xs:complexType>
  <xs:element name="Item" type="Item"/>
</xs:schema>
"""
    schema = convert_xmlschema(xsd, tmp_path)

    assert schema["title"] == "Item"
    assert schema["properties"]["name"]["type"] == "string"
    assert "definitions" not in schema


def test_xmlschema_single_root_same_name_and_recursive_ref(tmp_path: Path) -> None:
    """Keep the root type name when a single global element matches its type name."""
    xsd = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:complexType name="Node">
    <xs:sequence>
      <xs:element name="child" type="Node" minOccurs="0"/>
    </xs:sequence>
  </xs:complexType>
  <xs:element name="Node" type="Node"/>
</xs:schema>
"""
    schema = convert_xmlschema(xsd, tmp_path)

    assert schema["title"] == "Node"
    assert schema["properties"]["child"] == {"$ref": "#/definitions/Node"}
    assert schema["definitions"]["Node"]["properties"]["child"] == {"$ref": "#/definitions/Node"}


def test_xmlschema_edge_cases(tmp_path: Path) -> None:
    """Convert XML Schema edge cases that exercise defensive branches."""
    xsd = """<?xml version="1.0"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:other="https://example.com/other">
  <xs:simpleType name="EmptyRestriction">
    <xs:restriction>
      <other:ignored value="ignored"/>
      <xs:minLength value="bad"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:group name="optionalGroup">
    <xs:sequence>
      <xs:element name="optionalGrouped" type="xs:string"/>
    </xs:sequence>
  </xs:group>
  <xs:complexType name="NoSimpleChild">
    <xs:simpleContent/>
  </xs:complexType>
  <xs:complexType name="Loose">
    <xs:group>
      <xs:sequence>
        <xs:element name="inlineGroupElement" type="xs:string" fixed="v">
          <xs:annotation>
            <xs:documentation>Element docs</xs:documentation>
            <xs:documentation> </xs:documentation>
            <xs:documentation>More element docs</xs:documentation>
          </xs:annotation>
        </xs:element>
      </xs:sequence>
    </xs:group>
    <xs:sequence minOccurs="0">
      <xs:group ref="optionalGroup"/>
    </xs:sequence>
    <xs:sequence>
      <xs:annotation/>
      <xs:element/>
      <xs:element name="unboundedItem" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
      <xs:element name="badOccurs" type="xs:string" maxOccurs="bad"/>
      <xs:element name="empty"/>
      <xs:group ref="missingGroup"/>
      <xs:any/>
      <xs:element name="unknownNamespace" type="other:Thing"/>
    </xs:sequence>
    <xs:attributeGroup>
      <xs:attribute name="localGrouped">
        <xs:annotation><xs:documentation>Grouped attr</xs:documentation></xs:annotation>
      </xs:attribute>
    </xs:attributeGroup>
    <xs:attributeGroup ref="missingGroup"/>
    <xs:attribute/>
  </xs:complexType>
  <xs:attributeGroup name="topAttributes">
    <xs:attribute name="topAttribute" type="xs:string"/>
  </xs:attributeGroup>
  <other:named name="ignored"/>
  <xs:simpleType name="AfterTopAttributes"/>
  <xs:element name="plain" type="xs:string"/>
  <xs:element name="loose" type="Loose"/>
</xs:schema>
"""
    converter = _XMLSchemaConverter(base_path=tmp_path, encoding="utf-8")
    schema = converter.convert(Source(path=Path("schema.xsd"), text=xsd))

    definitions = schema["definitions"]
    assert definitions["EmptyRestriction"]["type"] == "string"
    assert "minLength" not in definitions["EmptyRestriction"]
    assert definitions["NoSimpleChild"]["properties"]["value"]["type"] == "string"

    loose = definitions["Loose"]
    assert loose["properties"]["inlineGroupElement"]["description"] == "Element docs\n\nMore element docs"
    assert loose["properties"]["inlineGroupElement"]["const"] == "v"
    assert loose["properties"]["unboundedItem"]["type"] == "array"
    assert "maxItems" not in loose["properties"]["unboundedItem"]
    assert loose["properties"]["badOccurs"]["type"] == "array"
    assert "maxItems" not in loose["properties"]["badOccurs"]
    assert loose["properties"]["empty"] == {}
    assert loose["properties"]["unknownNamespace"] == {}
    assert loose["properties"]["localGrouped"]["description"] == "Grouped attr"
    assert loose["additionalProperties"] is True
    assert "optionalGrouped" not in loose["required"]
    assert schema["properties"]["plain"]["title"] == "Plain"

    nameless_element = ET.Element(f"{{{XML_SCHEMA_NAMESPACE}}}element")
    assert converter._convert_global_element_as_property(nameless_element) == {}
    loose_key = (None, "Loose")
    assert converter._build_definition(loose_key) is converter._built_definitions[loose_key]
    loop_key = (None, "Loop")
    converter._building_definitions.add(loop_key)
    assert converter._build_definition(loop_key) == {"$ref": "#/definitions/Loop"}
    converter._building_definitions.remove(loop_key)
    assert converter._build_definition((None, "Missing")) == {"title": "Missing"}
    assert converter._contains_ref([{"$ref": "#/definitions/Loose"}], "#/definitions/Loose")
    assert converter._schema_for_qname(None) == {}


def test_xmlschema_import_resolves_by_namespace(tmp_path: Path) -> None:
    """Resolve imported components and exclude imported elements from root selection."""
    (tmp_path / "external.xsd").write_text(
        """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="https://example.com/external">
  <xs:simpleType name="ImportedCode">
    <xs:restriction base="xs:string">
      <xs:length value="5"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:element name="externalRoot" type="ImportedCode"/>
</xs:schema>
""",
        encoding="utf-8",
    )
    xsd = """<?xml version="1.0"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:ext="https://example.com/external"
    targetNamespace="https://example.com/main">
  <xs:import namespace="https://example.com/external" schemaLocation="external.xsd"/>
  <xs:element name="code" type="ext:ImportedCode"/>
</xs:schema>
"""
    schema = convert_xmlschema(xsd, tmp_path)

    assert schema["title"] == "Code"
    assert schema["allOf"] == [{"$ref": "#/definitions/ImportedCode"}]
    assert "externalRoot" not in schema.get("properties", {})
    assert schema["definitions"]["ImportedCode"]["minLength"] == 5
    assert schema["definitions"]["ImportedCode"]["maxLength"] == 5


def test_xmlschema_imported_namespace_name_collisions(tmp_path: Path) -> None:
    """Keep imported definitions distinct when local names collide."""
    (tmp_path / "shipping.xsd").write_text(
        """<?xml version="1.0"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:common="https://example.com/common/shipping"
    targetNamespace="https://example.com/shipping">
  <xs:import namespace="https://example.com/common/shipping" schemaLocation="shipping_common.xsd"/>
  <xs:complexType name="Address">
    <xs:sequence>
      <xs:element name="code" type="common:Code"/>
    </xs:sequence>
  </xs:complexType>
</xs:schema>
""",
        encoding="utf-8",
    )
    (tmp_path / "shipping_common.xsd").write_text(
        """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="https://example.com/common/shipping">
  <xs:simpleType name="Code">
    <xs:restriction base="xs:string">
      <xs:minLength value="2"/>
    </xs:restriction>
  </xs:simpleType>
</xs:schema>
""",
        encoding="utf-8",
    )
    (tmp_path / "billing.xsd").write_text(
        """<?xml version="1.0"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:common="https://example.com/common/billing"
    targetNamespace="https://example.com/billing">
  <xs:import namespace="https://example.com/common/billing" schemaLocation="billing_common.xsd"/>
  <xs:complexType name="Address">
    <xs:sequence>
      <xs:element name="code" type="common:Code"/>
    </xs:sequence>
  </xs:complexType>
</xs:schema>
""",
        encoding="utf-8",
    )
    (tmp_path / "billing_common.xsd").write_text(
        """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="https://example.com/common/billing">
  <xs:simpleType name="Code">
    <xs:restriction base="xs:string">
      <xs:maxLength value="4"/>
    </xs:restriction>
  </xs:simpleType>
</xs:schema>
""",
        encoding="utf-8",
    )
    xsd = """<?xml version="1.0"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:ship="https://example.com/shipping"
    xmlns:bill="https://example.com/billing"
    targetNamespace="https://example.com/order">
  <xs:import namespace="https://example.com/shipping" schemaLocation="shipping.xsd"/>
  <xs:import namespace="https://example.com/billing" schemaLocation="billing.xsd"/>
  <xs:element name="shipping" type="ship:Address"/>
  <xs:element name="billing" type="bill:Address"/>
</xs:schema>
"""
    schema = convert_xmlschema(xsd, tmp_path)
    definitions = schema["definitions"]

    shipping_ref = schema["properties"]["shipping"]["$ref"]
    billing_ref = schema["properties"]["billing"]["$ref"]
    assert shipping_ref != billing_ref

    shipping = definitions[shipping_ref.rsplit("/", maxsplit=1)[-1]]
    billing = definitions[billing_ref.rsplit("/", maxsplit=1)[-1]]
    shipping_code = definitions[shipping["properties"]["code"]["$ref"].rsplit("/", maxsplit=1)[-1]]
    billing_code = definitions[billing["properties"]["code"]["$ref"].rsplit("/", maxsplit=1)[-1]]
    assert shipping_code["minLength"] == 2
    assert billing_code["maxLength"] == 4


def test_xmlschema_namespace_fallback_and_referenced_name_collision(tmp_path: Path) -> None:
    """Resolve unprefixed target-namespace names and avoid duplicate referenced definitions."""
    xsd = """<?xml version="1.0"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="https://example.com/main">
  <xs:complexType name="LocalThing">
    <xs:sequence>
      <xs:element name="value" type="xs:string"/>
    </xs:sequence>
  </xs:complexType>
  <xs:complexType name="Shared">
    <xs:sequence>
      <xs:element name="name" type="xs:string"/>
    </xs:sequence>
  </xs:complexType>
  <xs:element name="Shared" type="LocalThing"/>
  <xs:element name="holder">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="Shared"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""
    schema = convert_xmlschema(xsd, tmp_path)

    assert schema["properties"]["Shared"] == {"$ref": "#/definitions/LocalThing"}
    assert schema["properties"]["holder"]["properties"]["Shared"] == {"$ref": "#/definitions/Shared"}
    assert schema["definitions"]["LocalThing"]["properties"]["value"]["type"] == "string"
    assert schema["definitions"]["Shared"]["properties"]["name"]["type"] == "string"


def test_xmlschema_generate_smoke() -> None:
    """Generate Python models through the public XML Schema parser path."""
    output = generate(
        """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Foo">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="bar" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>""",
        input_file_type=InputFileType.XMLSchema,
        disable_timestamp=True,
    )
    assert "class Foo(BaseModel):" in output
    assert "bar: str" in output
