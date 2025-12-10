"""Tests for GraphQL schema code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import black
import pytest

from tests.main.conftest import GRAPHQL_DATA_PATH, run_main_and_assert
from tests.main.graphql.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("output_model", "expected_output"),
    [
        (
            "pydantic.BaseModel",
            "simple_star_wars.py",
        ),
        (
            "dataclasses.dataclass",
            "simple_star_wars_dataclass.py",
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_simple_star_wars(output_model: str, expected_output: str, output_file: Path) -> None:
    """Test GraphQL code generation for simple Star Wars schema."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model", output_model],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_different_types_of_fields(output_file: Path) -> None:
    """Test GraphQL code generation with different field types."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "different-types-of-fields.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="different_types_of_fields.py",
    )


def test_main_use_default_kwarg(output_file: Path) -> None:
    """Test GraphQL code generation with use-default-kwarg flag."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "annotated.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="annotated_use_default_kwarg.py",
        extra_args=["--use-default-kwarg"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_custom_scalar_types(output_file: Path) -> None:
    """Test GraphQL code generation with custom scalar types."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "custom-scalar-types.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="custom_scalar_types.py",
        extra_args=["--extra-template-data", str(GRAPHQL_DATA_PATH / "custom-scalar-types.json")],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_field_aliases(output_file: Path) -> None:
    """Test GraphQL code generation with field aliases."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "field-aliases.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="field_aliases.py",
        extra_args=["--aliases", str(GRAPHQL_DATA_PATH / "field-aliases.json")],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_enum_casing(output_file: Path) -> None:
    """Test GraphQL code generation with enums."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enum-casing.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enum_casing.py",
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_enums(output_file: Path) -> None:
    """Test GraphQL code generation with enums."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enums.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enums.py",
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_specialized_enums(output_file: Path) -> None:
    """Test GraphQL code generation with specialized enums for Python 3.11+."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enums.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enums_specialized.py",
        extra_args=["--target-python-version", "3.11"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_specialized_enums_disabled(output_file: Path) -> None:
    """Test GraphQL code generation with specialized enums disabled."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enums.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enums_no_specialized.py",
        extra_args=["--target-python-version", "3.11", "--no-use-specialized-enum"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_enums_subclass(output_file: Path) -> None:
    """Test GraphQL code generation with enum subclasses."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enums.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enums_using_subclass.py",
        extra_args=["--use-subclass-enum"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_union(output_file: Path) -> None:
    """Test GraphQL code generation with union types."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "union.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="union.py",
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_additional_imports(output_file: Path) -> None:
    """Test GraphQL code generation with additional imports."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "additional-imports.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="additional_imports.py",
        extra_args=[
            "--extra-template-data",
            str(GRAPHQL_DATA_PATH / "additional-imports-types.json"),
            "--additional-imports",
            "datetime.datetime,datetime.date,mymodule.myclass.MyCustomPythonClass",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_custom_formatters(output_file: Path) -> None:
    """Test GraphQL code generation with custom formatters."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "custom-scalar-types.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="custom_formatters.py",
        extra_args=["--custom-formatters", "tests.data.python.custom_formatters.add_comment"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_use_standard_collections(output_file: Path) -> None:
    """Test GraphQL code generation with standard collections."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "use-standard-collections.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="use_standard_collections.py",
        extra_args=["--use-standard-collections"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_use_union_operator(output_file: Path) -> None:
    """Test GraphQL code generation with union operator syntax."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "use-union-operator.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="use_union_operator.py",
        extra_args=["--use-union-operator"],
    )


def test_main_graphql_extra_fields_allow(output_file: Path) -> None:
    """Test GraphQL code generation with extra fields allowed."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="simple_star_wars_extra_fields_allow.py",
        extra_args=["--extra-fields", "allow"],
    )


def test_main_graphql_type_alias(output_file: Path) -> None:
    """Test that TypeAliasType is generated for GraphQL schemas for Python 3.9-3.11."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "type_alias.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="type_alias.py",
        extra_args=["--use-type-alias"],
    )


@pytest.mark.skipif(
    int(black.__version__.split(".")[0]) < 23,
    reason="Installed black doesn't support the new 'type' statement",
)
def test_main_graphql_type_alias_py312(output_file: Path) -> None:
    """Test that type statement syntax is generated for GraphQL schemas with Python 3.12+ and Pydantic v2."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "type_alias.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="type_alias_py312.py",
        extra_args=[
            "--use-type-alias",
            "--target-python-version",
            "3.12",
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_dataclass_arguments(output_file: Path) -> None:
    """Test GraphQL code generation with custom dataclass arguments."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="simple_star_wars_dataclass_arguments.py",
        extra_args=[
            "--output-model",
            "dataclasses.dataclass",
            "--dataclass-arguments",
            '{"slots": true, "order": true}',
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_dataclass_arguments_with_pydantic(output_file: Path) -> None:
    """Test GraphQL code generation with dataclass arguments passed but using Pydantic model.

    This verifies that dataclass_arguments is properly ignored for non-dataclass models.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="simple_star_wars.py",
        extra_args=[
            "--output-model",
            "pydantic.BaseModel",
            "--dataclass-arguments",
            '{"slots": true, "order": true}',
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_dataclass_frozen_keyword_only(output_file: Path) -> None:
    """Test GraphQL code generation with frozen and keyword-only dataclass.

    This tests the 'if existing:' False branch in _create_data_model when
    no --dataclass-arguments is provided but --frozen and --keyword-only are set.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="simple_star_wars_dataclass_frozen_kw_only.py",
        extra_args=[
            "--output-model",
            "dataclasses.dataclass",
            "--frozen",
            "--keyword-only",
            "--target-python-version",
            "3.10",
        ],
    )
