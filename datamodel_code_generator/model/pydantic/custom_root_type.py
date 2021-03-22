from typing import ClassVar

from . import BaseModel


class CustomRootType(BaseModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'pydantic/BaseModel_root.jinja2'
    BASE_CLASS: ClassVar[str] = 'pydantic.BaseModel'
