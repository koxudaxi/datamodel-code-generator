from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Optional

from jinja2.filters import FILTERS

from datamodel_code_generator import DatetimeClassType, PythonVersion, PythonVersionMin
from datamodel_code_generator.imports import (
    IMPORT_DATE,
    IMPORT_DATETIME,
    IMPORT_TIME,
    IMPORT_TIMEDELTA,
    Import,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.model.types import type_map_factory
from datamodel_code_generator.types import DataType, StrictTypes, Types, chain_as_tuple

if TYPE_CHECKING:
    from collections.abc import Sequence

from datamodel_code_generator.model.pydantic.base_model import Constraints  # noqa: TC001

IMPORT_SQLMODEL = Import.from_full_path("sqlmodel.SQLModel")
IMPORT_FIELD = Import.from_full_path("sqlmodel.Field")
IMPORT_RELATIONSHIP = Import.from_full_path("sqlmodel.Relationship")


def camelcase_to_snake_case(value: str) -> str:
    return "".join(
        ["_" + c.lower() if c.isupper() else c for c in value]
    ).lstrip("_")


FILTERS["snake_case"] = camelcase_to_snake_case


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "sqlmodel.jinja2"
    BASE_CLASS: ClassVar[str] = "sqlmodel.SQLModel"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_SQLMODEL, IMPORT_FIELD)


class RootModel(BaseModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = "root.jinja2"


class DataModelField(DataModelFieldBase):
    _FIELD_KEYS: ClassVar[set[str]] = {
        "default_factory",
        "init",
        "repr",
        "hash",
        "compare",
        "metadata",
        "kw_only",
        # Custom keys for generating SQLModel fields
        "primary_key",
        "foreign_key",
    }
    constraints: Optional[Constraints] = None  # noqa: UP045

    @property
    def imports(self) -> tuple[Import, ...]:
        field = self.field
        if field and field.startswith("Field("):
            return chain_as_tuple(super().imports, (IMPORT_FIELD,))
        if field and field.startswith("Relationship("):
            return chain_as_tuple(super().imports, (IMPORT_RELATIONSHIP,))
        return super().imports

    def self_reference(self) -> bool:  # pragma: no cover
        return isinstance(self.parent, BaseModel) and self.parent.reference.path in {
            d.reference.path for d in self.data_type.all_data_types if d.reference
        }

    @property
    def field(self) -> str | None:
        """for backwards compatibility"""
        return str(self) or None

    def __str__(self) -> str:
        data: dict[str, Any] = {
            k: v
            for k, v in self.extras.items()
            if k in self._FIELD_KEYS
        }

        if self.default != UNDEFINED and self.default is not None:
            data["default"] = self.default

        if self.required:
            data = {
                k: v
                for k, v in data.items()
                if k not in {
                    "default",
                    "default_factory",
                }
            }

        if not data:
            return ""

        if len(data) == 1 and "default" in data:
            default = data["default"]

            if isinstance(default, (list, dict)):
                return f"Field(default=lambda :{default!r})"
            return repr(default)

        # TODO: handle PK/FK attributes here?
        # TODO: handling for relationships
        kwargs = [
            f"{k}={v if k == 'default' else repr(v)}"
            for k, v in data.items()
        ]
        return f"Field({', '.join(kwargs)})"


class DataTypeManager(_DataTypeManager):
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        python_version: PythonVersion = PythonVersionMin,
        use_standard_collections: bool = False,  # noqa: FBT001, FBT002
        use_generic_container_types: bool = False,  # noqa: FBT001, FBT002
        strict_types: Sequence[StrictTypes] | None = None,
        use_non_positive_negative_number_constrained_types: bool = False,  # noqa: FBT001, FBT002
        use_union_operator: bool = False,  # noqa: FBT001, FBT002
        use_pendulum: bool = False,  # noqa: FBT001, FBT002
        target_datetime_class: DatetimeClassType = DatetimeClassType.Datetime,
    ) -> None:
        super().__init__(
            python_version,
            use_standard_collections,
            use_generic_container_types,
            strict_types,
            use_non_positive_negative_number_constrained_types,
            use_union_operator,
            use_pendulum,
            target_datetime_class,
        )

        datetime_map = (
            {
                Types.time: self.data_type.from_import(IMPORT_TIME),
                Types.date: self.data_type.from_import(IMPORT_DATE),
                Types.date_time: self.data_type.from_import(IMPORT_DATETIME),
                Types.timedelta: self.data_type.from_import(IMPORT_TIMEDELTA),
            }
            if target_datetime_class is DatetimeClassType.Datetime
            else {}
        )

        self.type_map: dict[Types, DataType] = {
            **type_map_factory(self.data_type),
            **datetime_map,
        }
