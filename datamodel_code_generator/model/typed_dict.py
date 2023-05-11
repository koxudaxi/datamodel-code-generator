from __future__ import annotations

import keyword
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
)

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.improts import (
    IMPORT_FIELD,
    IMPORT_TYPED_DICT,
)
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import chain_as_tuple


def _is_valid_field_name(field: DataModelFieldBase) -> bool:
    name = field.original_name or field.name
    if name is None:  # pragma: no cover
        return False
    return name.isidentifier() and not keyword.iskeyword(name)


class TypedDict(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'TypedDict.jinja2'
    BASE_CLASS: ClassVar[str] = 'typing.TypedDict'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_TYPED_DICT,)

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
        default: Any = UNDEFINED,
        nullable: bool = False,
    ) -> None:
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

    @property
    def imports(self) -> Tuple[Import, ...]:
        if any(f for f in self.fields if f.field):
            return chain_as_tuple(super().imports, (IMPORT_FIELD,))
        return super().imports

    @property
    def is_functional_syntax(self) -> bool:
        return any(not _is_valid_field_name(f) for f in self.fields)

    @property
    def has_non_required_field(self) -> bool:
        return any(not f.required for f in self.fields)

    @property
    def all_keys(self) -> Iterator[DataModelFieldBase]:
        for base_class in self.base_classes:
            if base_class.reference is None:  # pragma: no cover
                continue
            data_model = base_class.reference.source
            if not isinstance(data_model, DataModel):
                continue

            if isinstance(data_model, TypedDict):
                yield from data_model.all_keys
            else:
                for field in data_model.fields:
                    yield field
        for field in self.fields:
            yield field


class DataModelField(DataModelFieldBase):
    @property
    def field(self) -> Optional[str]:
        """for backwards compatibility"""
        return None

    def __str__(self) -> str:
        return ''
