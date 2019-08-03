from typing import List, Optional

from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.model.pydantic.base_model import type_map


class DataClass(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/dataclass.jinja2'
    FROM_ = 'pydantic.dataclasses'
    IMPORT_ = 'pydantic.dataclasses.dataclass'
    DATA_TYPE_MAP = type_map

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
    ):
        super().__init__(name, fields, decorators)
