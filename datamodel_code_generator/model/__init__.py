from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable, NamedTuple, Optional, Type

from ..types import DataTypeManager as DataTypeManagerABC
from .base import ConstraintsBase, DataModel, DataModelFieldBase

if TYPE_CHECKING:
    from .. import DataModelType


class DataModelSet(NamedTuple):
    data_model: Type[DataModel]
    root_model: Type[DataModel]
    field_model: Type[DataModelFieldBase]
    data_type_manager: Type[DataTypeManagerABC]
    dump_resolve_reference_action: Optional[Callable[[Iterable[str]], str]]


def get_data_model_types(data_model_type: DataModelType) -> DataModelSet:
    from .. import DataModelType
    from . import dataclass, pydantic, rootmodel
    from .types import DataTypeManager

    if data_model_type == DataModelType.PydanticBaseModel:
        return DataModelSet(
            data_model=pydantic.BaseModel,
            root_model=pydantic.CustomRootType,
            field_model=pydantic.DataModelField,
            data_type_manager=pydantic.DataTypeManager,
            dump_resolve_reference_action=pydantic.dump_resolve_reference_action,
        )
    elif data_model_type == DataModelType.DataclassesDataclass:
        return DataModelSet(
            data_model=dataclass.DataClass,
            root_model=rootmodel.RootModel,
            field_model=dataclass.DataModelField,
            data_type_manager=DataTypeManager,
            dump_resolve_reference_action=None,
        )
    raise ValueError(
        f'{data_model_type} is unsupported data model type'
    )  # pragma: no cover


__all__ = ['ConstraintsBase', 'DataModel', 'DataModelFieldBase']
