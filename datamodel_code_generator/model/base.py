import keyword
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Set

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, root_validator

from datamodel_code_generator.imports import (
    IMPORT_LIST,
    IMPORT_OPTIONAL,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.types import DataType, Types

TEMPLATE_DIR: Path = Path(__file__).parents[0] / 'template'

UNION: str = 'Union'
OPTIONAL: str = 'Optional'
LIST: str = 'List'


def optional(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def inner(self: 'DataModelFieldBase', *args: Any, **kwargs: Any) -> Optional[str]:
        type_hint: Optional[str] = func(self, *args, **kwargs)
        if self.required:
            return type_hint
        self.imports.append(IMPORT_OPTIONAL)
        if type_hint is None or type_hint == '':
            return OPTIONAL
        return f'{OPTIONAL}[{type_hint}]'

    return inner


class DataModelFieldBase(BaseModel):
    name: Optional[str]
    default: Optional[Any]
    required: bool = False
    alias: Optional[str]
    example: Any = None
    examples: Any = None
    description: Optional[str]
    title: Optional[str]
    data_types: List[DataType] = []
    is_list: bool = False
    is_union: bool = False
    imports: List[Import] = []
    type_hint: Optional[str] = None
    unresolved_types: List[str] = []
    field: Optional[str]

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

    @root_validator
    def validate_root(cls, values: Any) -> Dict[str, Any]:
        name = values.get('name')
        if name:
            if keyword.iskeyword(name):
                alias = name
                name += '_'
            elif re.search(r'\W', name):
                alias = name
                name = re.sub(r'\W', '_', name)
            else:
                return values
            if not values.get('alias'):
                values['alias'] = alias
            values['name'] = name
        return values

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)
        for data_type in self.data_types:
            self.unresolved_types.extend(data_type.unresolved_types)
            if data_type.imports_:
                self.imports.extend(data_type.imports_)
        self.type_hint = self._get_type_hint()


class TemplateBase(ABC):
    def __init__(self, template_file_path: Path) -> None:
        self.template_file_path: Path = template_file_path
        loader = FileSystemLoader(str(TEMPLATE_DIR / template_file_path.parent))
        self.environment: Environment = Environment(loader=loader)
        self._template: Template = self.environment.get_template(
            template_file_path.name
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


class Config(BaseModel):
    extra: Optional[str] = None


class DataModel(TemplateBase, ABC):
    TEMPLATE_FILE_PATH: str = ''
    BASE_CLASS: str = ''

    def __init__(
        self,
        name: str,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[str]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        imports: Optional[List[Import]] = None,
        auto_import: bool = True,
        reference_classes: Optional[List[str]] = None,
    ) -> None:
        if not self.TEMPLATE_FILE_PATH:
            raise Exception('TEMPLATE_FILE_PATH is undefined')

        template_file_path = Path(self.TEMPLATE_FILE_PATH)
        if custom_template_dir is not None:
            custom_template_file_path = custom_template_dir / template_file_path.name
            if custom_template_file_path.exists():
                template_file_path = custom_template_file_path

        self.name: str = name
        self.fields: List[DataModelFieldBase] = fields or []
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
            self.base_class = base_class_full_path.rsplit('.', 1)[-1]

        if '.' in name:
            module, class_name = name.rsplit('.', 1)
            prefix = f'{module}.'
            if self.base_class.startswith(prefix):
                self.base_class = self.base_class.replace(prefix, '', 1)
        else:
            class_name = name

        self.class_name: str = class_name

        self.extra_template_data = (
            extra_template_data[self.name]
            if extra_template_data is not None
            else defaultdict(dict)
        )

        unresolved_types: Set[str] = set()
        for field in self.fields:
            unresolved_types.update(set(field.unresolved_types))

        self.reference_classes = list(set(self.reference_classes) | unresolved_types)

        if auto_import:
            for field in self.fields:
                self.imports.extend(field.imports)

        super().__init__(template_file_path=template_file_path)

    def render(self) -> str:
        response = self._render(
            class_name=self.class_name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
            **self.extra_template_data,
        )
        return response

    @classmethod
    @abstractmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError
