"""Tests for XML Schema code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.main.conftest import XML_SCHEMA_DATA_PATH, run_main_and_assert
from tests.main.xmlschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


def test_main_xmlschema_purchase_order(output_file: Path) -> None:
    """Generate models from an XML Schema document."""
    run_main_and_assert(
        input_path=XML_SCHEMA_DATA_PATH / "purchase_order.xsd",
        output_path=output_file,
        input_file_type="xmlschema",
        assert_func=assert_file_content,
        expected_file="purchase_order.py",
    )
