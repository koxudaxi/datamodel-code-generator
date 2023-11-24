from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, DefaultDict, Dict, List, Optional, Tuple

from datamodel_code_generator.imports import IMPORT_TYPE_ALIAS, IMPORT_UNION, Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.reference import Reference


class DataTypeUnion(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'Union.jinja2'
    BASE_CLASS: ClassVar[str] = ''
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (
        IMPORT_TYPE_ALIAS,
        IMPORT_UNION,
    )

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
