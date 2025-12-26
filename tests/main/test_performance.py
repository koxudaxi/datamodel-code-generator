"""Performance tests for large schemas and complex code generation scenarios.

These tests are designed to measure code generation performance with:
- Large number of models (500+)
- Duplicate/similar names requiring disambiguation
- Complex reference chains and circular references
- Deeply nested structures
- Multiple file inputs
- Large OpenAPI specifications

Tests are marked with @pytest.mark.perf for exclusion from regular CI runs.
Core tests are also marked with @pytest.mark.benchmark for CodSpeed integration.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from datamodel_code_generator import DataModelType, InputFileType, generate

PERFORMANCE_DATA_PATH: Path = Path(__file__).parent.parent / "data" / "performance"


@pytest.mark.perf
def test_perf_large_models(tmp_path: Path) -> None:
    """Performance test: Generate 500 models from a single schema.

    This tests the parser's ability to handle a large number of model definitions
    and the code generator's performance with many models.
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "large_models.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated all 500 models
    assert content.count("class Model") >= 500


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_large_models_pydantic_v2(tmp_path: Path) -> None:
    """Performance test: Generate 500 Pydantic v2 models."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "large_models.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    content = output_file.read_text()
    assert content.count("class Model") >= 500


@pytest.mark.perf
def test_perf_large_models_dataclass(tmp_path: Path) -> None:
    """Performance test: Generate 500 dataclass models."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "large_models.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.DataclassesDataclass,
    )
    content = output_file.read_text()
    assert content.count("class Model") >= 500


@pytest.mark.perf
def test_perf_large_models_typed_dict(tmp_path: Path) -> None:
    """Performance test: Generate 500 TypedDict models."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "large_models.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.TypingTypedDict,
    )
    content = output_file.read_text()
    assert content.count("class Model") >= 500


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_duplicate_names(tmp_path: Path) -> None:
    """Performance test: Handle 300 models with duplicate/similar names.

    This tests the name disambiguation logic when many models have similar names
    requiring prefixes or suffixes to avoid collisions.
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "duplicate_names.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated Container models
    assert content.count("class Container") >= 100


@pytest.mark.perf
def test_perf_duplicate_names_multiple_files(tmp_path: Path) -> None:
    """Performance test: Handle duplicate names with multiple file output."""
    output_dir = tmp_path / "models"
    generate(
        input_=PERFORMANCE_DATA_PATH / "duplicate_names.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_dir,
    )
    # Check output directory was created
    assert output_dir.exists()


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_complex_refs(tmp_path: Path) -> None:
    """Performance test: Handle 200 models with complex reference chains.

    This tests the reference resolution logic with:
    - Circular references
    - Deep reference chains
    - Self-references
    - Cross-references between models
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "complex_refs.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated Node models
    assert content.count("class Node") >= 200


@pytest.mark.perf
def test_perf_complex_refs_collapse_root(tmp_path: Path) -> None:
    """Performance test: Complex refs with collapse-root-models enabled."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "complex_refs.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        collapse_root_models=True,
    )
    content = output_file.read_text()
    assert "class Node" in content


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_deep_nested(tmp_path: Path) -> None:
    """Performance test: Handle deeply nested structures (50 levels deep).

    This tests:
    - Deep nesting resolution
    - Wide models with many fields
    - Combined deep and wide structures
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "deep_nested.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated Level and WideModel classes
    assert content.count("class Level") >= 50
    assert content.count("class WideModel") >= 100


@pytest.mark.perf
def test_perf_deep_nested_use_annotated(tmp_path: Path) -> None:
    """Performance test: Deep nested with use-annotated and field-constraints enabled."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "deep_nested.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        use_annotated=True,
        field_constraints=True,
    )
    content = output_file.read_text()
    assert "class Level" in content


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_multiple_files_input(tmp_path: Path) -> None:
    """Performance test: Process 50 schema files (500 models total).

    This tests:
    - Directory input handling
    - Multiple file parsing
    - Cross-file model coordination
    """
    output_dir = tmp_path / "models"
    generate(
        input_=PERFORMANCE_DATA_PATH / "multiple_files",
        input_file_type=InputFileType.JsonSchema,
        output=output_dir,
    )
    # Verify output directory was created with models
    assert output_dir.exists()
    py_files = list(output_dir.glob("**/*.py"))
    assert len(py_files) >= 1
    # Count total Module models across all files
    total_models = 0
    for py_file in py_files:
        content = py_file.read_text()
        total_models += content.count("class Module")
    assert total_models >= 500


@pytest.mark.perf
def test_perf_multiple_files_to_multiple_outputs(tmp_path: Path) -> None:
    """Performance test: Multiple input files to multiple output files."""
    output_dir = tmp_path / "models"
    generate(
        input_=PERFORMANCE_DATA_PATH / "multiple_files",
        input_file_type=InputFileType.JsonSchema,
        output=output_dir,
    )
    # Check multiple output files were created
    assert output_dir.exists()
    py_files = list(output_dir.glob("**/*.py"))
    assert len(py_files) >= 1


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_openapi_large(tmp_path: Path) -> None:
    """Performance test: Large OpenAPI spec with 300 schemas and 900 endpoints.

    This tests:
    - OpenAPI parsing performance
    - Path/endpoint processing
    - Component schema handling
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "openapi_large.yaml",
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated Entity models
    assert content.count("class Entity") >= 300


@pytest.mark.perf
def test_perf_openapi_large_strict_types(tmp_path: Path) -> None:
    """Performance test: Large OpenAPI with strict types enabled."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "openapi_large.yaml",
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        strict_types=[
            "str",
            "int",
            "float",
            "bool",
        ],
    )
    content = output_file.read_text()
    assert "class Entity" in content


@pytest.mark.perf
def test_perf_openapi_large_field_constraints(tmp_path: Path) -> None:
    """Performance test: Large OpenAPI with field constraints enabled."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "openapi_large.yaml",
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        field_constraints=True,
    )
    content = output_file.read_text()
    assert "class Entity" in content


@pytest.mark.perf
def test_perf_combined_large_models_with_formatting(tmp_path: Path) -> None:
    """Performance test: Large models with all formatting options.

    This tests the full pipeline including:
    - Parsing
    - Code generation
    - Import sorting
    - Code formatting
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "large_models.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        use_standard_collections=True,
        use_union_operator=True,
        use_annotated=True,
        field_constraints=True,
    )
    content = output_file.read_text()
    assert content.count("class Model") >= 500


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_all_options_enabled(tmp_path: Path) -> None:
    """Performance test: Large schema with many options enabled.

    This stress tests the code generator with multiple features enabled simultaneously.
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "deep_nested.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
        use_standard_collections=True,
        use_union_operator=True,
        use_annotated=True,
        field_constraints=True,
        collapse_root_models=True,
        use_field_description=True,
        use_default_kwarg=True,
    )
    content = output_file.read_text()
    assert "class" in content


# Real-world style schemas based on popular APIs


@pytest.mark.perf
def test_perf_kubernetes_style(tmp_path: Path) -> None:
    """Performance test: Kubernetes-style schema with 300+ definitions.

    Tests patterns common in Kubernetes APIs:
    - Deep metadata/spec/status patterns
    - Many resource types with similar structures
    - CRD-like custom resources
    - Complex allOf compositions
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "kubernetes_style.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated core K8s types
    assert "ObjectMeta" in content
    assert "class" in content


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_kubernetes_style_pydantic_v2(tmp_path: Path) -> None:
    """Performance test: Kubernetes-style schema with Pydantic v2."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "kubernetes_style.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    content = output_file.read_text()
    assert "ObjectMeta" in content


@pytest.mark.perf
def test_perf_stripe_style(tmp_path: Path) -> None:
    """Performance test: Stripe-style schema with 100+ definitions.

    Tests patterns common in Stripe API:
    - Event/webhook patterns
    - Expandable references (oneOf string or object)
    - Many payment-related types
    - Nested billing details
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "stripe_style.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated core Stripe types
    assert "class" in content


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_stripe_style_pydantic_v2(tmp_path: Path) -> None:
    """Performance test: Stripe-style schema with Pydantic v2."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "stripe_style.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    content = output_file.read_text()
    assert "class" in content


@pytest.mark.perf
def test_perf_aws_style_openapi(tmp_path: Path) -> None:
    """Performance test: AWS-style OpenAPI with 350+ schemas.

    Tests patterns common in AWS APIs:
    - Many resource types across services
    - Request/Response patterns
    - ARN references
    - Paginated list operations
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "aws_style.yaml",
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated AWS resource types
    assert "class" in content


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_aws_style_openapi_pydantic_v2(tmp_path: Path) -> None:
    """Performance test: AWS-style OpenAPI with Pydantic v2."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "aws_style.yaml",
        input_file_type=InputFileType.OpenAPI,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    content = output_file.read_text()
    assert "class" in content


@pytest.mark.perf
def test_perf_graphql_style(tmp_path: Path) -> None:
    """Performance test: GraphQL-style schema with 150+ definitions.

    Tests patterns common in GraphQL APIs converted to JSON Schema:
    - Connection/Edge patterns for pagination
    - Node interface pattern
    - Input/Payload types for mutations
    - Union types (oneOf)
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "graphql_style.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    # Verify we generated GraphQL patterns
    assert "PageInfo" in content
    assert "class" in content


@pytest.mark.perf
@pytest.mark.benchmark
def test_perf_graphql_style_pydantic_v2(tmp_path: Path) -> None:
    """Performance test: GraphQL-style schema with Pydantic v2."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "graphql_style.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    content = output_file.read_text()
    assert "PageInfo" in content


@pytest.mark.perf
def test_perf_graphql_style_typed_dict(tmp_path: Path) -> None:
    """Performance test: GraphQL-style schema with TypedDict."""
    output_file = tmp_path / "output.py"
    generate(
        input_=PERFORMANCE_DATA_PATH / "graphql_style.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.TypingTypedDict,
    )
    content = output_file.read_text()
    assert "PageInfo" in content


# =============================================================================
# Dynamically generated extreme-scale tests
# These tests generate schemas at runtime to avoid bloating the repository
# =============================================================================


@pytest.fixture
def extreme_large_schema(tmp_path: Path) -> Path:
    """Generate an extremely large schema with 2000 models."""
    import json

    schema: dict = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "ExtremeLargeSchema",
        "definitions": {},
    }
    for i in range(2000):
        schema["definitions"][f"Model{i:04d}"] = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "value": {"type": "number"},
                "active": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "metadata": {"type": "object", "additionalProperties": {"type": "string"}},
                "ref_prev": {"$ref": f"#/definitions/Model{max(0, i - 1):04d}"},
            },
            "required": ["id", "name"],
        }
    schema["$ref"] = "#/definitions/Model1999"

    schema_file = tmp_path / "extreme_large.json"
    schema_file.write_text(json.dumps(schema))
    return schema_file


@pytest.fixture
def massive_files_input(tmp_path: Path) -> Path:
    """Generate 200 separate schema files with cross-references."""
    import json

    input_dir = tmp_path / "massive_input"
    input_dir.mkdir()

    for i in range(200):
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": f"Schema{i:03d}",
            "definitions": {},
        }
        for j in range(20):
            model_name = f"Module{i:03d}Model{j:02d}"
            schema["definitions"][model_name] = {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "data": {"type": "object", "additionalProperties": True},
                },
                "required": ["id"],
            }
        schema["$ref"] = f"#/definitions/Module{i:03d}Model00"
        schema_file = input_dir / f"schema_{i:03d}.json"
        schema_file.write_text(json.dumps(schema))

    return input_dir


@pytest.fixture
def extreme_duplicate_names_schema(tmp_path: Path) -> Path:
    """Generate schema with 1000 models having highly similar/duplicate names."""
    import json

    schema: dict = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "ExtremeDuplicateNames",
        "definitions": {},
    }

    prefixes = ["User", "Account", "Order", "Product", "Item", "Entity", "Record", "Data", "Info", "Detail"]
    suffixes = ["Request", "Response", "Input", "Output", "Model", "Schema", "Type", "DTO", "Payload", "Result"]

    idx = 0
    for prefix in prefixes:
        for suffix in suffixes:
            for variant in range(10):
                name = f"{prefix}{suffix}"
                if variant > 0:
                    name = f"{name}{variant}"
                schema["definitions"][f"def_{idx}_{name}"] = {
                    "title": name,
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "value": {"type": "string"},
                        "nested": {
                            "type": "object",
                            "properties": {
                                "inner_id": {"type": "integer"},
                            },
                        },
                    },
                }
                idx += 1

    schema["$ref"] = "#/definitions/def_0_UserRequest"

    schema_file = tmp_path / "extreme_duplicates.json"
    schema_file.write_text(json.dumps(schema))
    return schema_file


@pytest.mark.perf
def test_perf_extreme_large_schema(tmp_path: Path, extreme_large_schema: Path) -> None:
    """Performance test: Extremely large schema with 2000 models.

    Tests the generator's ability to handle very large schemas that would be
    impractical to store in the repository.
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=extreme_large_schema,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    assert content.count("class Model") >= 2000


@pytest.mark.perf
def test_perf_extreme_large_schema_pydantic_v2(tmp_path: Path, extreme_large_schema: Path) -> None:
    """Performance test: Extremely large schema with Pydantic v2."""
    output_file = tmp_path / "output.py"
    generate(
        input_=extreme_large_schema,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    content = output_file.read_text()
    assert content.count("class Model") >= 2000


@pytest.mark.perf
def test_perf_massive_files_input(tmp_path: Path, massive_files_input: Path) -> None:
    """Performance test: Process 200 separate schema files (4000 models total).

    Tests directory input handling with a very large number of files.
    """
    output_dir = tmp_path / "output"
    generate(
        input_=massive_files_input,
        input_file_type=InputFileType.JsonSchema,
        output=output_dir,
    )
    assert output_dir.exists()
    py_files = list(output_dir.glob("**/*.py"))
    assert len(py_files) >= 1


@pytest.mark.perf
def test_perf_massive_files_single_output(tmp_path: Path, massive_files_input: Path) -> None:
    """Performance test: Merge 200 schema files into output directory."""
    output_dir = tmp_path / "merged"
    generate(
        input_=massive_files_input,
        input_file_type=InputFileType.JsonSchema,
        output=output_dir,
    )
    assert output_dir.exists()
    py_files = list(output_dir.glob("**/*.py"))
    assert len(py_files) >= 1


@pytest.mark.perf
def test_perf_extreme_duplicate_names(tmp_path: Path, extreme_duplicate_names_schema: Path) -> None:
    """Performance test: Handle 1000 models with highly similar names.

    Tests the name disambiguation logic under extreme conditions.
    """
    output_file = tmp_path / "output.py"
    generate(
        input_=extreme_duplicate_names_schema,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
    )
    content = output_file.read_text()
    assert content.count("class ") >= 1000


@pytest.mark.perf
def test_perf_extreme_duplicate_names_pydantic_v2(tmp_path: Path, extreme_duplicate_names_schema: Path) -> None:
    """Performance test: Extreme duplicate names with Pydantic v2."""
    output_file = tmp_path / "output.py"
    generate(
        input_=extreme_duplicate_names_schema,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )
    content = output_file.read_text()
    assert content.count("class ") >= 1000
