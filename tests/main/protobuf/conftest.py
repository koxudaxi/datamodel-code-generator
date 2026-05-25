"""Shared fixtures for Protocol Buffers tests."""

from __future__ import annotations

from tests.conftest import create_assert_file_content
from tests.main.conftest import EXPECTED_PROTOBUF_PATH

assert_file_content = create_assert_file_content(EXPECTED_PROTOBUF_PATH)
