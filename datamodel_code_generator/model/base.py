import keyword
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
)

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, root_validator

from datamodel_code_generator import cached_property
from datamodel_code_generator.imports import IMPORT_OPTIONAL, Import
from datamodel_code_generator.reference import Reference, _BaseModel
from datamodel_code_generator.types import DataType, chain_as_tuple

TEMPLATE_DIR: Path = Path(__file__).parents[0] / 'template'

OPTIONAL: str = 'Optional'

ALL_MODEL: str = '#all#'


class ConstraintsBase(BaseModel):
    ...


class DataModelFieldBase(_BaseModel):
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
    nullable: Optional[bool] = None
    parent: Optional[Any] = None

    _exclude_fields: ClassVar[Set[str]] = {'parent'}
    _pass_fields: ClassVar[Set[str]] = {'parent', 'data_type'}

    def __init__(self, **data: Any):  # type: ignore
        super().__init__(**data)  # type: ignore
        if isinstance(self.data_type, DataType) and self.data_type.reference:
            self.data_type.parent = self

    @property
    def type_hint(self) -> str:
        type_hint = self.data_type.type_hint

        if not type_hint:
            return OPTIONAL
        elif self.nullable is not None:
            if self.nullable:
                return f'{OPTIONAL}[{type_hint}]'
            return type_hint
        elif self.required:
            return type_hint
        return f'{OPTIONAL}[{type_hint}]'

    @property
    def imports(self) -> Tuple[Import, ...]:
        if self.nullable is None:
            if not self.required:
                return chain_as_tuple(self.data_type.all_imports, (IMPORT_OPTIONAL,))
        elif self.nullable:
            return chain_as_tuple(self.data_type.all_imports, (IMPORT_OPTIONAL,))
        return tuple(self.data_type.all_imports)

    @property
    def unresolved_types(self) -> FrozenSet[str]:
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


class DataModel(TemplateBase, ABC):
    TEMPLATE_FILE_PATH: str = ''
    BASE_CLASS: str = ''

    def __init__(
        self,
        *,
        reference: Reference,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[Reference]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
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

        self.fields: List[DataModelFieldBase] = fields or []
        self.decorators: List[str] = decorators or []
        self._additional_imports: List[Import] = []
        self.base_classes: List[Reference] = [
            base_class for base_class in base_classes or [] if base_class
        ]
        self.custom_base_class = custom_base_class
        self.file_path: Optional[Path] = path
        self.reference: Reference = reference

        self.reference.source = self

        self.extra_template_data = (
            extra_template_data[self.name]
            if extra_template_data is not None
            else defaultdict(dict)
        )

        if not self.base_classes:
            base_class_full_path = custom_base_class or self.BASE_CLASS
            if base_class_full_path:
                self._additional_imports.append(
                    Import.from_full_path(base_class_full_path)
                )

        if extra_template_data:
            all_model_extra_template_data = extra_template_data.get(ALL_MODEL)
            if all_model_extra_template_data:
                self.extra_template_data.update(all_model_extra_template_data)

        self.methods: List[str] = methods or []

        self.description = description
        for field in self.fields:
            field.parent = self

        super().__init__(template_file_path=template_file_path)

    @property
    def imports(self) -> Tuple[Import, ...]:
        return chain_as_tuple(
            (i for f in self.fields for i in f.imports), self._additional_imports
        )

    @property
    def reference_classes(self) -> FrozenSet[str]:
        return frozenset(
            {r.path for r in self.base_classes if r.name != self.BASE_CLASS}
            | {t for f in self.fields for t in f.unresolved_types}
        )

    @property
    def name(self) -> str:
        return self.reference.name

    @property
    def base_class(self) -> str:
        if self.base_classes:
            base_class: str = ', '.join(b.name for b in self.base_classes)
        else:
            base_class_full_path = self.custom_base_class or self.BASE_CLASS
            base_class = base_class_full_path.rsplit('.', 1)[-1]

        if '.' in self.name:
            module, class_name = self.name.rsplit('.', 1)
            prefix = f'{module}.'
            if base_class.startswith(prefix):
                base_class = base_class.replace(prefix, '', 1)
        return base_class

    @property
    def class_name(self) -> str:
        if '.' in self.name:
            return self.name.rsplit('.', 1)[-1]
        return self.name

    @property
    def module_path(self) -> List[str]:
        if self.file_path:
            return [
                *self.file_path.parts[:-1],
                self.file_path.stem,
                *self.name.split('.')[:-1],
            ]
        return self.name.split('.')[:-1]

    @property
    def all_data_types(self) -> Iterator['DataType']:
        for field in self.fields:
            yield from field.data_type.all_data_types

    @cached_property
    def path(self) -> str:
        return self.reference.path

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
