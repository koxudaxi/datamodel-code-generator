from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Mapping, Optional, Union

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.model.pydantic.types import get_data_type
from datamodel_code_generator.types import DataType, Types
from pydantic import BaseModel as _BaseModel


class Config(_BaseModel):
    extra: Optional[str] = None


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel.jinja2'
    BASE_CLASS = 'pydantic.BaseModel'

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[str]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Any]] = None,
        auto_import: bool = True,
        reference_classes: Optional[List[str]] = None,
        imports: Optional[List[Import]] = None,
    ):

        super().__init__(
            name=name,
            fields=fields,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            auto_import=auto_import,
            reference_classes=reference_classes,
            imports=imports,
        )

        if 'additionalProperties' in self.extra_template_data:
            self.extra_template_data['config'] = Config(extra='Extra.allow')
            self.imports.append(Import(from_='pydantic', import_='Extra'))

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        return get_data_type(types, **kwargs)
