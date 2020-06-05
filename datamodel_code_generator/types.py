from enum import Enum, auto
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.imports import Import


class DataType(BaseModel):
    type: str
    is_func: bool = False
    kwargs: Optional[Dict[str, Any]]
    imports_: Optional[List[Import]]
    python_version: PythonVersion = PythonVersion.PY_37
    unresolved_types: List[str] = []
    ref: bool = False
    version_compatible: bool = False

    @property
    def type_hint(self) -> str:
        if self.is_func:
            if self.kwargs:
                kwargs: str = ', '.join(f'{k}={v}' for k, v in self.kwargs.items())
                return f'{self.get_type()}({kwargs})'
            return f'{self.get_type()}()'
        return self.get_type()

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)
        if self.ref:
            self.unresolved_types.append(self.type)

    def _get_version_compatible_name(self) -> str:
        if self.version_compatible:
            if self.python_version == PythonVersion.PY_36:
                return f"'{self.type}'"
        return self.type

    def get_type(self) -> str:
        return self._get_version_compatible_name()


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
