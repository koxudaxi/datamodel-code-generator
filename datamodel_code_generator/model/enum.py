from typing import Any, List, Optional

from datamodel_code_generator.imports import IMPORT_ENUM
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.types import DataType, Types


class Enum(DataModel):
    TEMPLATE_FILE_PATH = 'Enum.jinja2'
    BASE_CLASS = 'enum.Enum'

    def __init__(
        self,
        name: str,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
    ):
        super().__init__(
            name=name, fields=fields, decorators=decorators, auto_import=False
        )
        self.imports.append(IMPORT_ENUM)

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError
