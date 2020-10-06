from enum import Enum, auto
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.imports import (
    IMPORT_DICT,
    IMPORT_LIST,
    IMPORT_OPTIONAL,
    IMPORT_UNION,
    Import,
)


class DataType(BaseModel):
    type: Optional[str]
    data_types: List['DataType'] = []
    is_func: bool = False
    kwargs: Optional[Dict[str, Any]]
    imports_: List[Import] = []
    python_version: PythonVersion = PythonVersion.PY_37
    unresolved_types: List[str] = []
    ref: bool = False
    is_optional: bool = False
    is_dict: bool = False
    is_list: bool = False

    @property
    def type_hint(self) -> str:
        return self.get_type()

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)
        if self.ref and self.type:
            self.unresolved_types.append(self.type)
        for field, import_ in (
            (self.is_list, IMPORT_LIST),
            (self.is_dict, IMPORT_DICT),
            (self.is_optional, IMPORT_OPTIONAL),
            (len(self.data_types) > 1, IMPORT_UNION),
        ):
            if field and import_ not in self.imports_:
                self.imports_.append(import_)
        for data_type in self.data_types:
            self.imports_.extend(data_type.imports_)

    def get_type(self, as_string: Optional[bool] = None) -> str:
        if self.is_func:
            if self.kwargs:
                kwargs: str = ', '.join(f'{k}={v}' for k, v in self.kwargs.items())
                return f'{self.get_raw_type()}({kwargs})'
            return f'{self.get_raw_type(as_string)}()'
        return self.get_raw_type(as_string)

    def get_raw_type(self, as_string: Optional[bool] = None) -> str:
        if self.type:
            type_: str = self.type
        else:
            types: List[str] = [
                data_type.get_type(as_string=False) for data_type in self.data_types
            ]
            if len(types) > 1:  # pragma: no cover
                type_ = f"Union[{', '.join(types)}]"
            else:
                type_ = types[0]
        if self.is_list:
            type_ = f'List[{type_}]'
        if self.is_dict:
            type_ = f'Dict[str, {type_}]'
        if self.is_optional:
            type_ = f'Optional[{type_}]'
        if as_string or (
            as_string is None and self.python_version == PythonVersion.PY_36
        ):
            return f"'{type_}'"
        return type_


DataType.update_forward_refs()


class DataTypePy36(DataType):
    python_version: PythonVersion = PythonVersion.PY_36


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
