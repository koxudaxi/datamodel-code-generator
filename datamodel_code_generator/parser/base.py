from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Set, Tuple, Type, Union

import inflect

from .. import PythonVersion
from ..imports import Imports
from ..model.base import DataModel, DataModelField, TemplateBase
from ..types import DataType
from .jsonschema import JsonSchemaObject, json_schema_data_formats

inflect_engine = inflect.engine()


def get_singular_name(name: str) -> str:
    singular_name = inflect_engine.singular_noun(name)
    if singular_name is False:
        singular_name = f'{name}Item'
    return singular_name


def snake_to_upper_camel(word: str) -> str:
    return ''.join(x[0].upper() + x[1:] for x in word.split('_'))


def dump_templates(templates: Union[TemplateBase, List[TemplateBase]]) -> str:
    if isinstance(templates, TemplateBase):
        templates = [templates]
    return '\n\n\n'.join(str(m) for m in templates)


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
        target_python_version: PythonVersion = PythonVersion.PY_37,
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
        self.target_python_version: PythonVersion = target_python_version
        self.unresolved_classes: ReferenceMapSet = OrderedDict()
        self.text: Optional[str] = text
        self.dump_resolve_reference_action: Optional[
            Callable[[List[str]], str]
        ] = dump_resolve_reference_action

    def get_type_name(self, name: str) -> str:
        if self.target_python_version == PythonVersion.PY_36:
            return f"'{name}'"
        return name

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

    def add_unresolved_classes(
        self, class_name: str, reference_names: Union[str, List[str]]
    ) -> None:
        if isinstance(reference_names, str):
            reference_names = [reference_names]
        if self.target_python_version == PythonVersion.PY_36:
            reference_names = [r.replace("'", "") for r in reference_names]
        unresolved_reference = set(reference_names) - self.created_model_names
        if unresolved_reference:
            self.unresolved_classes[class_name] = unresolved_reference

    @abstractmethod
    def parse(
        self, with_import: Optional[bool] = True, format_: Optional[bool] = True
    ) -> str:
        raise NotImplementedError

    def get_data_type(self, obj: JsonSchemaObject) -> DataType:
        format_ = obj.format or 'default'
        if obj.type is None:
            raise ValueError(f'invalid schema object {obj}')

        return self.data_model_type.get_data_type(
            json_schema_data_formats[obj.type][format_], **obj.dict()
        )
