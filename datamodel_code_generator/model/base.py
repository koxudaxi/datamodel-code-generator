from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

from jinja2 import Template

TEMPLATE_DIR: Path = Path(__file__).parents[0] / "template"


class DataModelField:
    def __init__(
        self,
        name: str,
        type_hint: Optional[str] = None,
        default: Optional[str] = None,
        required: bool = False,
    ):
        self.name: str = name
        self.type_hint: Optional[str] = type_hint
        self.required: bool = required
        self.default: Optional[str] = default


class TemplateBase(ABC):
    def __init__(self, template_file_path: str) -> None:
        self.template_file_path: str = template_file_path
        self._template: Optional[Template] = None

    @property
    def template(self) -> Template:
        if self._template:
            return self._template
        self._template = Template((TEMPLATE_DIR / self.template_file_path).read_text())
        return self._template

    @abstractmethod
    def render(self) -> str:
        pass

    def _render(self, *args: Any, **kwargs: Any) -> str:
        return self.template.render(*args, **kwargs)

    def __str__(self) -> str:
        return self.render()


class DataModel(TemplateBase, ABC):
    TEMPLATE_FILE_PATH: str = ""

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_class: Optional[str] = None,
    ) -> None:
        if not self.TEMPLATE_FILE_PATH:
            raise Exception(f"TEMPLATE_FILE_NAME Not Set")

        self.name: str = name
        self.fields: List[DataModelField] = fields or [DataModelField(name="pass")]
        self.decorators: List[str] = decorators or []
        self.base_class: Optional[str] = base_class
        self._template: Optional[Template] = None

        super().__init__(template_file_path=self.TEMPLATE_FILE_PATH)

    def render(self) -> str:
        response = self._render(
            class_name=self.name,
            fields=self.fields,
            decorators=self.decorators,
            base_class=self.base_class,
        )
        return response
