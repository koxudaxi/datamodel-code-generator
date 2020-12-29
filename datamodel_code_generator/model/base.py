import keyword
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterator, List, Optional, Set

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, root_validator

from datamodel_code_generator import cached_property
from datamodel_code_generator.imports import IMPORT_OPTIONAL, Import
from datamodel_code_generator.types import DataType

TEMPLATE_DIR: Path = Path(__file__).parents[0] / 'template'

OPTIONAL: str = 'Optional'

ALL_MODEL: str = '#all#'


class ConstraintsBase(BaseModel):
    ...


class DataModelFieldBase(BaseModel):
    name: Optional[str]
    default: Optional[Any]
    required: bool = False
    alias: Optional[str]
    example: Any = None
    examples: Any = None
    description: Optional[str]
    title: Optional[str]
    data_type: DataType
    constraints: Any = None
    strip_default_none: bool = False

    @property
    def type_hint(self) -> str:
        type_hint = self.data_type.type_hint
        if self.required:
            return type_hint
        if type_hint is None or type_hint == '':
            return OPTIONAL
        return f'{OPTIONAL}[{type_hint}]'

    @property
    def imports(self) -> List[Import]:
        if not self.required:
            return self.data_type.imports_ + [IMPORT_OPTIONAL]
        return self.data_type.imports_

    @property
    def unresolved_types(self) -> Set[str]:
        return self.data_type.unresolved_types

    @property
    def field(self) -> Optional[str]:
        """for backwards compatibility"""
        return None

    @property
    def method(self) -> Optional[str]:
        return None

    @root_validator
    def validate_root(cls, values: Any) -> Dict[str, Any]:
        name: Optional[str] = values.get('name')
        if name:
            if keyword.iskeyword(name):
                alias = name
                name += '_'
            elif name.isidentifier():
                return values
            else:  # pragma: no cover
                alias = name
                name = re.sub(r'\W', '_', name)
            if not values.get('alias'):
                values['alias'] = alias
            values['name'] = name
        return values

    @property
    def represented_default(self) -> str:
        return repr(self.default)


@lru_cache()
def get_template(template_file_path: Path) -> Template:
    loader = FileSystemLoader(str(TEMPLATE_DIR / template_file_path.parent))
    environment: Environment = Environment(loader=loader)
    return environment.get_template(template_file_path.name)


class TemplateBase(ABC):
    def __init__(self, template_file_path: Path) -> None:
        self.template_file_path: Path = template_file_path
        self._template: Template = get_template(template_file_path)

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
        methods: Optional[List[str]] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
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
        self.path: Optional[Path] = path

        self.reference_classes: Set[str] = {
            r for r in base_classes if r != self.BASE_CLASS
        } if base_classes else set()
        if reference_classes:
            self.reference_classes.update(reference_classes)

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
        if extra_template_data:
            all_model_extra_template_data = extra_template_data.get(ALL_MODEL)
            if all_model_extra_template_data:
                self.extra_template_data.update(all_model_extra_template_data)

        unresolved_types: Set[str] = {*()}
        for field in self.fields:
            unresolved_types.update(field.unresolved_types)

        self.reference_classes |= unresolved_types

        if auto_import:
            for field in self.fields:
                self.imports.extend(field.imports)

        self.methods: List[str] = methods or []

        self.description = description
        super().__init__(template_file_path=template_file_path)

    @cached_property
    def module_path(self) -> List[str]:
        if self.path:
            return [
                *self.path.parts[:-1],
                self.path.stem,
                *self.name.split('.')[:-1],
            ]
        return self.name.split('.')[:-1]

    @property
    def all_data_types(self) -> Iterator['DataType']:
        for field in self.fields:
            yield from field.data_type.all_data_types

    def render(self) -> str:
        response = self._render(
            class_name=self.class_name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
            methods=self.methods,
            description=self.description,
            **self.extra_template_data,
        )
        return response
