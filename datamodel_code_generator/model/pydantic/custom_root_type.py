from typing import List, Optional, Type

from datamodel_code_generator.model.base import DataModel, DataModelField


class CustomRootType(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel_root.jinja2'
    BASE_CLASS = 'BaseModel'

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
    ):
        super().__init__(name, fields=fields, decorators=decorators)
