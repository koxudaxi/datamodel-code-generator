import re
from abc import ABC, abstractmethod
from enum import Enum, auto
from functools import lru_cache
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import pydantic
from packaging import version
from pydantic import (
    StrictBool,
    StrictInt,
    StrictStr,
    create_model,
)

from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.imports import (
    IMPORT_ABC_MAPPING,
    IMPORT_ABC_SEQUENCE,
    IMPORT_ABC_SET,
    IMPORT_DICT,
    IMPORT_FROZEN_SET,
    IMPORT_LIST,
    IMPORT_LITERAL,
    IMPORT_LITERAL_BACKPORT,
    IMPORT_MAPPING,
    IMPORT_OPTIONAL,
    IMPORT_SEQUENCE,
    IMPORT_SET,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.reference import Reference, _BaseModel
from datamodel_code_generator.util import (
    PYDANTIC_V2,
    ConfigDict,
    Protocol,
    runtime_checkable,
)

if PYDANTIC_V2:
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import core_schema

T = TypeVar('T')

OPTIONAL = 'Optional'
OPTIONAL_PREFIX = f'{OPTIONAL}['

UNION = 'Union'
UNION_PREFIX = f'{UNION}['
UNION_DELIMITER = ', '
UNION_PATTERN: Pattern[str] = re.compile(r'\s*,\s*')
UNION_OPERATOR_DELIMITER = ' | '
UNION_OPERATOR_PATTERN: Pattern[str] = re.compile(r'\s*\|\s*')
NONE = 'None'
ANY = 'Any'
LITERAL = 'Literal'
SEQUENCE = 'Sequence'
FROZEN_SET = 'FrozenSet'
MAPPING = 'Mapping'
DICT = 'Dict'
SET = 'Set'
LIST = 'List'
STANDARD_DICT = 'dict'
STANDARD_LIST = 'list'
STANDARD_SET = 'set'
STR = 'str'

NOT_REQUIRED = 'NotRequired'
NOT_REQUIRED_PREFIX = f'{NOT_REQUIRED}['


class StrictTypes(Enum):
    str = 'str'
    bytes = 'bytes'
    int = 'int'
    float = 'float'
    bool = 'bool'


class UnionIntFloat:
    def __init__(self, value: Union[int, float]) -> None:
        self.value: Union[int, float] = value

    def __int__(self) -> int:
        return int(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[Any], Any]]:
        yield cls.validate

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: 'GetCoreSchemaHandler'
    ) -> 'core_schema.CoreSchema':
        from_int_schema = core_schema.chain_schema(
            [
                core_schema.union_schema(
                    [core_schema.int_schema(), core_schema.float_schema()]
                ),
                core_schema.no_info_plain_validator_function(cls.validate),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_int_schema,
            python_schema=core_schema.union_schema(
                [
                    # check if it's an instance first before doing any further work
                    core_schema.is_instance_schema(UnionIntFloat),
                    from_int_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: instance.value
            ),
        )

    @classmethod
    def validate(cls, v: Any) -> 'UnionIntFloat':
        if isinstance(v, UnionIntFloat):
            return v
        elif not isinstance(v, (int, float)):  # pragma: no cover
            try:
                int(v)
                return cls(v)
            except (TypeError, ValueError):
                pass
            try:
                float(v)
                return cls(v)
            except (TypeError, ValueError):
                pass

            raise TypeError(f'{v} is not int or float')
        return cls(v)


def chain_as_tuple(*iterables: Iterable[T]) -> Tuple[T, ...]:
    return tuple(chain(*iterables))


@lru_cache()
def _remove_none_from_type(
    type_: str, split_pattern: Pattern[str], delimiter: str
) -> List[str]:
    types: List[str] = []
    split_type: str = ''
    inner_count: int = 0
    for part in re.split(split_pattern, type_):
        if part == NONE:
            continue
        inner_count += part.count('[') - part.count(']')
        if split_type:
            split_type += delimiter
        if inner_count == 0:
            if split_type:
                types.append(f'{split_type}{part}')
            else:
                types.append(part)
            split_type = ''
            continue
        else:
            split_type += part
    return types


def _remove_none_from_union(type_: str, use_union_operator: bool) -> str:
    if use_union_operator:
        if not re.match(r'^\w+ | ', type_):
            return type_
        return UNION_OPERATOR_DELIMITER.join(
            _remove_none_from_type(
                type_, UNION_OPERATOR_PATTERN, UNION_OPERATOR_DELIMITER
            )
        )

    if not type_.startswith(UNION_PREFIX):
        return type_
    inner_types = _remove_none_from_type(
        type_[len(UNION_PREFIX) :][:-1], UNION_PATTERN, UNION_DELIMITER
    )

    if len(inner_types) == 1:
        return inner_types[0]
    return f'{UNION_PREFIX}{UNION_DELIMITER.join(inner_types)}]'


@lru_cache()
def get_optional_type(type_: str, use_union_operator: bool) -> str:
    type_ = _remove_none_from_union(type_, use_union_operator)

    if not type_ or type_ == NONE:
        return NONE
    if use_union_operator:
        return f'{type_} | {NONE}'
    return f'{OPTIONAL_PREFIX}{type_}]'


@runtime_checkable
class Modular(Protocol):
    @property
    def module_name(self) -> str:
        raise NotImplementedError


@runtime_checkable
class Nullable(Protocol):
    @property
    def nullable(self) -> bool:
        raise NotImplementedError


class DataType(_BaseModel):
    if PYDANTIC_V2:
        # TODO[pydantic]: The following keys were removed: `copy_on_model_validation`.
        # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
        model_config = ConfigDict(
            extra='forbid',
            revalidate_instances='never',
        )
    else:
        if not TYPE_CHECKING:

            @classmethod
            def model_rebuild(cls) -> None:
                cls.update_forward_refs()

        class Config:
            extra = 'forbid'
            copy_on_model_validation = (
                False
                if version.parse(pydantic.VERSION) < version.parse('1.9.2')
                else 'none'
            )

    type: Optional[str] = None
    reference: Optional[Reference] = None
    data_types: List['DataType'] = []
    is_func: bool = False
    kwargs: Optional[Dict[str, Any]] = None
    import_: Optional[Import] = None
    python_version: PythonVersion = PythonVersion.PY_37
    is_optional: bool = False
    is_dict: bool = False
    is_list: bool = False
    is_set: bool = False
    is_custom_type: bool = False
    literals: List[Union[StrictBool, StrictInt, StrictStr]] = []
    use_standard_collections: bool = False
    use_generic_container: bool = False
    use_union_operator: bool = False
    alias: Optional[str] = None
    parent: Optional[Any] = None
    children: List[Any] = []
    strict: bool = False
    dict_key: Optional['DataType'] = None

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
        is_set: bool = False,
        is_custom_type: bool = False,
        strict: bool = False,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> 'DataTypeT':
        return cls(
            type=import_.import_,
            import_=import_,
            is_optional=is_optional,
            is_dict=is_dict,
            is_list=is_list,
            is_set=is_set,
            is_func=True if kwargs else False,
            is_custom_type=is_custom_type,
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

    def replace_reference(self, reference: Optional[Reference]) -> None:
        if not self.reference:  # pragma: no cover
            raise Exception(
                f"`{self.__class__.__name__}.replace_reference()` can't be called"
                f' when `reference` field is empty.'
            )
        self_id = id(self)
        self.reference.children = [
            c for c in self.reference.children if id(c) != self_id
        ]
        self.reference = reference
        if reference:
            reference.children.append(self)

    def remove_reference(self) -> None:
        self.replace_reference(None)

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
            (self.is_optional and not self.use_union_operator, IMPORT_OPTIONAL),
            (len(self.data_types) > 1 and not self.use_union_operator, IMPORT_UNION),
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
                    (self.is_set, IMPORT_ABC_SET),
                    (self.is_dict, IMPORT_ABC_MAPPING),
                )
            else:
                imports = (
                    *imports,
                    (self.is_list, IMPORT_SEQUENCE),
                    (self.is_set, IMPORT_FROZEN_SET),
                    (self.is_dict, IMPORT_MAPPING),
                )
        elif not self.use_standard_collections:
            imports = (
                *imports,
                (self.is_list, IMPORT_LIST),
                (self.is_set, IMPORT_SET),
                (self.is_dict, IMPORT_DICT),
            )
        for field, import_ in imports:
            if field and import_ != self.import_:
                yield import_

        if self.dict_key:
            yield from self.dict_key.imports

    def __init__(self, **values: Any) -> None:
        if not TYPE_CHECKING:
            super().__init__(**values)

        for type_ in self.data_types:
            if type_.type == ANY and type_.is_optional:
                if any(t for t in self.data_types if t.type != ANY):  # pragma: no cover
                    self.is_optional = True
                    self.data_types = [
                        t
                        for t in self.data_types
                        if not (t.type == ANY and t.is_optional)
                    ]
                break  # pragma: no cover

        for data_type in self.data_types:
            if data_type.reference or data_type.data_types:
                data_type.parent = self

        if self.reference:
            self.reference.children.append(self)

    @property
    def type_hint(self) -> str:
        type_: Optional[str] = self.alias or self.type
        if not type_:
            if self.is_union:
                data_types: List[str] = []
                for data_type in self.data_types:
                    data_type_type = data_type.type_hint
                    if data_type_type in data_types:  # pragma: no cover
                        continue

                    if NONE == data_type_type:
                        self.is_optional = True
                        continue

                    non_optional_data_type_type = _remove_none_from_union(
                        data_type_type, self.use_union_operator
                    )

                    if non_optional_data_type_type != data_type_type:
                        self.is_optional = True

                    data_types.append(non_optional_data_type_type)
                if len(data_types) == 1:
                    type_ = data_types[0]
                else:
                    if self.use_union_operator:
                        type_ = UNION_OPERATOR_DELIMITER.join(data_types)
                    else:
                        type_ = f'{UNION_PREFIX}{UNION_DELIMITER.join(data_types)}]'
            elif len(self.data_types) == 1:
                type_ = self.data_types[0].type_hint
            elif self.literals:
                type_ = f"{LITERAL}[{', '.join(repr(literal) for literal in self.literals)}]"
            else:
                if self.reference:
                    type_ = self.reference.short_name
                else:
                    # TODO support strict Any
                    # type_ = 'Any'
                    type_ = ''
        if self.reference:
            source = self.reference.source
            if isinstance(source, Nullable) and source.nullable:
                self.is_optional = True
        if self.reference and self.python_version == PythonVersion.PY_36:
            type_ = f"'{type_}'"
        if self.is_list:
            if self.use_generic_container:
                list_ = SEQUENCE
            elif self.use_standard_collections:
                list_ = STANDARD_LIST
            else:
                list_ = LIST
            type_ = f'{list_}[{type_}]' if type_ else list_
        elif self.is_set:
            if self.use_generic_container:
                set_ = FROZEN_SET
            elif self.use_standard_collections:
                set_ = STANDARD_SET
            else:
                set_ = SET
            type_ = f'{set_}[{type_}]' if type_ else set_
        elif self.is_dict:
            if self.use_generic_container:
                dict_ = MAPPING
            elif self.use_standard_collections:
                dict_ = STANDARD_DICT
            else:
                dict_ = DICT
            if self.dict_key or type_:
                key = self.dict_key.type_hint if self.dict_key else STR
                type_ = f'{dict_}[{key}, {type_ or ANY}]'
            else:  # pragma: no cover
                type_ = dict_
        if self.is_optional and type_ != ANY:
            return get_optional_type(type_, self.use_union_operator)
        elif self.is_func:
            if self.kwargs:
                kwargs: str = ', '.join(f'{k}={v}' for k, v in self.kwargs.items())
                return f'{type_}({kwargs})'
            return f'{type_}()'
        return type_

    @property
    def is_union(self) -> bool:
        return len(self.data_types) > 1


DataType.model_rebuild()

DataTypeT = TypeVar('DataTypeT', bound=DataType)


class EmptyDataType(DataType):
    pass


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
    ipv4_network = auto()
    ipv6 = auto()
    ipv6_network = auto()
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
        use_non_positive_negative_number_constrained_types: bool = False,
        use_union_operator: bool = False,
    ) -> None:
        self.python_version = python_version
        self.use_standard_collections: bool = use_standard_collections
        self.use_generic_container_types: bool = use_generic_container_types
        self.strict_types: Sequence[StrictTypes] = strict_types or ()
        self.use_non_positive_negative_number_constrained_types: bool = (
            use_non_positive_negative_number_constrained_types
        )
        self.use_union_operator: bool = use_union_operator

        if (
            use_generic_container_types and python_version == PythonVersion.PY_36
        ):  # pragma: no cover
            raise Exception(
                'use_generic_container_types can not be used with target_python_version 3.6.\n'
                ' The version will be not supported in a future version'
            )

        if TYPE_CHECKING:
            self.data_type: Type[DataType]
        else:
            self.data_type: Type[DataType] = create_model(
                'ContextDataType',
                python_version=(PythonVersion, python_version),
                use_standard_collections=(bool, use_standard_collections),
                use_generic_container=(bool, use_generic_container_types),
                use_union_operator=(bool, use_union_operator),
                __base__=DataType,
            )

    @abstractmethod
    def get_data_type(self, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError

    def get_data_type_from_full_path(
        self, full_path: str, is_custom_type: bool
    ) -> DataType:
        return self.data_type.from_import(
            Import.from_full_path(full_path), is_custom_type=is_custom_type
        )

    def get_data_type_from_value(self, value: Any) -> DataType:
        type_: Optional[Types] = None
        if isinstance(value, str):
            type_ = Types.string
        elif isinstance(value, bool):
            type_ = Types.boolean
        elif isinstance(value, int):
            type_ = Types.integer
        elif isinstance(value, float):
            type_ = Types.float
        elif isinstance(value, dict):
            return self.data_type.from_import(IMPORT_DICT)
        elif isinstance(value, list):
            return self.data_type.from_import(IMPORT_LIST)
        else:
            type_ = Types.any
        return self.get_data_type(type_)
