"""Model generation module.

Provides factory functions and classes for generating different output formats
(Pydantic, dataclasses, TypedDict, msgspec) based on configuration.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, NamedTuple

from datamodel_code_generator import PythonVersion

from .base import UNDEFINED as UNDEFINED
from .base import ConstraintsBase, DataModel, DataModelFieldBase, _rebuild_model_with_datamodel_namespace

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

    from . import scalar, type_alias, union  # noqa: PLC0415

    pydantic_v2_models = {DataModelType.PydanticV2BaseModel, DataModelType.PydanticV2Dataclass}
    if target_python_version.has_type_statement:
        type_alias_class = type_alias.TypeStatement
        scalar_class = scalar.DataTypeScalarTypeStatement
        union_class = union.DataTypeUnionTypeStatement
    elif data_model_type in pydantic_v2_models:
        type_alias_class = type_alias.TypeAliasTypeBackport
        scalar_class = scalar.DataTypeScalarTypeBackport
        union_class = union.DataTypeUnionTypeBackport
    else:  # 3.10+ always has TypeAlias
        type_alias_class = type_alias.TypeAlias
        scalar_class = scalar.DataTypeScalar
        union_class = union.DataTypeUnion

    match data_model_type:
        case DataModelType.PydanticV2BaseModel:
            from . import pydantic_v2  # noqa: PLC0415

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
        case DataModelType.PydanticV2Dataclass:
            from . import pydantic_v2  # noqa: PLC0415
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
        case DataModelType.DataclassesDataclass:
            from . import dataclass  # noqa: PLC0415

            return DataModelSet(
                data_model=dataclass.DataClass,
                root_model=type_alias_class,
                field_model=dataclass.DataModelField,
                data_type_manager=dataclass.DataTypeManager,
                dump_resolve_reference_action=None,
                scalar_model=scalar_class,
                union_model=union_class,
            )
        case DataModelType.TypingTypedDict:
            from . import typed_dict  # noqa: PLC0415
            from .types import DataTypeManager  # noqa: PLC0415

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
        case DataModelType.MsgspecStruct:
            from . import msgspec  # noqa: PLC0415

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


__all__ = [
    "DEFAULT_TARGET_PYTHON_VERSION",
    "UNDEFINED",
    "ConstraintsBase",
    "DataModel",
    "DataModelFieldBase",
    "DataModelSet",
    "_rebuild_model_with_datamodel_namespace",
    "get_data_model_types",
]
