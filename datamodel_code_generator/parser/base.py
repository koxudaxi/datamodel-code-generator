from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Set, Tuple, Type, Union

import inflect

from .. import PythonVersion
from ..imports import Imports
from ..model.base import DataModel, DataModelField, TemplateBase
from ..types import DataType, DataTypePy36
from .jsonschema import JsonSchemaObject, json_schema_data_formats

inflect_engine = inflect.engine()


def get_singular_name(name: str) -> str:
    singular_name = inflect_engine.singular_noun(name)
    if singular_name is False:
        singular_name = f'{name}Item'
    return singular_name


def snake_to_upper_camel(word: str) -> str:
    return ''.join(x[0].upper() + x[1:] for x in word.split('_'))


def dump_templates(templates: Union[DataModel, List[DataModel]]) -> str:
    if isinstance(templates, TemplateBase):
        templates = [templates]

    return '\n\n\n'.join(str(m) for m in templates)


ReferenceMapSet = Dict[str, Set[str]]
SortedDataModels = Dict[str, DataModel]


def sort_data_models(
    unsorted_data_models: List[DataModel],
    sorted_data_models: Optional[SortedDataModels] = None,
    require_update_action_models: Optional[List[str]] = None,
) -> Tuple[List[DataModel], SortedDataModels, List[str]]:
    if sorted_data_models is None:
        sorted_data_models = OrderedDict()
    if require_update_action_models is None:
        require_update_action_models = []

    unresolved_references: List[DataModel] = []
    for model in unsorted_data_models:
        if not model.reference_classes:
            sorted_data_models[model.name] = model
        elif (
            model.name in model.reference_classes and len(model.reference_classes) == 1
        ):  # only self-referencing
            sorted_data_models[model.name] = model
            require_update_action_models.append(model.name)
        elif (
            not set(model.reference_classes) - set(model.name) - set(sorted_data_models)
        ):  # reference classes have been resolved
            sorted_data_models[model.name] = model
            if model.name in model.reference_classes:
                require_update_action_models.append(model.name)
        else:
            unresolved_references.append(model)
    if unresolved_references:
        try:
            return sort_data_models(
                unresolved_references, sorted_data_models, require_update_action_models
            )
        except RecursionError:
            unresolved_classes = ', '.join(
                f"[class: {item.name} references: {item.reference_classes}]"
                for item in unresolved_references
            )
            raise Exception(f'A Parser can not resolve classes: {unresolved_classes}.')
    return unresolved_references, sorted_data_models, require_update_action_models


class Parser(ABC):
    def __init__(
        self,
        data_model_type: Type[DataModel],
        data_model_root_type: Type[DataModel],
        data_model_field_type: Type[DataModelField] = DataModelField,
        filename: Optional[str] = None,
        base_class: Optional[str] = None,
        target_python_version: PythonVersion = PythonVersion.PY_37,
        text: Optional[str] = None,
        result: Optional[List[DataModel]] = None,
        dump_resolve_reference_action: Optional[Callable[[List[str]], str]] = None,
    ):

        self.data_model_type: Type[DataModel] = data_model_type
        self.data_model_root_type: Type[DataModel] = data_model_root_type
        self.data_model_field_type: Type[DataModelField] = data_model_field_type
        self.filename: Optional[str] = filename
        self.imports: Imports = Imports()
        self.base_class: Optional[str] = base_class
        self.created_model_names: Set[str] = set()
        self.target_python_version: PythonVersion = target_python_version
        self.text: Optional[str] = text
        self.results: List[DataModel] = result or []
        self.dump_resolve_reference_action: Optional[
            Callable[[List[str]], str]
        ] = dump_resolve_reference_action

        if self.target_python_version == PythonVersion.PY_36:
            self.data_type: Type[DataType] = DataTypePy36
        else:
            self.data_type = DataType

    def append_result(self, data_model: DataModel) -> None:
        self.created_model_names.add(data_model.name)
        self.results.append(data_model)

    def get_class_name(self, field_name: str) -> str:
        upper_camel_name = snake_to_upper_camel(field_name)
        return self.get_uniq_name(upper_camel_name)

    def get_uniq_name(self, name: str) -> str:
        uniq_name: str = name
        count: int = 1
        while uniq_name in self.created_model_names:
            uniq_name = f'{name}_{count}'
            count += 1
        return uniq_name

    @abstractmethod
    def parse(
        self, with_import: Optional[bool] = True, format_: Optional[bool] = True
    ) -> Union[str, Dict[Tuple[str, ...], str]]:
        raise NotImplementedError

    def get_data_type(self, obj: JsonSchemaObject) -> DataType:
        format_ = obj.format or 'default'
        if obj.type is None:
            raise ValueError(f'invalid schema object {obj}')

        return self.data_model_type.get_data_type(
            json_schema_data_formats[obj.type][format_], **obj.dict()
        )
