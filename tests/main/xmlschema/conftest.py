"""Shared fixtures for XML Schema tests."""

from __future__ import annotations

from tests.conftest import create_assert_file_content
from tests.main.conftest import EXPECTED_XML_SCHEMA_PATH

assert_file_content = create_assert_file_content(EXPECTED_XML_SCHEMA_PATH)
