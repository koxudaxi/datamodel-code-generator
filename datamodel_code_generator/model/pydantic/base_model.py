from typing import List, Optional

from datamodel_code_generator.model import DataModel, DataModelField


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel.jinja2'
    BASE_CLASS = 'BaseModel'

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_class: Optional[str] = None
    ):
        super().__init__(name=name, fields=fields, decorators=decorators, base_class=base_class)
