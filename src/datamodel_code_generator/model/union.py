from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, DefaultDict, Dict, List, Tuple

from datamodel_code_generator.imports import IMPORT_TYPE_ALIAS, IMPORT_UNION, Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.reference import Reference

if TYPE_CHECKING:
    from pathlib import Path


class DataTypeUnion(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "Union.jinja2"
    BASE_CLASS: ClassVar[str] = ""
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (
        IMPORT_TYPE_ALIAS,
        IMPORT_UNION,
    )

    def __init__(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: List[DataModelFieldBase],
        decorators: List[str] | None = None,
        base_classes: List[Reference] | None = None,
        custom_base_class: str | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: DefaultDict[str, Dict[str, Any]] | None = None,
        methods: List[str] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
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
            keyword_only=keyword_only,
        )
