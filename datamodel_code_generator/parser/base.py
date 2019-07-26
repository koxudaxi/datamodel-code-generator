from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Type

from pydantic import BaseModel

from ..model.base import DataModel, DataModelField


class Types(Enum):
    int = 'int'
    float = 'float'
    str = 'str'
    bytes = 'bytes'
    bool = 'bool'
    date = 'date'
    datetime = 'datetime'
    secret_str = 'secret_str'


class DataType(BaseModel):
    type: Types
    format: Optional[str]
    default: Optional[str]
    row_type: Optional[Types]


class Parser(ABC):
    def __init__(
        self,
        data_model_type: Type[DataModel],
        data_model_root_type: Type[DataModel],
        data_model_field_type: Type[DataModelField] = DataModelField,
        filename: str = 'api.yaml',
    ):

        self.data_model_type: Type[DataModel] = data_model_type
        self.data_model_root_type: Type[DataModel] = data_model_root_type
        self.data_model_field_type: Type[DataModelField] = data_model_field_type
        self.filename: str = filename

    @abstractmethod
    def parse(self) -> str:
        raise NotImplementedError
