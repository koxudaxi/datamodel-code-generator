"""Pydantic v2 RootModel type alias implementation.

Generates RootModel as type alias format: `Foo = RootModel[type]`
instead of class inheritance format: `class Foo(RootModel[type]): root: type`

This improves mypy type inference for RootModel constructors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from datamodel_code_generator import cached_path_exists
from datamodel_code_generator.model.base import TEMPLATE_DIR
from datamodel_code_generator.model.pydantic_v2.base_model import has_lookaround_pattern
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_ROOT_MODEL
from datamodel_code_generator.model.pydantic_v2.root_model import RootModel

if TYPE_CHECKING:
    from pathlib import Path

    from datamodel_code_generator.imports import Import
    from datamodel_code_generator.model.base import DataModelFieldBase


def _root_model_constraints_fallback(
    fields: list[DataModelFieldBase], custom_template_dir: Path | None
) -> type[RootModel] | None:
    """Keep constraints omitted by the alias template on an executable root class."""
    if any(
        field.constraints and field.constraints.model_dump(exclude={"unique_items"}, exclude_none=True)
        for field in fields
    ) or has_lookaround_pattern(fields):
        if (
            custom_template_dir is not None
            and cached_path_exists(custom_template_dir / RootModelTypeAlias.TEMPLATE_FILE_PATH)
            and custom_template_dir.resolve() != TEMPLATE_DIR.resolve()
        ):
            return None
        return RootModel
    return None


class RootModelTypeAlias(RootModel):
    """DataModel for Pydantic v2 RootModel as type alias.

    Generates: Foo = RootModel[type]
    instead of: class Foo(RootModel[type]): root: type

    This format is better understood by mypy for constructor argument inference.
    """

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/RootModelTypeAlias.jinja2"
    IS_ALIAS: ClassVar[bool] = True
    ROOT_MODEL_CONSTRAINTS_FALLBACK = staticmethod(_root_model_constraints_fallback)
    DOCSTRING_INDENT: ClassVar[int] = 0
    FIELD_DOCSTRING_INDENT: ClassVar[int] = 0
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_ROOT_MODEL,)
