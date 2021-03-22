from typing import Any, ClassVar, Optional, Tuple

from datamodel_code_generator.imports import IMPORT_ANY, IMPORT_ENUM, Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.types import DataType, Types


class Enum(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'Enum.jinja2'
    BASE_CLASS: ClassVar[str] = 'enum.Enum'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_ENUM,)

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError

    def get_member(self, field: DataModelFieldBase) -> 'Member':
        return Member(self, field)

    def find_member(self, value: Any) -> Optional['Member']:
        repr_value = repr(value)
        for field in self.fields:  # pragma: no cover
            if field.default == repr_value:
                return self.get_member(field)
        return None  # pragma: no cover

    @property
    def imports(self) -> Tuple[Import, ...]:
        return tuple(i for i in super().imports if i != IMPORT_ANY)


class Member:
    def __init__(self, enum: Enum, field: DataModelFieldBase) -> None:
        self.enum: Enum = enum
        self.field: DataModelFieldBase = field

    def __repr__(self) -> str:
        return f'{self.enum.name}.{self.field.name}'
