from enum import Enum, auto
from typing import Any, Dict, Optional

from datamodel_code_generator.imports import Import
from pydantic import BaseModel


class DataType(BaseModel):
    type: str
    is_func: bool = False
    kwargs: Optional[Dict[str, Any]]
    import_: Optional[Import]

    @property
    def type_hint(self) -> str:
        if self.is_func:
            if self.kwargs:
                kwargs: str = ', '.join(f'{k}={v}' for k, v in self.kwargs.items())
                return f'{self.type}({kwargs})'
            return f'{self.type}()'
        return self.type


class Types(Enum):
    integer = auto()
    int32 = auto()
    int64 = auto()
    number = auto()
    float = auto()
    double = auto()
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
    ipv4 = auto()
    ipv6 = auto()
    boolean = auto()
