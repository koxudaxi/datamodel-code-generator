from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.model.pydantic_v2.base_model import BaseModel


class RootModel(BaseModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'pydantic_v2/RootModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'pydantic.RootModel'

    def __init__(
            self,
            **kwargs,
    ):
        # Remove custom_base_class for Pydantic V2 models; behaviour is different from Pydantic V1 as it will not
        # be treated as a root model. custom_base_class cannot both implement BaseModel and RootModel!
        kwargs.pop("custom_base_class")

        super().__init__(**kwargs)
