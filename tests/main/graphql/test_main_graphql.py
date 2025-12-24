"""Tests for GraphQL schema code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import black
import pytest

from tests.main.conftest import GRAPHQL_DATA_PATH, LEGACY_BLACK_SKIP, run_main_and_assert
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
@pytest.mark.cli_doc(
    options=["--output-model-type"],
    input_schema="graphql/simple-star-wars.graphql",
    cli_args=["--output-model-type", "pydantic.BaseModel"],
    model_outputs={
        "pydantic_v1": "graphql/simple_star_wars.py",
        "dataclass": "graphql/simple_star_wars_dataclass.py",
    },
)
@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_simple_star_wars(output_model: str, expected_output: str, output_file: Path) -> None:
    """Generate models from GraphQL with different output model types.

    This example demonstrates using `--output-model-type` with GraphQL schemas
    to generate either Pydantic models or dataclasses.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file=expected_output,
        extra_args=["--output-model-type", output_model],
    )


@LEGACY_BLACK_SKIP
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


@pytest.mark.cli_doc(
    options=["--use-default-kwarg"],
    input_schema="graphql/annotated.graphql",
    cli_args=["--use-default-kwarg"],
    golden_output="graphql/annotated_use_default_kwarg.py",
)
def test_main_use_default_kwarg(output_file: Path) -> None:
    """Use default= keyword argument instead of positional argument for fields with defaults.

    The `--use-default-kwarg` flag generates Field() declarations using `default=`
    as a keyword argument instead of a positional argument for fields that have
    default values.
    """
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
@pytest.mark.cli_doc(
    options=["--aliases"],
    input_schema="graphql/field-aliases.graphql",
    cli_args=["--aliases", "graphql/field-aliases.json"],
    golden_output="graphql/field_aliases.py",
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
def test_main_graphql_casing(output_file: Path) -> None:
    """Test GraphQL code generation with casing transformations."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "casing.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="casing.py",
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


@pytest.mark.cli_doc(
    options=["--enum-field-as-literal"],
    input_schema="graphql/enums.graphql",
    cli_args=["--enum-field-as-literal", "all"],
    golden_output="graphql/enum_literals_all.py",
    comparison_output="graphql/enums.py",
)
def test_main_graphql_enums_as_literals_all(output_file: Path) -> None:
    """Convert all enum fields to Literal types instead of Enum classes.

    The `--enum-field-as-literal all` flag converts all enum types to Literal
    type annotations. This is useful when you want string literal types instead
    of Enum classes for all enumerations.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enums.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enum_literals_all.py",
        extra_args=["--enum-field-as-literal", "all"],
    )


@pytest.mark.cli_doc(
    options=["--enum-field-as-literal"],
    input_schema="graphql/enums.graphql",
    cli_args=["--enum-field-as-literal", "one"],
    golden_output="graphql/enum_literals_one.py",
)
def test_main_graphql_enums_as_literals_one(output_file: Path) -> None:
    """Convert single-member enums to Literal types.

    The `--enum-field-as-literal one` flag only converts enums with a single
    member to Literal types, keeping multi-member enums as Enum classes.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enums.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enum_literals_one.py",
        extra_args=["--enum-field-as-literal", "one"],
    )


def test_main_graphql_enums_to_typed_dict(output_file: Path) -> None:
    """Test GraphQL code generation paired with typing.TypedDict output which forces enums as literals."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enums.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enums_typed_dict.py",
        extra_args=["--output-model-type", "typing.TypedDict"],
    )


@pytest.mark.cli_doc(
    options=["--ignore-enum-constraints"],
    input_schema="graphql/enums.graphql",
    cli_args=["--ignore-enum-constraints"],
    golden_output="graphql/enums_ignore_enum_constraints.py",
    comparison_output="graphql/enums.py",
)
def test_main_graphql_enums_ignore_enum_constraints(output_file: Path) -> None:
    """Ignore enum constraints and use base string type instead of Enum classes.

    The `--ignore-enum-constraints` flag ignores enum constraints and uses
    the base type (str) instead of generating Enum classes. This is useful
    when you need flexibility in the values a field can accept beyond the
    defined enum members.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "enums.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="enums_ignore_enum_constraints.py",
        extra_args=["--ignore-enum-constraints"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--no-use-specialized-enum"],
    input_schema="graphql/enums.graphql",
    cli_args=["--target-python-version", "3.11", "--no-use-specialized-enum"],
    golden_output="graphql/enums_no_specialized.py",
    related_options=["--use-specialized-enum", "--target-python-version"],
)
def test_main_graphql_specialized_enums_disabled(output_file: Path) -> None:
    """Disable specialized Enum classes for Python 3.11+ code generation.

    The `--no-use-specialized-enum` flag prevents the generator from using
    specialized Enum classes (StrEnum, IntEnum) when generating code for
    Python 3.11+, falling back to standard Enum classes instead.
    """
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
@pytest.mark.cli_doc(
    options=["--use-subclass-enum"],
    input_schema="graphql/enums.graphql",
    cli_args=["--use-subclass-enum"],
    golden_output="graphql/enums_using_subclass.py",
)
def test_main_graphql_enums_subclass(output_file: Path) -> None:
    """Generate typed Enum subclasses for enums with specific field types.

    The `--use-subclass-enum` flag generates Enum classes as subclasses of the
    appropriate field type (int, float, bytes, str) when an enum has a specific
    type, providing better type safety and IDE support.
    """
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
@pytest.mark.cli_doc(
    options=["--additional-imports"],
    input_schema="graphql/additional-imports.graphql",
    cli_args=["--additional-imports", "datetime.datetime,datetime.date,mymodule.myclass.MyCustomPythonClass"],
    golden_output="graphql/additional_imports.py",
)
def test_main_graphql_additional_imports(output_file: Path) -> None:
    """Add custom imports to generated output files.

    The `--additional-imports` flag allows you to specify custom imports as a
    comma-delimited list that will be added to the generated output file. This
    is useful when using custom types defined in external modules (e.g.,
    "datetime.datetime,datetime.date,mymodule.myclass.MyCustomPythonClass").
    """
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
def test_main_graphql_additional_imports_in_extra_template_data(output_file: Path) -> None:
    """Test additional_imports specified in extra-template-data JSON file (string format)."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "additional-imports.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="additional_imports.py",
        extra_args=[
            "--extra-template-data",
            str(GRAPHQL_DATA_PATH / "additional-imports-in-extra-template-data.json"),
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_additional_imports_in_extra_template_data_list_format(output_file: Path) -> None:
    """Test additional_imports specified in extra-template-data JSON file (list format)."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "additional-imports.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="additional_imports.py",
        extra_args=[
            "--extra-template-data",
            str(GRAPHQL_DATA_PATH / "additional-imports-list-format.json"),
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_additional_imports_merged(output_file: Path) -> None:
    """Test merging additional_imports from CLI and extra-template-data JSON."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "additional-imports.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="additional_imports.py",
        extra_args=[
            "--extra-template-data",
            str(GRAPHQL_DATA_PATH / "additional-imports-partial.json"),
            "--additional-imports",
            "datetime.date,mymodule.myclass.MyCustomPythonClass",
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--custom-formatters"],
    input_schema="graphql/custom-scalar-types.graphql",
    cli_args=["--custom-formatters", "tests.data.python.custom_formatters.add_comment"],
    golden_output="graphql/custom_formatters.py",
)
def test_main_graphql_custom_formatters(output_file: Path) -> None:
    """Apply custom Python code formatters to generated output.

    The `--custom-formatters` flag allows you to specify custom Python functions
    that will be applied to format the generated code. The formatter is specified
    as a module path (e.g., "mymodule.formatter_function"). This is useful for
    adding custom comments, modifying code structure, or applying project-specific
    formatting rules beyond what black/isort provide.
    """
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


@pytest.mark.cli_doc(
    options=["--extra-fields"],
    input_schema="graphql/simple-star-wars.graphql",
    cli_args=["--extra-fields", "allow"],
    golden_output="graphql/simple_star_wars_extra_fields_allow.py",
)
def test_main_graphql_extra_fields_allow(output_file: Path) -> None:
    """Configure how generated models handle extra fields not defined in schema.

    The `--extra-fields` flag sets the generated models to allow, forbid, or
    ignore extra fields. With `--extra-fields allow`, models will accept and
    store fields not defined in the schema. Options: allow, ignore, forbid.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="simple_star_wars_extra_fields_allow.py",
        extra_args=["--extra-fields", "allow"],
    )


@pytest.mark.cli_doc(
    options=["--use-type-alias"],
    input_schema="graphql/type_alias.graphql",
    cli_args=["--use-type-alias"],
    golden_output="graphql/type_alias.py",
    related_options=["--target-python-version"],
)
def test_main_graphql_type_alias(output_file: Path) -> None:
    """Use TypeAlias instead of root models for type definitions (experimental).

    The `--use-type-alias` flag generates TypeAlias declarations instead of
    root model classes for certain type definitions. For Python 3.10-3.11, it
    generates TypeAliasType, and for Python 3.12+, it uses the 'type' statement
    syntax. This feature is experimental.
    """
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
@pytest.mark.cli_doc(
    options=["--dataclass-arguments"],
    input_schema="graphql/simple-star-wars.graphql",
    cli_args=[
        "--output-model-type",
        "dataclasses.dataclass",
        "--dataclass-arguments",
        '{"slots": true, "order": true}',
    ],
    golden_output="graphql/simple_star_wars_dataclass_arguments.py",
    related_options=["--frozen-dataclasses", "--keyword-only"],
)
def test_main_graphql_dataclass_arguments(output_file: Path) -> None:
    """Customize dataclass decorator arguments via JSON dictionary.

    The `--dataclass-arguments` flag accepts custom dataclass arguments as a JSON
    dictionary (e.g., '{"frozen": true, "kw_only": true, "slots": true, "order": true}').
    This overrides individual flags like --frozen-dataclasses and provides fine-grained
    control over dataclass generation.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="simple_star_wars_dataclass_arguments.py",
        extra_args=[
            "--output-model-type",
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
            "--output-model-type",
            "pydantic.BaseModel",
            "--dataclass-arguments",
            '{"slots": true, "order": true}',
        ],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@pytest.mark.cli_doc(
    options=["--keyword-only"],
    input_schema="graphql/simple-star-wars.graphql",
    cli_args=[
        "--output-model-type",
        "dataclasses.dataclass",
        "--frozen-dataclasses",
        "--keyword-only",
        "--target-python-version",
        "3.10",
    ],
    golden_output="graphql/simple_star_wars_dataclass_frozen_kw_only.py",
    related_options=["--frozen-dataclasses", "--target-python-version", "--output-model-type"],
)
def test_main_graphql_dataclass_frozen_keyword_only(output_file: Path) -> None:
    """Generate dataclasses with keyword-only fields (Python 3.10+).

    The `--keyword-only` flag generates dataclasses where all fields must be
    specified as keyword arguments (kw_only=True). This is only available for
    Python 3.10+. When combined with `--frozen-dataclasses`, it creates immutable
    dataclasses with keyword-only arguments, improving code clarity and preventing
    positional argument errors.
    """
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="simple_star_wars_dataclass_frozen_kw_only.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--frozen-dataclasses",
            "--keyword-only",
            "--target-python-version",
            "3.10",
        ],
    )


def test_main_graphql_union_snake_case_field(output_file: Path) -> None:
    """Test that union type references are not converted to snake_case."""
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "union.graphql",
        output_path=output_file,
        input_file_type="graphql",
        assert_func=assert_file_content,
        expected_file="union_snake_case_field.py",
        extra_args=["--snake-case-field", "--output-model-type", "pydantic_v2.BaseModel"],
    )
