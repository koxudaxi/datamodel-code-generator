"""Enum definitions for datamodel-code-generator.

This module contains all enum types used by the CLI and code generation,
separated from the main module to allow fast CLI startup without loading pydantic.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

from typing_extensions import TypedDict


class DataclassArguments(TypedDict, total=False):
    """Arguments for @dataclass decorator."""

    init: bool
    repr: bool
    eq: bool
    order: bool
    unsafe_hash: bool
    frozen: bool
    match_args: bool
    kw_only: bool
    slots: bool
    weakref_slot: bool


MIN_VERSION: Final[int] = 10
MAX_VERSION: Final[int] = 13
DEFAULT_SHARED_MODULE_NAME: Final[str] = "shared"


class InputFileType(Enum):
    """Supported input file types for schema parsing."""

    Auto = "auto"
    OpenAPI = "openapi"
    JsonSchema = "jsonschema"
    Json = "json"
    Yaml = "yaml"
    Dict = "dict"
    CSV = "csv"
    GraphQL = "graphql"


class DataModelType(Enum):
    """Supported output data model types."""

    PydanticBaseModel = "pydantic.BaseModel"
    PydanticV2BaseModel = "pydantic_v2.BaseModel"
    PydanticV2Dataclass = "pydantic_v2.dataclass"
    DataclassesDataclass = "dataclasses.dataclass"
    TypingTypedDict = "typing.TypedDict"
    MsgspecStruct = "msgspec.Struct"


class ReuseScope(Enum):
    """Scope for model reuse deduplication.

    module: Deduplicate identical models within each module (default).
    tree: Deduplicate identical models across all modules, placing shared models in shared.py.
    """

    Module = "module"
    Tree = "tree"


class OpenAPIScope(Enum):
    """Scopes for OpenAPI model generation."""

    Schemas = "schemas"
    Paths = "paths"
    Tags = "tags"
    Parameters = "parameters"
    Webhooks = "webhooks"
    RequestBodies = "requestbodies"


class AllExportsScope(Enum):
    """Scope for __all__ exports in __init__.py.

    children: Export models from direct child modules only.
    recursive: Export models from all descendant modules recursively.
    """

    Children = "children"
    Recursive = "recursive"


class AllExportsCollisionStrategy(Enum):
    """Strategy for handling name collisions in recursive exports.

    error: Raise an error when name collision is detected.
    minimal_prefix: Add module prefix only to colliding names.
    full_prefix: Add full module path prefix to all colliding names.
    """

    Error = "error"
    MinimalPrefix = "minimal-prefix"
    FullPrefix = "full-prefix"


class FieldTypeCollisionStrategy(Enum):
    """Strategy for handling field name and type name collisions.

    rename_field: Rename the field with a suffix and add alias (default).
    rename_type: Rename the type class with a suffix to preserve field name.
    """

    RenameField = "rename-field"
    RenameType = "rename-type"


class NamingStrategy(Enum):
    """Strategy for generating unique model names when duplicates occur.

    numbered: Append numeric suffix (Address1, Address2) [default].
    parent_prefixed: Prefix with parent model name (CustomerAddress, UserAddress).
    full_path: Use full schema path for unique names (OrdersItemsAddress).
    primary_first: Prioritize primary schema definitions, others get suffix.
    """

    Numbered = "numbered"
    ParentPrefixed = "parent-prefixed"
    FullPath = "full-path"
    PrimaryFirst = "primary-first"


class CollapseRootModelsNameStrategy(Enum):
    """Strategy for naming when collapsing root models with object references.

    child: Keep the inner (child) model's name, remove the wrapper.
    parent: Rename inner model to wrapper's name, remove the wrapper.
    """

    Child = "child"
    Parent = "parent"


class AllOfMergeMode(Enum):
    """Mode for field merging in allOf schemas.

    constraints: Merge only constraint fields (minItems, maxItems, pattern, etc.) from parent.
    all: Merge constraints plus annotation fields (default, examples) from parent.
    none: Do not merge any fields from parent properties.
    """

    Constraints = "constraints"
    All = "all"
    NoMerge = "none"


class GraphQLScope(Enum):
    """Scopes for GraphQL model generation."""

    Schema = "schema"


class ReadOnlyWriteOnlyModelType(Enum):
    """Model generation strategy for readOnly/writeOnly fields.

    RequestResponse: Generate only Request/Response model variants (no base model).
    All: Generate Base, Request, and Response models.
    """

    RequestResponse = "request-response"
    All = "all"


class ModuleSplitMode(Enum):
    """Mode for splitting generated models into separate files.

    Single: Generate one file per model class.
    """

    Single = "single"


class TargetPydanticVersion(Enum):
    """Target Pydantic version for generated code.

    V2: Generate code compatible with Pydantic 2.0+ (uses populate_by_name).
    V2_11: Generate code for Pydantic 2.11+ (uses validate_by_name).
    """

    V2 = "2"
    V2_11 = "2.11"


class UnionMode(Enum):
    """Union discriminator mode for Pydantic v2."""

    smart = "smart"
    left_to_right = "left_to_right"


class StrictTypes(Enum):
    """Strict type options for generated models."""

    str = "str"
    bytes = "bytes"
    int = "int"
    float = "float"
    bool = "bool"


__all__ = [
    "DEFAULT_SHARED_MODULE_NAME",
    "MAX_VERSION",
    "MIN_VERSION",
    "AllExportsCollisionStrategy",
    "AllExportsScope",
    "AllOfMergeMode",
    "CollapseRootModelsNameStrategy",
    "DataModelType",
    "DataclassArguments",
    "FieldTypeCollisionStrategy",
    "GraphQLScope",
    "InputFileType",
    "ModuleSplitMode",
    "NamingStrategy",
    "OpenAPIScope",
    "ReadOnlyWriteOnlyModelType",
    "ReuseScope",
    "StrictTypes",
    "TargetPydanticVersion",
    "UnionMode",
]
