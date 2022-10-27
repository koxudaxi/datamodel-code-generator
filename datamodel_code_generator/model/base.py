from abc import ABC, abstractmethod
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import (
    TYPE_CHECKING,
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
    Union,
)

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel

from datamodel_code_generator import cached_property
from datamodel_code_generator.imports import IMPORT_ANNOTATED, IMPORT_OPTIONAL, Import
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
    data_type: DataType
    constraints: Any = None
    strip_default_none: bool = False
    nullable: Optional[bool] = None
    parent: Optional[Any] = None
    extras: Dict[str, Any] = {}
    use_annotated: bool = False
    has_default: bool = False
    _exclude_fields: ClassVar[Set[str]] = {'parent'}
    _pass_fields: ClassVar[Set[str]] = {'parent', 'data_type'}

    if not TYPE_CHECKING:

        def __init__(self, **data: Any):
            super().__init__(**data)
            if self.data_type.reference or self.data_type.data_types:
                self.data_type.parent = self

    @property
    def type_hint(self) -> str:
        type_hint = self.data_type.type_hint

        if not type_hint:
            return OPTIONAL
        elif self.nullable is not None:
            if self.nullable:
                if self.data_type.use_union_operator:
                    return f'{type_hint} | None'
                else:
                    return f'{OPTIONAL}[{type_hint}]'
            return type_hint
        elif self.required:
            return type_hint
        if self.data_type.use_union_operator:
            return f'{type_hint} | None'
        else:
            return f'{OPTIONAL}[{type_hint}]'

    @property
    def imports(self) -> Tuple[Import, ...]:
        imports: List[Union[Tuple[Import], Iterator[Import]]] = [
            self.data_type.all_imports
        ]
        if (
            self.nullable or (self.nullable is None and not self.required)
        ) and not self.data_type.use_union_operator:
            imports.append((IMPORT_OPTIONAL,))
        if self.use_annotated:
            imports.append((IMPORT_ANNOTATED,))
        return chain_as_tuple(*imports)

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

    @property
    def represented_default(self) -> str:
        return repr(self.default)

    @property
    def annotated(self) -> Optional[str]:
        return None


@lru_cache()
def get_template(template_file_path: Path) -> Template:
    loader = FileSystemLoader(str(TEMPLATE_DIR / template_file_path.parent))
    environment: Environment = Environment(loader=loader)
    return environment.get_template(template_file_path.name)


def get_module_path(name: str, file_path: Optional[Path]) -> List[str]:
    if file_path:
        return [
            *file_path.parts[:-1],
            file_path.stem,
            *name.split('.')[:-1],
        ]
    return name.split('.')[:-1]


def get_module_name(name: str, file_path: Optional[Path]) -> str:
    return '.'.join(get_module_path(name, file_path))


class TemplateBase(ABC):
    @property
    @abstractmethod
    def template_file_path(self) -> Path:
        raise NotImplementedError

    @cached_property
    def template(self) -> Template:
        return get_template(self.template_file_path)

    @abstractmethod
    def render(self) -> str:
        raise NotImplementedError

    def _render(self, *args: Any, **kwargs: Any) -> str:
        return self.template.render(*args, **kwargs)

    def __str__(self) -> str:
        return self.render()


class BaseClassDataType(DataType):
    ...


UNDEFINED: Any = object()


class DataModel(TemplateBase, ABC):
    TEMPLATE_FILE_PATH: ClassVar[str] = ''
    BASE_CLASS: ClassVar[str] = ''
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = ()

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
        default: Any = UNDEFINED,
    ) -> None:
        if not self.TEMPLATE_FILE_PATH:
            raise Exception('TEMPLATE_FILE_PATH is undefined')

        template_file_path = Path(self.TEMPLATE_FILE_PATH)
        if custom_template_dir is not None:
            custom_template_file_path = custom_template_dir / template_file_path.name
            if custom_template_file_path.exists():
                template_file_path = custom_template_file_path
        self._template_file_path = template_file_path

        self.fields: List[DataModelFieldBase] = fields or []
        self.decorators: List[str] = decorators or []
        self._additional_imports: List[Import] = []
        self.custom_base_class = custom_base_class
        if base_classes:
            self.base_classes: List[BaseClassDataType] = [
                BaseClassDataType(reference=b) for b in base_classes
            ]
        else:
            self.set_base_class()

        self.file_path: Optional[Path] = path
        self.reference: Reference = reference

        self.reference.source = self

        self.extra_template_data = (
            extra_template_data[self.name]
            if extra_template_data is not None
            else defaultdict(dict)
        )

        for base_class in self.base_classes:
            if base_class.reference:
                base_class.reference.children.append(self)

        if extra_template_data:
            all_model_extra_template_data = extra_template_data.get(ALL_MODEL)
            if all_model_extra_template_data:
                self.extra_template_data.update(all_model_extra_template_data)

        self.methods: List[str] = methods or []

        self.description = description
        for field in self.fields:
            field.parent = self

        self._additional_imports.extend(self.DEFAULT_IMPORTS)
        self.default: Any = default

    def set_base_class(self) -> None:
        base_class_import = Import.from_full_path(
            self.custom_base_class or self.BASE_CLASS
        )
        self._additional_imports.append(base_class_import)
        self.base_classes = [BaseClassDataType.from_import(base_class_import)]

    @property
    def template_file_path(self) -> Path:
        return self._template_file_path

    @property
    def imports(self) -> Tuple[Import, ...]:
        return chain_as_tuple(
            (i for f in self.fields for i in f.imports),
            self._additional_imports,
        )

    @property
    def reference_classes(self) -> FrozenSet[str]:
        return frozenset(
            {r.reference.path for r in self.base_classes if r.reference}
            | {t for f in self.fields for t in f.unresolved_types}
        )

    @property
    def name(self) -> str:
        return self.reference.name

    @property
    def base_class(self) -> str:
        return ', '.join(b.type_hint for b in self.base_classes)

    @property
    def class_name(self) -> str:
        if '.' in self.name:
            return self.name.rsplit('.', 1)[-1]
        return self.name

    @property
    def module_path(self) -> List[str]:
        return get_module_path(self.name, self.file_path)

    @property
    def module_name(self) -> str:
        return get_module_name(self.name, self.file_path)

    @property
    def all_data_types(self) -> Iterator['DataType']:
        for field in self.fields:
            yield from field.data_type.all_data_types
        yield from self.base_classes

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
