from __future__ import annotations

from typing import ClassVar

from datamodel_code_generator.model import DataModel


class Root(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'root.jinja2'
