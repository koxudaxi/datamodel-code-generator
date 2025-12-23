"""Tests for GraphQL schema parser."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from datamodel_code_generator.model.dataclass import DataClass
from datamodel_code_generator.parser.graphql import GraphQLParser
from datamodel_code_generator.reference import Reference
from tests.conftest import create_assert_file_content
from tests.main.conftest import GRAPHQL_DATA_PATH, run_main_and_assert
from tests.main.test_main_general import DATA_PATH

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED_GRAPHQL_PATH: Path = DATA_PATH / "expected" / "parser" / "graphql"

assert_file_content = create_assert_file_content(EXPECTED_GRAPHQL_PATH)


def test_graphql_field_enum(output_file: Path) -> None:
    """Test parsing GraphQL field with enum default value."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "field-default-enum.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="field-default-enum.py",
        extra_args=["--set-default-enum-member"],
    )


def test_graphql_union_aliased_bug(output_file: Path) -> None:
    """Test parsing GraphQL union with aliased types."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "union-aliased-bug.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="union-aliased-bug.py",
    )


def test_graphql_union_commented(output_file: Path) -> None:
    """Test parsing GraphQL union with comments."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "union-commented.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="union-commented.py",
    )


@pytest.mark.parametrize(
    ("frozen_dataclasses", "keyword_only", "parser_dataclass_args", "kwargs_dataclass_args", "expected"),
    [
        (False, False, None, None, {}),
        (True, False, None, None, {"frozen": True}),
        (False, True, None, None, {"kw_only": True}),
        (True, True, None, None, {"frozen": True, "kw_only": True}),
        (False, False, {"slots": True}, None, {"slots": True}),
        (True, True, {"slots": True}, None, {"slots": True}),
        (True, True, {"slots": True}, {"order": True}, {"order": True}),
    ],
)
def test_create_data_model_dataclass_arguments(
    frozen_dataclasses: bool,
    keyword_only: bool,
    parser_dataclass_args: dict | None,
    kwargs_dataclass_args: dict | None,
    expected: dict,
) -> None:
    """Test _create_data_model handles dataclass_arguments correctly."""
    parser = GraphQLParser(
        source="type Query { id: ID }",
        data_model_type=DataClass,
        frozen_dataclasses=frozen_dataclasses,
        keyword_only=keyword_only,
    )
    parser.dataclass_arguments = parser_dataclass_args

    reference = Reference(path="test", original_name="Test", name="Test")
    kwargs: dict[str, Any] = {"reference": reference, "fields": []}
    if kwargs_dataclass_args is not None:
        kwargs["dataclass_arguments"] = kwargs_dataclass_args
    result = parser._create_data_model(**kwargs)
    assert isinstance(result, DataClass)
    assert result.dataclass_arguments == expected


def test_create_data_model_class_decorators() -> None:
    """Test _create_data_model applies class_decorators correctly."""
    parser = GraphQLParser(
        source="type Query { id: ID }",
        data_model_type=DataClass,
        class_decorators=["@dataclass_json"],
    )

    reference = Reference(path="test", original_name="Test", name="Test")
    result = parser._create_data_model(reference=reference, fields=[])
    assert isinstance(result, DataClass)
    assert result.decorators == ["@dataclass_json"]
