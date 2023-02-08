from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, DefaultDict, Dict, List, Optional, Tuple

from datamodel_code_generator.imports import IMPORT_ANY, IMPORT_ENUM, Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED, BaseClassDataType
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, Types

_INT: str = 'int'
_FLOAT: str = 'float'
_BYTES: str = 'bytes'
_STR: str = 'str'

SUBCLASS_BASE_CLASSES: Dict[Types, str] = {
    Types.int32: _INT,
    Types.int64: _INT,
    Types.integer: _INT,
    Types.float: _FLOAT,
    Types.double: _FLOAT,
    Types.number: _FLOAT,
    Types.byte: _BYTES,
    Types.string: _STR,
}


class Enum(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'Enum.jinja2'
    BASE_CLASS: ClassVar[str] = 'enum.Enum'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_ENUM,)

    def __init__(
        self,
        *,
        reference: Reference,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[Reference]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        methods: Optional[List[str]] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
        type_: Optional[Types] = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
    ):
        super().__init__(
            reference=reference,
            fields=fields,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            methods=methods,
            path=path,
            description=description,
            default=default,
            nullable=nullable,
        )

        if not base_classes and type_:
            base_class = SUBCLASS_BASE_CLASSES.get(type_)
            if base_class:
                self.base_classes: List[BaseClassDataType] = [
                    BaseClassDataType(type=base_class),
                    *self.base_classes,
                ]

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError

    def get_member(self, field: DataModelFieldBase) -> Member:
        return Member(self, field)

    def find_member(self, value: Any) -> Optional[Member]:
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
        self.alias: Optional[str] = None

    def __repr__(self) -> str:
        return f'{self.alias or self.enum.name}.{self.field.name}'
