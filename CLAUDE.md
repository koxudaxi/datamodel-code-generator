# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

datamodel-code-generator automatically generates Python data models (Pydantic v1/v2, dataclasses, TypedDict, msgspec) from various schema formats including OpenAPI 3.0, JSON Schema, GraphQL, and raw JSON/YAML data.

## Common Development Commands

### Running Tests
```bash
# Run all tests with coverage
pytest --cov=datamodel_code_generator --cov-report=term-missing

# Run tests for specific Python version
tox -e 3.12

# Run a single test file
pytest tests/model/test_pydantic.py

# Run a specific test
pytest tests/model/test_pydantic.py::test_specific_function

# Run tests with verbose output
pytest -vv

# Run tests matching a pattern
pytest -k "test_openapi"
```

### Code Quality
```bash
# Run linting and formatting fixes
tox -e fix

# Run type checking
tox -e type

# Format code with ruff
ruff format .

# Check code with ruff
ruff check .

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Building and Documentation
```bash
# Generate documentation
tox -e docs

# Build package
python -m build

# Update command help in README
python scripts/update_command_help_on_markdown.py
```

### Development Setup
```bash
# Install in development mode with all extras
pip install -e ".[all,dev]"

# Install pre-commit hooks
pre-commit install
```

## Code Architecture

### Core Components

**Parser System** (`src/datamodel_code_generator/parser/`):
- `base.py`: Abstract parser with schema resolution, reference handling, and model generation logic
- Input-specific parsers inherit from `Parser` base class
- Parsers convert input schemas to internal `DataModel` representations

**Model Generation** (`src/datamodel_code_generator/model/`):
- Each output type has its own module/package (pydantic/, pydantic_v2/, dataclass.py, etc.)
- Models inherit from `DataModel` base class
- Template-based generation using Jinja2 for custom outputs

**Type System** (`src/datamodel_code_generator/types.py`):
- `DataType` hierarchy for representing schema types
- Handles type constraints, validations, and Python type mappings

**Reference Resolution**:
- Complex $ref resolution supporting local and remote schemas
- Caching and circular reference detection
- Model reuse optimization

### Key Design Patterns

1. **Parser Plugin Architecture**: New input formats can be added by creating parser subclasses
2. **Template-Based Generation**: Jinja2 templates allow custom model outputs
3. **Visitor Pattern**: Used for traversing and transforming schema trees
4. **Factory Pattern**: Model and parser creation based on configuration

### Important Implementation Details

- **Import Management**: The `imports.py` module tracks and optimizes imports, handling relative/absolute imports and version-specific features
- **Formatting Pipeline**: Code passes through configurable formatters (black, isort, ruff) post-generation
- **Field Constraints**: Complex constraint handling varies by output type (Pydantic Field() vs dataclass metadata)
- **Name Collision Resolution**: Automatic renaming and aliasing to avoid Python keyword conflicts

## Testing Strategy

- **Integration Tests**: Located in `tests/main/`, test end-to-end generation for various input/output combinations
- **Parser Tests**: Validate schema parsing and reference resolution
- **Model Tests**: Verify correct Python code generation for each output type
- **Test Data**: Extensive real-world schemas in `tests/data/` covering edge cases

## Configuration

The tool supports extensive configuration through:
- Command-line arguments (see `arguments.py`)
- pyproject.toml `[tool.datamodel-codegen]` section
- Environment variables for HTTP configuration

## Recent Feature Implementation: --use-type-alias Flag

### Overview
Added comprehensive support for TypeAlias generation as an alternative to root models across all schema types (JSON Schema, OpenAPI, GraphQL).

### Implementation Details

**Core Changes:**
- `src/datamodel_code_generator/arguments.py`: Added `--use-type-alias` CLI flag
- `src/datamodel_code_generator/model/type_alias.py`: New TypeAlias model class using Jinja2 template
- `src/datamodel_code_generator/model/template/type_alias.jinja2`: Template for TypeAlias generation
- `src/datamodel_code_generator/model/__init__.py`: Modified `get_data_model_types()` to conditionally use TypeAlias instead of root models

**Behavior:**
- When `--use-type-alias` is used, "simple types" (root-level schemas) generate TypeAlias declarations instead of root model classes
- Supports both annotated and non-annotated TypeAlias based on schema metadata (title, description)
- Works across all output model types (Pydantic v1/v2, dataclasses, TypedDict, msgspec)

**Examples:**
```python
# Without --use-type-alias (traditional root models)
class Model(RootModel[Union[str, int]]):
    root: Union[str, int]

# With --use-type-alias
Model: TypeAlias = Union[str, int]

# With metadata (title/description)
Model: TypeAlias = Annotated[Union[str, int], Field(..., title='My Model')]
```

### Test Coverage

**Comprehensive tests added for all schema types:**

1. **JSON Schema** (`tests/main/jsonschema/test_main_jsonschema.py::test_main_jsonschema_type_alias`)
   - Uses schema with `definitions` containing multiple type scenarios
   - Covers: primitive types, unions, arrays, annotated types

2. **OpenAPI** (`tests/main/openapi/test_main_openapi.py::test_main_openapi_type_alias`)
   - Uses OpenAPI component schemas for TypeAlias generation
   - Covers: string types, unions, arrays, annotated unions

3. **GraphQL** (`tests/main/graphql/test_main_graphql.py::test_main_graphql_type_alias`)
   - Uses GraphQL scalars and unions for TypeAlias generation
   - Covers: custom scalars (`SimpleString`), built-in scalars with documentation (`Boolean`, `Int`, `String`), and union types (`UnionType`)
   - Note: Only scalars and unions generate TypeAlias; regular types/interfaces generate normal classes

**Test Data Files:**
- `tests/data/jsonschema/type_alias.json` + expected output
- `tests/data/openapi/type_alias.yaml` + expected output
- `tests/data/graphql/type_alias.graphql` + expected output

### Documentation Updates
- Updated README.md and docs/index.md with new flag documentation
- Flag description: "Use TypeAlias instead of root models"

### Key Technical Decisions
1. **TypeAlias vs Root Models**: TypeAlias is only used for root-level "simple types", not complex objects with properties
2. **Metadata Handling**: Automatically uses Annotated wrapper when schema has title/description
3. **Template Architecture**: Used Jinja2 template for consistency with existing model generation
4. **Backwards Compatibility**: Flag is optional, existing behavior unchanged when not specified

## Common Pitfalls

- Remote schema resolution requires the `[http]` extra
- GraphQL support requires the `[graphql]` extra
- Some formatters (black, ruff) have version-specific behavior
- Pydantic v1 vs v2 have different constraint and validation approaches