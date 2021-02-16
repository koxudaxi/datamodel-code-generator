from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Type

from pydantic import BaseModel

from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.imports import (
    IMPORT_ABC_MAPPING,
    IMPORT_ABC_SEQUENCE,
    IMPORT_DICT,
    IMPORT_LIST,
    IMPORT_LITERAL,
    IMPORT_MAPPING,
    IMPORT_OPTIONAL,
    IMPORT_SEQUENCE,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.reference import Reference


class DataType(BaseModel):
    type: Optional[str]
    reference: Optional[Reference]
    data_types: List['DataType'] = []
    is_func: bool = False
    kwargs: Optional[Dict[str, Any]]
    imports_: List[Import] = []
    python_version: PythonVersion = PythonVersion.PY_37
    unresolved_types: Set[str] = {*()}
    ref: bool = False
    is_optional: bool = False
    is_dict: bool = False
    is_list: bool = False
    literals: List[str] = []
    use_standard_collections: bool = False
    use_generic_container: bool = False
    alias: Optional[str] = None

    @classmethod
    def from_reference(cls, reference: Reference, is_list: bool = False) -> 'DataType':
        data_type = cls(type=reference.name, ref=True, is_list=is_list)
        data_type.reference = reference
        return data_type

    @classmethod
    def create_literal(cls, literals: List[str]) -> 'DataType':
        return cls(literals=literals)

    @property
    def module_name(self) -> Optional[str]:
        return self.reference.module_name if self.reference else None

    @property
    def full_name(self) -> str:
        module_name = self.module_name
        if module_name:
            return f'{module_name}.{self.type}'
        return self.type  # type: ignore

    @property
    def name(self) -> str:
        return self.type.rsplit('.', 1)[-1]  # type: ignore

    @property
    def all_data_types(self) -> Iterator['DataType']:
        for data_type in self.data_types:
            yield from data_type.all_data_types
        yield self

    def __init__(self, **values: Any) -> None:  # type: ignore
        super().__init__(**values)
        if self.type and (self.reference or self.ref):
            self.unresolved_types.add(self.type)
        for type_ in self.data_types:
            if type_.type == 'Any' and type_.is_optional:
                if any(t for t in self.data_types if t.type != 'Any'):
                    self.is_optional = True
                    self.data_types = [
                        t
                        for t in self.data_types
                        if not (t.type == 'Any' and t.is_optional)
                    ]
                break

        imports: Tuple[Tuple[bool, Import], ...] = (
            (self.is_optional, IMPORT_OPTIONAL),
            (len(self.data_types) > 1, IMPORT_UNION),
            (any(self.literals), IMPORT_LITERAL),
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
            if field and import_ not in self.imports_:
                self.imports_.append(import_)
        for data_type in self.data_types:
            self.imports_.extend(data_type.imports_)
            self.unresolved_types.update(data_type.unresolved_types)

    @property
    def type_hint(self) -> str:
        type_: Optional[str] = self.alias or self.type
        if type_:
            if (
                self.reference or self.ref
            ) and self.python_version == PythonVersion.PY_36:
                type_ = f"'{type_}'"
        else:
            if len(self.data_types) > 1:
                type_ = f"Union[{', '.join(data_type.type_hint for data_type in self.data_types)}]"
            elif len(self.data_types) == 1:
                type_ = self.data_types[0].type_hint
            elif self.literals:
                type_ = (
                    f"Literal[{', '.join(repr(literal) for literal in self.literals)}]"
                )
            else:
                # TODO support strict Any
                # type_ = 'Any'
                type_ = ''
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
            type_ = f'{dict_}[str, {type_}]' if type_ else 'dict_'
        if self.is_optional and type_ != 'Any':
            type_ = f'Optional[{type_}]'
        elif self.is_func:
            if self.kwargs:
                kwargs: str = ', '.join(f'{k}={v}' for k, v in self.kwargs.items())
                return f'{type_}({kwargs})'
            return f'{type_}()'
        return type_


DataType.update_forward_refs()


class DataTypePy36(DataType):
    python_version: PythonVersion = PythonVersion.PY_36


class DataTypeStandardCollections(DataType):
    use_standard_collections: bool = True


class DataTypeGenericContainer(DataType):
    use_generic_container: bool = True


class DataTypeGenericContainerStandardCollections(DataType):
    use_standard_collections: bool = True
    use_generic_container: bool = True


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
    ) -> None:
        self.python_version = python_version
        self.use_standard_collections: bool = use_standard_collections
        self.use_generic_container_types: bool = use_generic_container_types

        self.data_type: Type[DataType]
        if use_generic_container_types:
            if python_version == PythonVersion.PY_36:  # pragma: no cover
                raise Exception(
                    "use_generic_container_types can not be used with target_python_version 3.6.\n"
                    " The verison will be not supported in a future version"
                )
            if use_standard_collections:
                self.data_type = DataTypeGenericContainerStandardCollections
            else:
                self.data_type = DataTypeGenericContainer
        elif use_standard_collections:
            self.data_type = DataTypeStandardCollections
        elif python_version == PythonVersion.PY_36:
            self.data_type = DataTypePy36
        else:
            self.data_type = DataType

    @abstractmethod
    def get_data_type(self, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError
