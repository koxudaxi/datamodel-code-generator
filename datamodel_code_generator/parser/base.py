from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, Union, List

from pydantic import BaseModel, Schema

from ..model.base import DataModel, DataModelField


class DataType(BaseModel):
    type: str
    is_func: bool = False
    kwargs: Optional[Dict[str, Any]]

    @property
    def type_hint(self) -> str:
        # if self.is_func:
        #     if self.kwargs:
        #         kwargs: str = ', '.join(f'{k}={v}' for k, v in self.kwargs.items())
        #         return f'{self.type}({kwargs})'
        #     return f'{self.type}()'
        return self.type


json_schema_data_formats: Dict[str, Dict[str, DataType]] = {
    'integer': {'int32': DataType(type='int'), 'int64': DataType(type='int')},
    'number': {
        'float': DataType(type='float'),
        'double': DataType(type='float'),
        'time': DataType(type='time'),
    },
    'string': {
        'default': DataType(type='str'),
        'byte': DataType(type='str'),  # base64 encoded string
        'binary': DataType(type='bytes'),
        'date': DataType(type='date'),
        'date-time': DataType(type='datetime'),
        'password': DataType(type='SecretStr'),
        'email': DataType(type='EmailStr'),
        'uri': DataType(type='UrlStr'),
        'ipv4': DataType(type='IPv4Address'),
        'ipv6': DataType(type='IPv6Address'),
    },
    'boolean': {'default': DataType(type='bool')},
}


class JsonSchemaObject(BaseModel):
    items: Union['JsonSchemaObject', List['JsonSchemaObject'], None]
    uniqueItem: Optional[bool]
    type: Optional[str]
    format: Optional[str]
    pattern: Optional[str]
    minLength: Optional[int]
    maxLength: Optional[int]
    minimum: Optional[float]
    maximum: Optional[float]
    multipleOf: Optional[float]
    exclusiveMaximum: Optional[bool]
    exclusiveMinimum: Optional[bool]
    additionalProperties: Optional['JsonSchemaObject']
    anyOf: Optional[List['JsonSchemaObject']]
    enum: Optional[List[str]]
    writeOnly: Optional[bool]
    properties: Optional[Dict[str, 'JsonSchemaObject']]
    required: Optional[List[str]]
    ref: Optional[str] = Schema(default=None, alias='$ref')

    @property
    def is_object(self) -> bool:
        return self.properties is not None or self.type == 'object'

    @property
    def is_array(self) -> bool:
        return self.items is not None or self.type == 'array'


JsonSchemaObject.update_forward_refs()


def get_data_type(obj: JsonSchemaObject) -> DataType:
    format_ = obj.format or 'default'
    return json_schema_data_formats[obj.type][format_]


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
