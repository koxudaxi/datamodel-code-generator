import re
from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from typing import Any, Callable, List, Optional, Set

from datamodel_code_generator.imports import (
    IMPORT_LIST,
    IMPORT_OPTIONAL,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.types import DataType, Types
from jinja2 import Template
from pydantic import BaseModel, validator

TEMPLATE_DIR: Path = Path(__file__).parents[0] / 'template'

UNION: str = 'Union'
OPTIONAL: str = 'Optional'
LIST: str = 'List'


def optional(func: Callable) -> Callable:
    @wraps(func)
    def inner(self: 'DataModelField', *args: Any, **kwargs: Any) -> Optional[str]:
        type_hint: Optional[str] = func(self, *args, **kwargs)
        if self.required:
            return type_hint
        self.imports.append(IMPORT_OPTIONAL)
        if type_hint is None or type_hint == '':
            return OPTIONAL
        return f'{OPTIONAL}[{type_hint}]'

    return inner


class DataModelField(BaseModel):
    name: Optional[str]
    default: Optional[str]
    required: bool = False
    alias: Optional[str]
    example: Optional[str]
    description: Optional[str]
    data_types: List[DataType] = []
    is_list: bool = False
    is_union: bool = False
    imports: List[Import] = []
    type_hint: Optional[str] = None
    unresolved_types: List[str] = []

    @optional
    def _get_type_hint(self) -> Optional[str]:
        type_hint = ', '.join(d.type_hint for d in self.data_types)
        if not type_hint:
            if self.is_list:
                self.imports.append(IMPORT_LIST)
                return LIST
            return ''
        if len(self.data_types) == 1:
            if self.is_list:
                self.imports.append(IMPORT_LIST)
                return f'{LIST}[{type_hint}]'
            return type_hint
        if self.is_list:
            self.imports.append(IMPORT_LIST)
            if self.is_union:
                self.imports.append(IMPORT_UNION)
                return f'{LIST}[{UNION}[{type_hint}]]'
            return f'{LIST}[{type_hint}]'
        self.imports.append(IMPORT_UNION)
        return f'{UNION}[{type_hint}]'

    @validator('name')
    def validate_name(cls, name: Any) -> Any:
        return re.sub(r'\W', '_', name)

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)
        if not self.alias and 'name' in values:
            self.alias = values['name']
        for data_type in self.data_types:
            self.unresolved_types.extend(data_type.unresolved_types)
            if data_type.imports_:
                self.imports.extend(data_type.imports_)
        self.type_hint = self._get_type_hint()


class TemplateBase(ABC):
    def __init__(self, template_file_path: str) -> None:
        self.template_file_path: str = template_file_path
        self._template: Template = Template(
            (TEMPLATE_DIR / self.template_file_path).read_text()
        )

    @property
    def template(self) -> Template:
        return self._template

    @abstractmethod
    def render(self) -> str:
        raise NotImplementedError

    def _render(self, *args: Any, **kwargs: Any) -> str:
        return self.template.render(*args, **kwargs)

    def __str__(self) -> str:
        return self.render()


class DataModel(TemplateBase, ABC):
    TEMPLATE_FILE_PATH: str = ''
    BASE_CLASS: str = ''

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[str]] = None,
        custom_base_class: Optional[str] = None,
        imports: Optional[List[Import]] = None,
        auto_import: bool = True,
        reference_classes: Optional[List[str]] = None,
    ) -> None:
        if not self.TEMPLATE_FILE_PATH:
            raise Exception('TEMPLATE_FILE_PATH is undefined')

        self.name: str = name
        self.fields: List[DataModelField] = fields or []
        self.decorators: List[str] = decorators or []
        self.imports: List[Import] = imports or []
        self.base_class: Optional[str] = None
        base_classes = [base_class for base_class in base_classes or [] if base_class]
        self.base_classes: List[str] = base_classes

        self.reference_classes: List[str] = [
            r for r in base_classes if r != self.BASE_CLASS
        ] if base_classes else []
        if reference_classes:
            self.reference_classes.extend(reference_classes)

        if self.base_classes:
            self.base_class = ', '.join(self.base_classes)
        else:
            base_class_full_path = custom_base_class or self.BASE_CLASS
            if auto_import:
                if base_class_full_path:
                    self.imports.append(Import.from_full_path(base_class_full_path))
            self.base_class = base_class_full_path.split('.')[-1]

        unresolved_types: Set[str] = set()
        for field in self.fields:
            unresolved_types.update(set(field.unresolved_types))

        self.reference_classes = list(set(self.reference_classes) | unresolved_types)

        if auto_import:
            for field in self.fields:
                self.imports.extend(field.imports)
        super().__init__(template_file_path=self.TEMPLATE_FILE_PATH)

    def render(self) -> str:
        response = self._render(
            class_name=self.name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
        )
        return response

    @classmethod
    @abstractmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError
