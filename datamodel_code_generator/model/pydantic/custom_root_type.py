from typing import Any, List, Optional

from datamodel_code_generator.model.base import DataModel, DataModelField
from datamodel_code_generator.model.pydantic.types import get_data_type
from datamodel_code_generator.types import DataType, Types


class CustomRootType(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel_root.jinja2'
    BASE_CLASS = 'pydantic.BaseModel'

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_class: Optional[str] = None,
    ):

        super().__init__(
            name, fields=fields, decorators=decorators, base_class=base_class
        )

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        return get_data_type(types, **kwargs)
