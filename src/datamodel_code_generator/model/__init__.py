"""Model generation module.

Provides factory functions and classes for generating different output formats
(Pydantic, dataclasses, TypedDict, msgspec) based on configuration.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, NamedTuple

from datamodel_code_generator import PythonVersion

from .base import ConstraintsBase, DataModel, DataModelFieldBase

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from datamodel_code_generator import DataModelType
    from datamodel_code_generator.types import DataTypeManager as DataTypeManagerABC

DEFAULT_TARGET_PYTHON_VERSION = PythonVersion(f"{sys.version_info.major}.{sys.version_info.minor}")


class DataModelSet(NamedTuple):
    """Collection of model types needed for a specific output format."""

    data_model: type[DataModel]
    root_model: type[DataModel]
    field_model: type[DataModelFieldBase]
    data_type_manager: type[DataTypeManagerABC]
    dump_resolve_reference_action: Callable[[Iterable[str]], str] | None
    scalar_model: type[DataModel]
    union_model: type[DataModel]
    known_third_party: list[str] | None = None


def get_data_model_types(  # noqa: PLR0912
    data_model_type: DataModelType,
    target_python_version: PythonVersion = DEFAULT_TARGET_PYTHON_VERSION,
    use_type_alias: bool = False,  # noqa: FBT001, FBT002
    use_root_model_type_alias: bool = False,  # noqa: FBT001, FBT002
) -> DataModelSet:
    """Get the appropriate model types for the given output format and Python version."""
    from datamodel_code_generator import DataModelType  # noqa: PLC0415

    from . import (  # noqa: PLC0415
        dataclass,
        msgspec,
        pydantic,
        pydantic_v2,
        scalar,
        type_alias,
        typed_dict,
        union,
    )
    from .types import DataTypeManager  # noqa: PLC0415

    # Pydantic v2 requires TypeAliasType; other output types use TypeAlias for better compatibility
    if data_model_type in {DataModelType.PydanticV2BaseModel, DataModelType.PydanticV2Dataclass}:
        if target_python_version.has_type_statement:
            type_alias_class = type_alias.TypeStatement
            scalar_class = scalar.DataTypeScalarTypeStatement
            union_class = union.DataTypeUnionTypeStatement
        else:
            type_alias_class = type_alias.TypeAliasTypeBackport
            scalar_class = scalar.DataTypeScalarTypeBackport
            union_class = union.DataTypeUnionTypeBackport
    elif target_python_version.has_type_statement:
        type_alias_class = type_alias.TypeStatement
        scalar_class = scalar.DataTypeScalarTypeStatement
        union_class = union.DataTypeUnionTypeStatement
    else:  # 3.10+ always has TypeAlias
        type_alias_class = type_alias.TypeAlias
        scalar_class = scalar.DataTypeScalar
        union_class = union.DataTypeUnion

    if data_model_type == DataModelType.PydanticBaseModel:
        return DataModelSet(
            data_model=pydantic.BaseModel,
            root_model=type_alias_class if use_type_alias else pydantic.CustomRootType,
            field_model=pydantic.DataModelField,
            data_type_manager=pydantic.DataTypeManager,
            dump_resolve_reference_action=pydantic.dump_resolve_reference_action,
            scalar_model=scalar_class,
            union_model=union_class,
        )
    if data_model_type == DataModelType.PydanticV2BaseModel:
        if use_type_alias:
            root_model_class: type[DataModel] = type_alias_class
        elif use_root_model_type_alias:
            root_model_class = pydantic_v2.RootModelTypeAlias
        else:
            root_model_class = pydantic_v2.RootModel
        return DataModelSet(
            data_model=pydantic_v2.BaseModel,
            root_model=root_model_class,
            field_model=pydantic_v2.DataModelField,
            data_type_manager=pydantic_v2.DataTypeManager,
            dump_resolve_reference_action=pydantic_v2.dump_resolve_reference_action,
            scalar_model=scalar_class,
            union_model=union_class,
        )
    if data_model_type == DataModelType.PydanticV2Dataclass:
        from .pydantic_v2 import dataclass as pydantic_v2_dataclass  # noqa: PLC0415

        return DataModelSet(
            data_model=pydantic_v2_dataclass.DataClass,
            root_model=type_alias_class,
            field_model=pydantic_v2_dataclass.DataModelField,
            data_type_manager=pydantic_v2.DataTypeManager,
            dump_resolve_reference_action=None,
            scalar_model=scalar_class,
            union_model=union_class,
        )
    if data_model_type == DataModelType.DataclassesDataclass:
        return DataModelSet(
            data_model=dataclass.DataClass,
            root_model=type_alias_class,
            field_model=dataclass.DataModelField,
            data_type_manager=dataclass.DataTypeManager,
            dump_resolve_reference_action=None,
            scalar_model=scalar_class,
            union_model=union_class,
        )
    if data_model_type == DataModelType.TypingTypedDict:
        if target_python_version.has_typed_dict_read_only:
            typed_dict_field_model: type[DataModelFieldBase] = typed_dict.DataModelField
        elif target_python_version.has_typed_dict_non_required:
            typed_dict_field_model = typed_dict.DataModelFieldReadOnlyBackport
        else:
            typed_dict_field_model = typed_dict.DataModelFieldBackport
        return DataModelSet(
            data_model=typed_dict.TypedDict,
            root_model=type_alias_class,
            field_model=typed_dict_field_model,
            data_type_manager=DataTypeManager,
            dump_resolve_reference_action=None,
            scalar_model=scalar_class,
            union_model=union_class,
        )
    if data_model_type == DataModelType.MsgspecStruct:
        return DataModelSet(
            data_model=msgspec.Struct,
            root_model=type_alias_class,
            field_model=msgspec.DataModelField,
            data_type_manager=msgspec.DataTypeManager,
            dump_resolve_reference_action=None,
            known_third_party=["msgspec"],
            scalar_model=scalar_class,
            union_model=union_class,
        )
    msg = f"{data_model_type} is unsupported data model type"  # pragma: no cover
    raise ValueError(msg)  # pragma: no cover


__all__ = ["ConstraintsBase", "DataModel", "DataModelFieldBase"]
