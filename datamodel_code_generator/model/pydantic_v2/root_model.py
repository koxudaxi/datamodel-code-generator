from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.model.pydantic_v2.base_model import BaseModel


class RootModel(BaseModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'pydantic_v2/RootModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'pydantic.RootModel'
