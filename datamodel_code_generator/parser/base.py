from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Set, Tuple, Type, Union

from datamodel_code_generator.types import DataType, Imports
from pydantic import BaseModel, Schema

from ..model.base import DataModel, DataModelField, Types


def snake_to_upper_camel(word: str) -> str:
    return ''.join(x[0].upper() + x[1:] for x in word.split('_'))


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


ReferenceMapSet = Dict[str, Set[str]]
ResolvedReferences = List[str]


def resolve_references(
    resolved_references: ResolvedReferences, references: ReferenceMapSet
) -> Tuple[ResolvedReferences, ReferenceMapSet]:
    unresolved_references: ReferenceMapSet = OrderedDict()
    for key, item in references.items():
        if key in item and len(item) == 1:  # only self-referencing
            resolved_references.append(key)
        elif (
            not item - set(key) - set(resolved_references)
        ):  # reference classes have been resolved
            resolved_references.append(key)
        else:
            unresolved_references[key] = item
    if unresolved_references:
        try:
            return resolve_references(resolved_references, unresolved_references)
        except RecursionError:
            unresolved_classes = ', '.join(
                f"[class: {k} references: {v}]"
                for k, v in unresolved_references.items()
            )
            raise Exception(f'A Parser can not resolve classes: {unresolved_classes}.')
    return resolved_references, unresolved_references


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
        dump_resolve_reference_action: Optional[Callable[[List[str]], str]] = None,
    ):

        self.data_model_type: Type[DataModel] = data_model_type
        self.data_model_root_type: Type[DataModel] = data_model_root_type
        self.data_model_field_type: Type[DataModelField] = data_model_field_type
        self.filename: Optional[str] = filename
        self.imports: Imports = Imports()
        self.base_class: Optional[str] = base_class
        self.created_model_names: Set[str] = set()
        self.target_python_version: str = target_python_version
        self.unresolved_classes: ReferenceMapSet = OrderedDict()
        self.text: Optional[str] = text
        self.dump_resolve_reference_action: Optional[
            Callable[[List[str]], str]
        ] = dump_resolve_reference_action

    def get_type_name(self, name: str) -> str:
        if self.target_python_version == '3.6':
            return f"'{name}'"
        return name

    def add_unresolved_classes(
        self, class_name: str, reference_names: Union[str, List[str]]
    ) -> None:
        if isinstance(reference_names, str):
            if self.target_python_version == '3.6':
                reference_names = reference_names.replace("'", "")
            if reference_names not in self.created_model_names:  # pragma: no cover
                self.unresolved_classes[class_name] = {reference_names}
        else:
            if self.target_python_version == '3.6':
                reference_names = [r.replace("'", "") for r in reference_names]
            unresolved_reference = set(reference_names) - self.created_model_names
            if unresolved_reference:
                self.unresolved_classes[class_name] = unresolved_reference

    @abstractmethod
    def parse(
        self, with_import: Optional[bool] = True, format_: Optional[bool] = True
    ) -> str:
        raise NotImplementedError
