"""Pydantic v2 RootModel type alias implementation.

Generates RootModel as type alias format: `Foo = RootModel[type]`
instead of class inheritance format: `class Foo(RootModel[type]): root: type`

This improves mypy type inference for RootModel constructors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_ROOT_MODEL
from datamodel_code_generator.model.pydantic_v2.root_model import RootModel

if TYPE_CHECKING:
    from datamodel_code_generator.imports import Import


class RootModelTypeAlias(RootModel):
    """DataModel for Pydantic v2 RootModel as type alias.

    Generates: Foo = RootModel[type]
    instead of: class Foo(RootModel[type]): root: type

    This format is better understood by mypy for constructor argument inference.
    """

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/RootModelTypeAlias.jinja2"
    IS_ALIAS: ClassVar[bool] = True
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_ROOT_MODEL,)
