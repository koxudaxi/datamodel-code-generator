from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Set, Union

from pydantic import BaseModel


class Import(BaseModel):
    from_: Optional[str] = None
    import_: str
    alias: Optional[str]

    @classmethod
    def from_full_path(cls, class_path: str) -> 'Import':
        split_class_path: List[str] = class_path.split('.')
        return Import(
            from_='.'.join(split_class_path[:-1]) or None, import_=split_class_path[-1]
        )


class Imports(DefaultDict[Optional[str], Set[str]]):
    def __str__(self) -> str:
        return self.dump()

    def __init__(self) -> None:
        super().__init__(set)
        self.alias: DefaultDict[Optional[str], Dict[str, str]] = defaultdict(dict)

    def _set_alias(self, from_: Optional[str], imports: Set[str]) -> List[str]:
        return [
            f'{i} as {self.alias[from_][i]}' if i in self.alias[from_] else i
            for i in sorted(imports)
        ]

    def create_line(self, from_: Optional[str], imports: Set[str]) -> str:
        if from_:
            line = f'from {from_} '
            line += f"import {', '.join(self._set_alias(from_, imports))}"
            return line
        return '\n'.join(f'import {i}' for i in self._set_alias(from_, imports))

    def dump(self) -> str:
        return '\n'.join(
            self.create_line(from_, imports) for from_, imports in self.items()
        )

    def append(self, imports: Union[Import, List[Import], None]) -> None:
        if imports:
            if isinstance(imports, Import):
                imports = [imports]
            for import_ in imports:
                if import_.import_.count('.') >= 1:
                    self[None].add(import_.import_)
                else:
                    self[import_.from_].add(import_.import_)
                    if import_.alias:
                        self.alias[import_.from_][import_.import_] = import_.alias


IMPORT_ANY = Import.from_full_path('typing.Any')
IMPORT_LIST = Import.from_full_path('typing.List')
IMPORT_UNION = Import.from_full_path('typing.Union')
IMPORT_OPTIONAL = Import.from_full_path('typing.Optional')
IMPORT_ENUM = Import.from_full_path('enum.Enum')
IMPORT_ANNOTATIONS = Import.from_full_path('__future__.annotations')
IMPORT_DICT = Import.from_full_path('typing.Dict')
IMPORT_DECIMAL = Import.from_full_path('decimal.Decimal')
IMPORT_DATE = Import.from_full_path('datetime.date')
IMPORT_DATETIME = Import.from_full_path('datetime.datetime')
IMPORT_UUID = Import.from_full_path('uuid.UUID')
