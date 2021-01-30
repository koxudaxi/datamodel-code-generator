from pathlib import Path
from typing import Any, List, Optional

from datamodel_code_generator.imports import IMPORT_ENUM
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, Types


class Enum(DataModel):
    TEMPLATE_FILE_PATH = 'Enum.jinja2'
    BASE_CLASS = 'enum.Enum'

    def __init__(
        self,
        name: str,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
        reference: Optional[Reference] = None,
    ):
        super().__init__(
            name=name,
            fields=fields,
            decorators=decorators,
            auto_import=False,
            path=path,
            description=description,
            reference=reference,
        )
        self.imports.append(IMPORT_ENUM)

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


class Member:
    def __init__(self, enum: Enum, field: DataModelFieldBase) -> None:
        self.enum: Enum = enum
        self.field: DataModelFieldBase = field

    def __repr__(self) -> str:
        return f'{self.enum.name}.{self.field.name}'
