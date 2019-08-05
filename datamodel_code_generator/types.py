from enum import Enum, auto
from typing import Any, DefaultDict, Dict, List, Optional, Set, Union

from pydantic import BaseModel


class Import(BaseModel):
    from_: Optional[str] = None
    import_: str

    @classmethod
    def from_full_path(cls, class_path: str) -> 'Import':
        split_class_path: List[str] = class_path.split('.')
        return Import(
            from_='.'.join(split_class_path[:-1]) or None, import_=split_class_path[-1]
        )


class Imports(DefaultDict[Optional[str], Set[str]]):
    def __init__(self) -> None:
        super().__init__(set)

    @classmethod
    def create_line(cls, from_: Optional[str], imports: Set[str]) -> str:
        line: str = ''
        if from_:  # pragma: no cover
            line = f'from {from_} '
        line += f"import {', '.join(sorted(imports))}"
        return line

    def dump(self) -> str:
        return '\n'.join(
            self.create_line(from_, imports) for from_, imports in self.items()
        )

    def append(self, imports: Union[Import, List[Import], None]) -> None:
        if imports:
            if isinstance(imports, Import):
                imports = [imports]
            for import_ in imports:
                self[import_.from_].add(import_.import_)


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
