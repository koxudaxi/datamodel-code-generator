from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

from jinja2 import Template
from pydantic import BaseModel

TEMPLATE_DIR: Path = Path(__file__).parents[0] / 'template'


class DataModelField(BaseModel):
    name: Optional[str]
    type_hint: Optional[str]
    default: Optional[str]
    required: bool = False


class TemplateBase(ABC):
    def __init__(self, template_file_path: str) -> None:
        self.template_file_path: str = template_file_path
        self._template: Template = Template(
            (TEMPLATE_DIR / self.template_file_path).read_text()
        )

    @property
    def template(self) -> Template:
        return self._template

    @abstractmethod
    def render(self) -> str:
        raise NotImplementedError

    def _render(self, *args: Any, **kwargs: Any) -> str:
        return self.template.render(*args, **kwargs)

    def __str__(self) -> str:
        return self.render()


class DataModel(TemplateBase, ABC):
    TEMPLATE_FILE_PATH: str = ''
    BASE_CLASS: str = ''

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_class: Optional[str] = None,
    ) -> None:
        if not self.TEMPLATE_FILE_PATH:
            raise Exception('TEMPLATE_FILE_NAME is undefined')

        self.name: str = name
        self.fields: List[DataModelField] = fields or [DataModelField(name='pass')]
        self.decorators: List[str] = decorators or []
        self.base_class: Optional[str] = base_class

        super().__init__(template_file_path=self.TEMPLATE_FILE_PATH)

    def render(self) -> str:
        response = self._render(
            class_name=self.name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.BASE_CLASS,
        )
        return response
