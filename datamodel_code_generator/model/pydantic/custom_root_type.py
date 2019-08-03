from typing import List, Optional

from datamodel_code_generator.model.base import DataModel, DataModelField
from datamodel_code_generator.model.pydantic.base_model import type_map
from datamodel_code_generator.types import Types


class CustomRootType(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel_root.jinja2'
    BASE_CLASS = 'BaseModel'
    FROM_ = 'pydantic'
    IMPORT_ = 'BaseModel'
    DATA_TYPE_MAP = type_map

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
    ):
        super().__init__(name, fields=fields, decorators=decorators)
