"""Tests for GraphQL schema parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datamodel_code_generator.__main__ import Exit
from tests.conftest import create_assert_file_content
from tests.main.conftest import GRAPHQL_DATA_PATH, run_main
from tests.main.test_main_general import DATA_PATH

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED_GRAPHQL_PATH: Path = DATA_PATH / "expected" / "parser" / "graphql"

assert_file_content = create_assert_file_content(EXPECTED_GRAPHQL_PATH)


def test_graphql_field_enum(tmp_path: Path) -> None:
    """Test parsing GraphQL field with enum default value."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        GRAPHQL_DATA_PATH / "field-default-enum.graphql",
        output_file,
        "graphql",
        extra_args=["--set-default-enum-member"],
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, "field-default-enum.py")


def test_graphql_union_aliased_bug(tmp_path: Path) -> None:
    """Test parsing GraphQL union with aliased types."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        GRAPHQL_DATA_PATH / "union-aliased-bug.graphql",
        output_file,
        "graphql",
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, "union-aliased-bug.py")


def test_graphql_union_commented(tmp_path: Path) -> None:
    """Test parsing GraphQL union with comments."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        GRAPHQL_DATA_PATH / "union-commented.graphql",
        output_file,
        "graphql",
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, "union-commented.py")
