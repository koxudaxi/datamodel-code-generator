from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel as _BaseModel

from .base_model import BaseModel, DataModelField
from .custom_root_type import CustomRootType
from .dataclass import DataClass
from .types import DataTypeManager


def dump_resolve_reference_action(class_names: Iterable[str]) -> str:
    return "\n".join(f"{class_name}.update_forward_refs()" for class_name in class_names)


class Config(_BaseModel):
    extra: str | None = None
    title: str | None = None
    allow_population_by_field_name: bool | None = None
    allow_extra_fields: bool | None = None
    allow_mutation: bool | None = None
    arbitrary_types_allowed: bool | None = None
    orm_mode: bool | None = None


# def get_validator_template() -> Template:
#     template_file_path: Path = Path('pydantic') / 'one_of_validator.jinja2'
#     loader = FileSystemLoader(str(TEMPLATE_DIR / template_file_path.parent))
#     environment: Environment = Environment(loader=loader, autoescape=True)
#     return environment.get_template(template_file_path.name)
#
#
# VALIDATOR_TEMPLATE: Template = get_validator_template()


__all__ = [
    "BaseModel",
    "CustomRootType",
    "DataClass",
    "DataModelField",
    "DataTypeManager",
    "dump_resolve_reference_action",
    # 'VALIDATOR_TEMPLATE',
]
