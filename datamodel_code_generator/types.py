from abc import ABC, abstractmethod
from enum import Enum, auto
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
)

from pydantic import create_model

from datamodel_code_generator import Protocol, runtime_checkable
from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.imports import (
    IMPORT_ABC_MAPPING,
    IMPORT_ABC_SEQUENCE,
    IMPORT_DICT,
    IMPORT_LIST,
    IMPORT_LITERAL,
    IMPORT_LITERAL_BACKPORT,
    IMPORT_MAPPING,
    IMPORT_OPTIONAL,
    IMPORT_SEQUENCE,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.reference import Reference, _BaseModel

T = TypeVar('T')


class StrictTypes(Enum):
    str = 'str'
    bytes = 'bytes'
    int = 'int'
    float = 'float'
    bool = 'bool'


def chain_as_tuple(*iterables: Iterable[T]) -> Tuple[T, ...]:
    return tuple(chain(*iterables))


@runtime_checkable
class Modular(Protocol):
    @property
    def module_name(self) -> str:
        raise NotImplementedError


class DataType(_BaseModel):
    type: Optional[str]
    reference: Optional[Reference]
    data_types: List['DataType'] = []
    is_func: bool = False
    kwargs: Optional[Dict[str, Any]]
    import_: Optional[Import] = None
    python_version: PythonVersion = PythonVersion.PY_37
    is_optional: bool = False
    is_dict: bool = False
    is_list: bool = False
    literals: List[str] = []
    use_standard_collections: bool = False
    use_generic_container: bool = False
    alias: Optional[str] = None
    parent: Optional[Any] = None
    children: List[Any] = []
    strict: bool = False

    _exclude_fields: ClassVar[Set[str]] = {'parent', 'children'}
    _pass_fields: ClassVar[Set[str]] = {'parent', 'children', 'data_types', 'reference'}

    @classmethod
    def from_import(
        cls: Type['DataTypeT'],
        import_: Import,
        *,
        is_optional: bool = False,
        is_dict: bool = False,
        is_list: bool = False,
        strict: bool = False,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> 'DataTypeT':
        return cls(
            type=import_.import_,
            import_=import_,
            is_optional=is_optional,
            is_dict=is_dict,
            is_list=is_list,
            is_func=True if kwargs else False,
            strict=strict,
            kwargs=kwargs,
        )

    @property
    def unresolved_types(self) -> FrozenSet[str]:
        return frozenset(
            {
                t.reference.path
                for data_types in self.data_types
                for t in data_types.all_data_types
                if t.reference
            }
            | ({self.reference.path} if self.reference else set())
        )

    def replace_reference(self, reference: Reference) -> None:
        if not self.reference:  # pragma: no cover
            raise Exception(
                f'`{self.__class__.__name__}.replace_reference()` can\'t be called'
                f' when `reference` field is empty.'
            )

        self.reference.children.remove(self)
        self.reference = reference
        reference.children.append(self)

    @property
    def module_name(self) -> Optional[str]:
        if self.reference and isinstance(self.reference.source, Modular):
            return self.reference.source.module_name
        return None  # pragma: no cover

    @property
    def full_name(self) -> str:
        module_name = self.module_name
        if module_name:
            return f'{module_name}.{self.reference.short_name}'  # type: ignore
        return self.reference.short_name  # type: ignore

    @property
    def all_data_types(self) -> Iterator['DataType']:
        for data_type in self.data_types:
            yield from data_type.all_data_types
        yield self

    @property
    def all_imports(self) -> Iterator[Import]:
        for data_type in self.data_types:
            yield from data_type.all_imports
        yield from self.imports

    @property
    def imports(self) -> Iterator[Import]:
        if self.import_:
            yield self.import_
        imports: Tuple[Tuple[bool, Import], ...] = (
            (self.is_optional, IMPORT_OPTIONAL),
            (len(self.data_types) > 1, IMPORT_UNION),
        )
        if any(self.literals):
            import_literal = (
                IMPORT_LITERAL
                if self.python_version.has_literal_type
                else IMPORT_LITERAL_BACKPORT
            )
            imports = (
                *imports,
                (any(self.literals), import_literal),
            )

        if self.use_generic_container:
            if self.use_standard_collections:
                imports = (
                    *imports,
                    (self.is_list, IMPORT_ABC_SEQUENCE),
                    (self.is_dict, IMPORT_ABC_MAPPING),
                )
            else:
                imports = (
                    *imports,
                    (self.is_list, IMPORT_SEQUENCE),
                    (self.is_dict, IMPORT_MAPPING),
                )
        elif not self.use_standard_collections:
            imports = (
                *imports,
                (self.is_list, IMPORT_LIST),
                (self.is_dict, IMPORT_DICT),
            )
        for field, import_ in imports:
            if field and import_ != self.import_:
                yield import_

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)  # type: ignore

        for type_ in self.data_types:
            if type_.type == 'Any' and type_.is_optional:
                if any(
                    t for t in self.data_types if t.type != 'Any'
                ):  # pragma: no cover
                    self.is_optional = True
                    self.data_types = [
                        t
                        for t in self.data_types
                        if not (t.type == 'Any' and t.is_optional)
                    ]
                break

        for data_type in self.data_types:
            if data_type.reference:
                data_type.parent = self

        if self.reference:
            self.reference.children.append(self)

    @property
    def type_hint(self) -> str:
        type_: Optional[str] = self.alias or self.type
        if not type_:
            if len(self.data_types) > 1:
                type_ = f"Union[{', '.join(data_type.type_hint for data_type in self.data_types)}]"
            elif len(self.data_types) == 1:
                type_ = self.data_types[0].type_hint
            elif self.literals:
                type_ = (
                    f"Literal[{', '.join(repr(literal) for literal in self.literals)}]"
                )
            else:
                if self.reference:
                    type_ = self.reference.short_name
                else:
                    # TODO support strict Any
                    # type_ = 'Any'
                    type_ = ''
        if self.reference and self.python_version == PythonVersion.PY_36:
            type_ = f"'{type_}'"
        if self.is_list:
            if self.use_generic_container:
                list_ = 'Sequence'
            elif self.use_standard_collections:
                list_ = 'list'
            else:
                list_ = 'List'
            type_ = f'{list_}[{type_}]' if type_ else list_
        elif self.is_dict:
            if self.use_generic_container:
                dict_ = 'Mapping'
            elif self.use_standard_collections:
                dict_ = 'dict'
            else:
                dict_ = 'Dict'
            type_ = f'{dict_}[str, {type_}]' if type_ else dict_
        if self.is_optional and type_ != 'Any':
            type_ = f'Optional[{type_}]'
        elif self.is_func:
            if self.kwargs:
                kwargs: str = ', '.join(f'{k}={v}' for k, v in self.kwargs.items())
                return f'{type_}({kwargs})'
            return f'{type_}()'
        return type_


DataType.update_forward_refs()

DataTypeT = TypeVar('DataTypeT', bound=DataType)


class Types(Enum):
    integer = auto()
    int32 = auto()
    int64 = auto()
    number = auto()
    float = auto()
    double = auto()
    decimal = auto()
    time = auto()
    string = auto()
    byte = auto()
    binary = auto()
    date = auto()
    date_time = auto()
    password = auto()
    email = auto()
    uuid = auto()
    uuid1 = auto()
    uuid2 = auto()
    uuid3 = auto()
    uuid4 = auto()
    uuid5 = auto()
    uri = auto()
    hostname = auto()
    ipv4 = auto()
    ipv6 = auto()
    boolean = auto()
    object = auto()
    null = auto()
    array = auto()
    any = auto()


class DataTypeManager(ABC):
    def __init__(
        self,
        python_version: PythonVersion = PythonVersion.PY_37,
        use_standard_collections: bool = False,
        use_generic_container_types: bool = False,
        strict_types: Optional[Sequence[StrictTypes]] = None,
    ) -> None:
        self.python_version = python_version
        self.use_standard_collections: bool = use_standard_collections
        self.use_generic_container_types: bool = use_generic_container_types
        self.strict_types: Sequence[StrictTypes] = strict_types or ()

        if (
            use_generic_container_types and python_version == PythonVersion.PY_36
        ):  # pragma: no cover
            raise Exception(
                "use_generic_container_types can not be used with target_python_version 3.6.\n"
                " The version will be not supported in a future version"
            )

        if TYPE_CHECKING:
            self.data_type: Type[DataType]
        else:
            self.data_type: Type[DataType] = create_model(
                'ContextDataType',
                python_version=python_version,
                use_standard_collections=use_standard_collections,
                use_generic_container=use_generic_container_types,
                __base__=DataType,
            )

    @abstractmethod
    def get_data_type(self, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError
