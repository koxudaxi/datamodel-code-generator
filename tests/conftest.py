from __future__ import annotations

import pytest
from inline_snapshot import register_format_alias

from datamodel_code_generator import MIN_VERSION


register_format_alias(".py", ".txt")
register_format_alias(".pyi", ".txt")


@pytest.fixture(autouse=True)
def _inline_snapshot_file_formats() -> None:
    register_format_alias(".py", ".txt")
    register_format_alias(".pyi", ".txt")


@pytest.fixture(scope="session")
def min_version() -> str:
    return f"3.{MIN_VERSION}"
