"""Tests for XML Schema code generation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from datamodel_code_generator import InputFileType
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.parser.xmlschema import (
    _clear_xml_schema_data_cache,
    _clear_xml_text_cache,
    _read_xml_text,
)
from tests.main.conftest import (
    XML_SCHEMA_DATA_PATH,
    assert_path_cache_invalidates_after_write,
    assert_path_cache_reuses_value,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.xmlschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_main_xmlschema_purchase_order(output_file: Path) -> None:
    """Generate models from an XML Schema document."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "purchase_order.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="purchase_order.py",
    )


def test_main_xmlschema_with_parsed_source_cache(output_file: Path) -> None:
    """Generate XML Schema models with process-local parsed source cache enabled."""
    _clear_xml_schema_data_cache()
    run_generate_file_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "purchase_order.xsd",
        output_path=output_file,
        input_file_type=InputFileType.XMLSchema,
        assert_func=assert_file_content,
        expected_file="purchase_order.py",
    )


def test_read_xml_text_caches_raw_source(tmp_path: Path) -> None:
    """Reuse raw XML source text by path and content hash."""
    schema_path = tmp_path / "schema.xsd"
    schema_path.write_text(
        (XML_SCHEMA_DATA_PATH / "single_root_item.xsd").read_text(encoding="utf-8"), encoding="utf-8"
    )
    _clear_xml_text_cache()

    assert_path_cache_reuses_value(_read_xml_text, schema_path, warmups=1)


def test_read_xml_text_invalidates_updated_raw_source(tmp_path: Path) -> None:
    """Reload raw XML source text when the local file changes."""
    schema_path = tmp_path / "schema.xsd"
    schema_path.write_text(
        (XML_SCHEMA_DATA_PATH / "single_root_item.xsd").read_text(encoding="utf-8"), encoding="utf-8"
    )
    _clear_xml_text_cache()

    updated_text = (XML_SCHEMA_DATA_PATH / "inline_root.xsd").read_text(encoding="utf-8")
    assert_path_cache_invalidates_after_write(
        _read_xml_text,
        schema_path,
        updated_text,
        updated_text.replace("\n", os.linesep),
    )


def test_main_xmlschema_purchase_order_from_normalized_external_path(tmp_path: Path, output_file: Path) -> None:
    """Generate XML Schema models when the external input path needs normalization."""
    redirect_dir = tmp_path / "redirect"
    redirect_dir.mkdir()
    run_main_and_assert(
        input_path=redirect_dir / ".." / "purchase_order.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="purchase_order.py",
        copy_files=[
            (XML_SCHEMA_DATA_PATH / "purchase_order.xsd", tmp_path / "purchase_order.xsd"),
            (XML_SCHEMA_DATA_PATH / "common.xsd", tmp_path / "common.xsd"),
        ],
    )


def test_main_xmlschema_infer_input_file_type(output_file: Path) -> None:
    """Infer XML Schema input and generate a model."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "single_root_item.xsd",
        output_path=output_file,
        assert_func=assert_file_content,
        expected_file="single_root_item.py",
    )


def test_main_xmlschema_supported_constructs(output_file: Path) -> None:
    """Generate models for supported XML Schema constructs."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "constructs_matrix.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="constructs_matrix.py",
    )


def test_main_xmlschema_edge_cases(output_file: Path) -> None:
    """Generate models for XML Schema edge cases."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "edge_cases.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="edge_cases.py",
    )


def test_main_xmlschema_fixed_decimal(output_file: Path) -> None:
    """Generate Decimal defaults for fixed XML Schema decimal values."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "fixed_decimal.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="fixed_decimal.py",
    )


def test_main_xmlschema_special_float_defaults(output_file: Path) -> None:
    """Generate non-finite float defaults from XML Schema lexical values."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "special_float_defaults.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="special_float_defaults.py",
    )


def test_main_xmlschema_special_float_bounds(output_file: Path) -> None:
    """Generate non-finite float bounds from XML Schema lexical values."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "special_float_bounds.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="special_float_bounds.py",
    )


def test_main_xmlschema_union_defaults(output_file: Path) -> None:
    """Generate typed defaults for XML Schema union values."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "union_defaults.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="union_defaults.py",
    )


def test_main_xmlschema_boolean_whitespace_defaults(output_file: Path) -> None:
    """Generate boolean defaults after XML Schema whitespace normalization."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "boolean_whitespace_defaults.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="boolean_whitespace_defaults.py",
    )


def test_main_xmlschema_temporal_defaults(output_file: Path) -> None:
    """Generate typed defaults for XML Schema temporal lexical values."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "temporal_defaults.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="temporal_defaults.py",
    )


def test_main_xmlschema_single_root_same_name(output_file: Path) -> None:
    """Inline a single root type when no other definition references it."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "single_root_item.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="single_root_item.py",
    )


def test_main_xmlschema_inline_root(output_file: Path) -> None:
    """Generate a titled model for a single inline root element."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "inline_root.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="inline_root.py",
    )


def test_main_xmlschema_recursive_root(output_file: Path) -> None:
    """Keep recursive root definitions addressable."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "recursive_node.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="recursive_node.py",
    )


def test_main_xmlschema_import_resolves_by_namespace(output_file: Path) -> None:
    """Resolve imported components by namespace without selecting imported roots."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "import_namespace.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="import_namespace.py",
    )


def test_main_xmlschema_imported_namespace_name_collisions(output_file: Path) -> None:
    """Keep imported definitions distinct when local names collide."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "namespace_collisions.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="namespace_collisions.py",
    )


def test_main_xmlschema_no_namespace_name_collision(output_file: Path) -> None:
    """Name no-namespace definitions distinctly when imported names collide."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "no_namespace_collision.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="no_namespace_collision.py",
    )


def test_main_xmlschema_namespace_fallback(output_file: Path) -> None:
    """Resolve unprefixed target-namespace names and referenced definitions."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "namespace_fallback.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="namespace_fallback.py",
    )


def test_main_xmlschema_advanced_constructs(output_file: Path) -> None:
    """Generate models for abstract substitution groups and mixed content."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "advanced_constructs.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="advanced_constructs.py",
    )


def test_main_xmlschema_multiple_substitution_groups(output_file: Path) -> None:
    """Generate models for elements affiliated with multiple substitution groups."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "multiple_substitution_groups.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="multiple_substitution_groups.py",
    )


def test_main_xmlschema_include_local_elements(output_file: Path) -> None:
    """Treat included global elements as local root candidates."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "include_local_elements.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="include_local_elements.py",
    )


def test_main_xmlschema_type_element_symbol_spaces(output_file: Path) -> None:
    """Keep same-name type definitions and element declarations distinct."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "type_element_symbol_spaces.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="type_element_symbol_spaces.py",
    )


def test_main_xmlschema_model_groups_and_wildcards(output_file: Path) -> None:
    """Generate models for repeating model groups, defaults, fixed values, and wildcards."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "model_groups_and_wildcards.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="model_groups_and_wildcards.py",
    )


def test_main_xmlschema_spec_constructs(output_file: Path) -> None:
    """Generate models for additional XML Schema 1.0 declaration and particle constructs."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "spec_constructs.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="spec_constructs.py",
    )


def test_main_xmlschema_list_defaults(output_file: Path) -> None:
    """Generate list-typed defaults from XML Schema list lexical values."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "list_defaults.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="list_defaults.py",
    )


def test_main_xmlschema_utf16_input(tmp_path: Path, output_file: Path) -> None:
    """Generate models from XML Schema files that rely on XML encoding detection."""
    input_path = tmp_path / "utf16_schema.xsd"
    input_path.write_text(
        """<?xml version="1.0" encoding="UTF-16"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="utf16Item">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="value" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
""",
        encoding="utf-16",
    )

    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
    )


def test_main_xmlschema_unicode_ncname_alias(tmp_path: Path, output_file: Path) -> None:
    """Generate aliases for XML NCName values that are not valid Python identifiers."""
    input_path = tmp_path / "unicode_ncname_schema.xsd"
    input_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType>
      <xs:attribute name="ำ62" type="xs:integer"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
""",
        encoding="utf-8",
    )

    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
    )


def test_main_xmlschema_unsupported_xsd_pattern_importable(tmp_path: Path, output_file: Path) -> None:
    """Skip XSD regex facets that Python/Pydantic cannot compile at import time."""
    input_path = tmp_path / "unsupported_xsd_pattern.xsd"
    input_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:simpleType name="NameToken">
    <xs:restriction base="xs:string">
      <xs:pattern value="\\i\\c*"/>
    </xs:restriction>
  </xs:simpleType>
  <xs:simpleType name="BrokenPattern">
    <xs:restriction base="xs:string">
      <xs:pattern value="("/>
    </xs:restriction>
  </xs:simpleType>
  <xs:element name="root" type="NameToken"/>
  <xs:element name="broken" type="BrokenPattern"/>
</xs:schema>
""",
        encoding="utf-8",
    )

    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
    )


def test_main_xmlschema_self_extension_without_redefine_importable(tmp_path: Path, output_file: Path) -> None:
    """Emit the local content for a self-extension when no redefined base exists."""
    input_path = tmp_path / "self_extension_without_redefine.xsd"
    input_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:complexType name="Node">
    <xs:complexContent>
      <xs:extension base="Node">
        <xs:sequence>
          <xs:element name="child" type="xs:string"/>
        </xs:sequence>
      </xs:extension>
    </xs:complexContent>
  </xs:complexType>
  <xs:element name="root" type="Node"/>
</xs:schema>
""",
        encoding="utf-8",
    )

    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
    )


def test_main_xmlschema_redefine_self_references_importable(tmp_path: Path, output_file: Path) -> None:
    """Resolve self-references inside xs:redefine against the original definition."""
    (tmp_path / "base.xsd").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="urn:redefine" xmlns="urn:redefine">
  <xs:group name="group">
    <xs:sequence>
      <xs:element name="base" type="xs:string"/>
    </xs:sequence>
  </xs:group>
  <xs:attributeGroup name="attrs">
    <xs:attribute name="baseAttr" type="xs:string"/>
  </xs:attributeGroup>
  <xs:complexType name="Container">
    <xs:group ref="group"/>
    <xs:attributeGroup ref="attrs"/>
  </xs:complexType>
  <xs:element name="root" type="Container"/>
</xs:schema>
""",
        encoding="utf-8",
    )
    input_path = tmp_path / "redefine_self_reference.xsd"
    input_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="urn:redefine" xmlns="urn:redefine">
  <xs:redefine schemaLocation="base.xsd">
    <xs:group name="group">
      <xs:sequence>
        <xs:element name="before" type="xs:string"/>
        <xs:group ref="group"/>
        <xs:element name="after" type="xs:string"/>
      </xs:sequence>
    </xs:group>
    <xs:attributeGroup name="attrs">
      <xs:attributeGroup ref="attrs"/>
      <xs:attribute name="addedAttr" type="xs:string"/>
    </xs:attributeGroup>
    <xs:attributeGroup name="newAttrs">
      <xs:attribute name="newAttr" type="xs:string"/>
    </xs:attributeGroup>
    <xs:complexType name="Container">
      <xs:complexContent>
        <xs:extension base="Container">
          <xs:sequence>
            <xs:element name="tail" type="xs:string"/>
          </xs:sequence>
        </xs:extension>
      </xs:complexContent>
    </xs:complexType>
  </xs:redefine>
</xs:schema>
""",
        encoding="utf-8",
    )

    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
    )


def test_main_xmlschema_schema_composition(output_file: Path) -> None:
    """Generate models from include, redefine, override, and chameleon schemas."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "schema_composition.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="schema_composition.py",
    )


def test_main_xmlschema_xsd11_constructs(output_file: Path) -> None:
    """Generate models from XML Schema 1.1 open content and alternatives."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "xsd11_constructs.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="xsd11_constructs.py",
    )


def test_main_xmlschema_versioning_auto(output_file: Path) -> None:
    """Apply XSD 1.1 conditional inclusion when auto-detection sees versioning attributes."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "versioning.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="versioning.py",
    )


def test_main_xmlschema_versioning_xsd10(output_file: Path) -> None:
    """Apply XSD 1.0 conditional inclusion when requested through --schema-version."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "versioning.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        extra_args=["--schema-version", "1.0"],
        assert_func=assert_file_content,
        expected_file="versioning_xsd10.py",
    )


def test_main_xmlschema_versioning_auto_from_include(output_file: Path) -> None:
    """Detect XSD 1.1 versioning attributes from included schemas in auto mode."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "versioning_include.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="versioning_include.py",
    )


def test_main_xmlschema_versioning_include_xsd10(output_file: Path) -> None:
    """Keep included XSD versioning conditional on an explicit XSD 1.0 processor version."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "versioning_include.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        extra_args=["--schema-version", "1.0"],
        assert_func=assert_file_content,
        expected_file="versioning_include_xsd10.py",
    )


def test_main_xmlschema_default_open_content_applies_to_empty(output_file: Path) -> None:
    """Apply defaultOpenContent to empty complex content only when requested."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "default_open_content_applies_to_empty.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="default_open_content_applies_to_empty.py",
    )


def test_main_xmlschema_datatypes_and_mixed_content(output_file: Path) -> None:
    """Generate models from XSD built-in datatypes and complexContent mixed content."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "datatypes_and_mixed_content.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="datatypes_and_mixed_content.py",
    )


def test_main_xmlschema_builtin_datatypes_matrix(output_file: Path) -> None:
    """Generate models for the W3C XML Schema built-in datatype set."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "builtin_datatypes_matrix.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="builtin_datatypes_matrix.py",
    )


def test_main_xmlschema_datetime_classes_default(output_file: Path) -> None:
    """Use XML Schema datetime defaults when no datetime class option is set."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "datetime_classes.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="datetime_classes.py",
    )


def test_main_xmlschema_datetime_classes_naive(output_file: Path) -> None:
    """Respect an explicit NaiveDatetime class for XML Schema date-time types."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "datetime_classes.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="datetime_classes_naive.py",
        extra_args=["--output-datetime-class", "NaiveDatetime"],
    )


def test_main_xmlschema_datetime_classes_aware(output_file: Path) -> None:
    """Respect an explicit AwareDatetime class for XML Schema date-time types."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "datetime_classes.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="datetime_classes_aware.py",
        extra_args=["--output-datetime-class", "AwareDatetime"],
    )


def test_main_xmlschema_blocks_relative_schema_location_outside_base_path(
    capsys: pytest.CaptureFixture[str],
    output_file: Path,
) -> None:
    """Reject XML Schema includes that resolve outside the input base path."""
    project_dir = output_file.parent / "project"
    secret_dir = output_file.parent / "secret"
    project_dir.mkdir()
    secret_dir.mkdir()
    (secret_dir / "leak.xsd").write_text(
        """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:simpleType name="Leaked"><xs:restriction base="xs:string"/></xs:simpleType>
</xs:schema>
""",
        encoding="utf-8",
    )
    input_file = project_dir / "attack.xsd"
    input_file.write_text(
        """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:include schemaLocation="../secret/leak.xsd"/>
  <xs:element name="Root" type="Leaked"/>
</xs:schema>
""",
        encoding="utf-8",
    )

    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        input_file_type="xmlschema",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Blocked unsafe XML Schema schemaLocation",
        output_should_not_exist=True,
    )


def test_main_xmlschema_blocks_absolute_schema_location_outside_base_path(
    capsys: pytest.CaptureFixture[str],
    output_file: Path,
) -> None:
    """Reject absolute XML Schema includes outside the input base path."""
    project_dir = output_file.parent / "project"
    secret_dir = output_file.parent / "secret"
    project_dir.mkdir()
    secret_dir.mkdir()
    secret_schema = secret_dir / "leak.xsd"
    secret_schema.write_text(
        """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:simpleType name="Leaked"><xs:restriction base="xs:string"/></xs:simpleType>
</xs:schema>
""",
        encoding="utf-8",
    )
    input_file = project_dir / "attack.xsd"
    input_file.write_text(
        f"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:include schemaLocation="{secret_schema}"/>
  <xs:element name="Root" type="Leaked"/>
</xs:schema>
""",
        encoding="utf-8",
    )

    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        input_file_type="xmlschema",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Blocked unsafe XML Schema schemaLocation",
        output_should_not_exist=True,
    )


def test_main_xmlschema_parse_error(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Report invalid XML Schema syntax through the CLI."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "invalid_xml.xml",
        output_path=output_file,
        input_file_type="xmlschema",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Invalid XML Schema document",
        output_should_not_exist=True,
    )


def test_main_xmlschema_wrong_root_error(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Report non-schema XML roots through explicit XML Schema parsing."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "invalid_root.xml",
        output_path=output_file,
        input_file_type="xmlschema",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="XML Schema root element must be xs:schema",
        output_should_not_exist=True,
    )


def test_main_xmlschema_auto_broken_xml_error(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Exercise XML Schema auto-detection for malformed XML input."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "invalid_xml.xml",
        output_path=output_file,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Can't infer input file type",
        output_should_not_exist=True,
    )


def test_main_xmlschema_auto_wrong_root_error(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Exercise XML Schema auto-detection for non-schema XML input."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "invalid_root.xml",
        output_path=output_file,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Can't infer input file type",
        output_should_not_exist=True,
    )
