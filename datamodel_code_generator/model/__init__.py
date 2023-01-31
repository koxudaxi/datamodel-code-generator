from __future__ import annotations

from enum import Enum
from typing import NamedTuple, Type

from .base import ConstraintsBase, DataModel, DataModelFieldBase

__all__ = ['ConstraintsBase', 'DataModel', 'DataModelFieldBase']


class DataModelType(Enum):
    PydanticBaseModel = 'pydantic.BaseModel'
    DataclassesDataclass = 'dataclasses.dataclass'


class DataModelSet(NamedTuple):
    data_model: Type[DataModel]
    root_model: Type[DataModel]
    field_model: Type[DataModelFieldBase]


def get_data_model_types(data_model_type: DataModelType) -> DataModelSet:
    from . import dataclass, pydantic, rootmodel

    if data_model_type == DataModelType.PydanticBaseModel:
        return DataModelSet(
            data_model=pydantic.BaseModel,
            root_model=pydantic.CustomRootType,
            field_model=pydantic.DataModelField,
        )
    elif data_model_type == DataModelType.DataclassesDataclass:
        return DataModelSet(
            data_model=dataclass.DataClass,
            root_model=rootmodel.RootModel,
            field_model=dataclass.DataModelField,
        )
    raise ValueError(f'{data_model_type} is unsupported data model type')
