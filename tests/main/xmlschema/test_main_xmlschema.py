"""Tests for XML Schema code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datamodel_code_generator.__main__ import Exit
from tests.main.conftest import XML_SCHEMA_DATA_PATH, run_main_and_assert
from tests.main.xmlschema.conftest import assert_file_content, assert_xmlschema_snippets

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _identity(content: str) -> str:
    return content


def test_main_xmlschema_purchase_order(output_file: Path) -> None:
    """Generate models from an XML Schema document."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "purchase_order.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="purchase_order.py",
    )


def test_main_xmlschema_infer_input_file_type(output_file: Path) -> None:
    """Infer XML Schema input and generate a model."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "single_root_item.xsd",
        output_path=output_file,
        assert_func=assert_xmlschema_snippets,
        expected_file="single_root_item.py",
    )


def test_main_xmlschema_coverage_constructs(output_file: Path) -> None:
    """Generate models for supported XML Schema constructs."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "coverage.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="coverage.py",
        transform=_identity,
    )


def test_main_xmlschema_edge_cases(output_file: Path) -> None:
    """Generate models for XML Schema edge cases."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "edge_cases.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="edge_cases.py",
    )


def test_main_xmlschema_single_root_same_name(output_file: Path) -> None:
    """Inline a single root type when no other definition references it."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "single_root_item.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="single_root_item.py",
    )


def test_main_xmlschema_inline_root(output_file: Path) -> None:
    """Generate a titled model for a single inline root element."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "inline_root.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="inline_root.py",
    )


def test_main_xmlschema_recursive_root(output_file: Path) -> None:
    """Keep recursive root definitions addressable."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "recursive_node.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="recursive_node.py",
    )


def test_main_xmlschema_import_resolves_by_namespace(output_file: Path) -> None:
    """Resolve imported components by namespace without selecting imported roots."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "import_namespace.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="import_namespace.py",
    )


def test_main_xmlschema_imported_namespace_name_collisions(output_file: Path) -> None:
    """Keep imported definitions distinct when local names collide."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "namespace_collisions.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="namespace_collisions.py",
    )


def test_main_xmlschema_no_namespace_name_collision(output_file: Path) -> None:
    """Name no-namespace definitions distinctly when imported names collide."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "no_namespace_collision.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="no_namespace_collision.py",
    )


def test_main_xmlschema_namespace_fallback(output_file: Path) -> None:
    """Resolve unprefixed target-namespace names and referenced definitions."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "namespace_fallback.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="namespace_fallback.py",
    )


def test_main_xmlschema_advanced_constructs(output_file: Path) -> None:
    """Generate models for abstract substitution groups and mixed content."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "advanced_constructs.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="advanced_constructs.py",
    )


def test_main_xmlschema_model_groups_and_wildcards(output_file: Path) -> None:
    """Generate models for repeating model groups, defaults, fixed values, and wildcards."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "model_groups_and_wildcards.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="model_groups_and_wildcards.py",
    )


def test_main_xmlschema_schema_composition(output_file: Path) -> None:
    """Generate models from include, redefine, override, and chameleon schemas."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "schema_composition.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_xmlschema_snippets,
        expected_file="schema_composition.py",
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
        file_should_not_exist=output_file,
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
        file_should_not_exist=output_file,
    )


def test_main_xmlschema_auto_broken_xml_error(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Exercise XML Schema auto-detection for malformed XML input."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "invalid_xml.xml",
        output_path=output_file,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Can't infer input file type",
        file_should_not_exist=output_file,
    )


def test_main_xmlschema_auto_wrong_root_error(capsys: pytest.CaptureFixture[str], output_file: Path) -> None:
    """Exercise XML Schema auto-detection for non-schema XML input."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "invalid_root.xml",
        output_path=output_file,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Can't infer input file type",
        file_should_not_exist=output_file,
    )
