from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Type, Union

from datamodel_code_generator.types import DataType, Imports
from pydantic import BaseModel, Schema

from ..model.base import DataModel, DataModelField, Types


def snake_to_upper_camel(word: str) -> str:
    return ''.join(x.capitalize() for x in word.split('_'))


json_schema_data_formats: Dict[str, Dict[str, Types]] = {
    'integer': {'int32': Types.int32, 'int64': Types.int64, 'default': Types.integer},
    'number': {
        'float': Types.float,
        'double': Types.double,
        'time': Types.time,
        'default': Types.number,
    },
    'string': {
        'default': Types.string,
        'byte': Types.byte,  # base64 encoded string
        'binary': Types.binary,
        'date': Types.date,
        'date-time': Types.date_time,
        'password': Types.password,
        'email': Types.email,
        'uuid': Types.uuid,
        'uuid1': Types.uuid1,
        'uuid2': Types.uuid2,
        'uuid3': Types.uuid3,
        'uuid4': Types.uuid4,
        'uuid5': Types.uuid5,
        'uri': Types.uri,
        'ipv4': Types.ipv4,
        'ipv6': Types.ipv6,
    },
    'boolean': {'default': Types.boolean},
}


class JsonSchemaObject(BaseModel):
    items: Union[List['JsonSchemaObject'], 'JsonSchemaObject', None]
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
    ref: Optional[str] = Schema(default=None, alias='$ref')  # type: ignore
    nullable: Optional[bool] = False

    @property
    def is_object(self) -> bool:
        return self.properties is not None or self.type == 'object'

    @property
    def is_array(self) -> bool:
        return self.items is not None or self.type == 'array'

    @property
    def ref_object_name(self) -> str:
        return self.ref.split('/')[-1]  # type: ignore


JsonSchemaObject.update_forward_refs()


def get_data_type(obj: JsonSchemaObject, data_model: Type[DataModel]) -> DataType:
    format_ = obj.format or 'default'
    if obj.type is None:
        raise ValueError(f'invalid schema object {obj}')

    return data_model.get_data_type(
        json_schema_data_formats[obj.type][format_], **obj.dict()
    )


class Parser(ABC):
    def __init__(
        self,
        data_model_type: Type[DataModel],
        data_model_root_type: Type[DataModel],
        data_model_field_type: Type[DataModelField] = DataModelField,
        filename: Optional[str] = None,
        base_class: Optional[str] = None,
        target_python_version: str = '3.7',
        text: Optional[str] = None,
    ):

        self.data_model_type: Type[DataModel] = data_model_type
        self.data_model_root_type: Type[DataModel] = data_model_root_type
        self.data_model_field_type: Type[DataModelField] = data_model_field_type
        self.filename: Optional[str] = filename
        self.imports: Imports = Imports()
        self.base_class: Optional[str] = base_class
        self.created_model_names: Set[str] = set()
        self.target_python_version: str = target_python_version
        self.un_resolve_classes: Set[str] = set()
        self.text: Optional[str] = text

    def get_type_name(self, name: str) -> str:
        if self.target_python_version == '3.6':
            return f"'{name}'"
        return name

    def add_un_resolve_class(self, class_name: str, reference_name: Union[str, List[str]]) -> None:
        if isinstance(reference_name, str):
            if reference_name not in self.created_model_names:
                self.un_resolve_classes.add(class_name)
        elif isinstance(reference_name, list):
            if set(reference_name) - self.created_model_names:
                self.un_resolve_classes.add(class_name)

    @abstractmethod
    def parse(
        self, with_import: Optional[bool] = True, format_: Optional[bool] = True
    ) -> str:
        raise NotImplementedError
