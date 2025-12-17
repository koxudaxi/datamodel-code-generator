"""Tests for GraphQL annotated types generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.main.conftest import GRAPHQL_DATA_PATH, run_main_and_assert
from tests.main.graphql.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


def test_annotated(output_file: Path) -> None:
    """Test GraphQL code generation with annotated types."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "annotated.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--use-annotated"],
    )


def test_annotated_use_standard_collections(output_file: Path) -> None:
    """Test GraphQL annotated types with standard collections."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "annotated.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--use-standard-collections",
        ],
    )


@pytest.mark.cli_doc(
    options=["--use-annotated", "--use-union-operator"],
    input_schema="graphql/annotated.graphql",
    cli_args=[
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--use-annotated",
        "--use-standard-collections",
        "--use-union-operator",
    ],
    golden_output="graphql/annotated_use_standard_collections_use_union_operator.py",
    related_options=["--use-standard-collections"],
)
def test_annotated_use_standard_collections_use_union_operator(output_file: Path) -> None:
    """Test GraphQL annotated types with standard collections and union operator."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "annotated.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--use-standard-collections",
            "--use-union-operator",
        ],
    )


@pytest.mark.cli_doc(
    options=["--use-annotated", "--use-union-operator"],
    input_schema="graphql/annotated.graphql",
    cli_args=["--output-model-type", "pydantic_v2.BaseModel", "--use-annotated", "--use-union-operator"],
    golden_output="graphql/annotated_use_union_operator.py",
)
def test_annotated_use_union_operator(output_file: Path) -> None:
    """Test GraphQL annotated types with union operator."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "annotated.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--use-union-operator",
        ],
    )


@pytest.mark.cli_doc(
    options=["--aliases", "--use-annotated"],
    input_schema="graphql/field-aliases.graphql",
    cli_args=[
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--use-annotated",
        "--aliases",
        "graphql/field-aliases.json",
    ],
    golden_output="graphql/annotated_field_aliases.py",
)
def test_annotated_field_aliases(output_file: Path) -> None:
    """Test GraphQL annotated types with field aliases."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "field-aliases.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--aliases",
            str(GRAPHQL_DATA_PATH / "field-aliases.json"),
        ],
    )
