from pathlib import Path
from typing import Any, List, Mapping, Optional

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.model.pydantic.types import get_data_type, type_map
from datamodel_code_generator.types import DataType, Types


class DataClass(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/dataclass.jinja2'

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[str]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[Mapping[str, Any]] = None,
        auto_import: bool = True,
        reference_classes: Optional[List[str]] = None,
    ):

        super().__init__(
            name,
            fields,
            decorators,
            base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            auto_import=auto_import,
            reference_classes=reference_classes,
        )
        self.imports.append(Import.from_full_path('pydantic.dataclasses.dataclass'))

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        return get_data_type(types, **kwargs)
