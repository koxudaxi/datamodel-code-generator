from typing import ClassVar, Tuple

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.base import DataModel
from datamodel_code_generator.types import chain_as_tuple


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'schematics/BaseModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'schematics.models.Model'

    @property
    def is_fake_class(self) -> bool:
        """
        This configuration causes a "class" to be created even though it really shouldn't:
        "extensions": {
            "type": "object",
            "additionalProperties": {
              "type": "object",
              "additionalProperties": false
            },
            "nullable": true,
            "readOnly": true
          }

        Whereas this configuration is properly parsed:
        "errors": {
            "type": "object",
            "additionalProperties": {
              "type": "array",
              "items": {
                "type": "string"
              }
            },
            "nullable": true
          }
        """
        return not self.fields

    def render(self) -> str:
        if self.is_fake_class:
            return ''

        return super().render()

    @property
    def imports(self) -> Tuple[Import, ...]:
        return chain_as_tuple(
            (i for f in self.fields for i in f.imports), self._additional_imports
        )
