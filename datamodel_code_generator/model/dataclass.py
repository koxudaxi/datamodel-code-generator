from pathlib import Path
from typing import (
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from datamodel_code_generator import DatetimeClassType, PythonVersion
from datamodel_code_generator.imports import (
    IMPORT_DATE,
    IMPORT_DATETIME,
    IMPORT_TIME,
    IMPORT_TIMEDELTA,
    Import,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.imports import IMPORT_DATACLASS, IMPORT_FIELD
from datamodel_code_generator.model.pydantic.base_model import Constraints
from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.model.types import type_map_factory
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, StrictTypes, Types, chain_as_tuple


def _has_field_assignment(field: DataModelFieldBase) -> bool:
    return bool(field.field) or not (
        field.required
        or (field.represented_default == 'None' and field.strip_default_none)
    )


class DataClass(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'dataclass.jinja2'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_DATACLASS,)

    def __init__(
        self,
        *,
        reference: Reference,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[Reference]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        methods: Optional[List[str]] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
    ) -> None:
        super().__init__(
            reference=reference,
            fields=sorted(fields, key=_has_field_assignment, reverse=False),
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            methods=methods,
            path=path,
            description=description,
            default=default,
            nullable=nullable,
            keyword_only=keyword_only,
        )


class DataModelField(DataModelFieldBase):
    _FIELD_KEYS: ClassVar[Set[str]] = {
        'default_factory',
        'init',
        'repr',
        'hash',
        'compare',
        'metadata',
        'kw_only',
    }
    constraints: Optional[Constraints] = None

    @property
    def imports(self) -> Tuple[Import, ...]:
        field = self.field
        if field and field.startswith('field('):
            return chain_as_tuple(super().imports, (IMPORT_FIELD,))
        return super().imports

    def self_reference(self) -> bool:  # pragma: no cover
        return isinstance(self.parent, DataClass) and self.parent.reference.path in {
            d.reference.path for d in self.data_type.all_data_types if d.reference
        }

    @property
    def field(self) -> Optional[str]:
        """for backwards compatibility"""
        result = str(self)
        if result == '':
            return None

        return result

    def __str__(self) -> str:
        data: Dict[str, Any] = {
            k: v for k, v in self.extras.items() if k in self._FIELD_KEYS
        }

        if self.default != UNDEFINED and self.default is not None:
            data['default'] = self.default

        if self.required:
            data = {
                k: v
                for k, v in data.items()
                if k
                not in (
                    'default',
                    'default_factory',
                )
            }

        if not data:
            return ''

        if len(data) == 1 and 'default' in data:
            default = data['default']

            if isinstance(default, (list, dict)):
                return f'field(default_factory=lambda :{repr(default)})'
            return repr(default)
        kwargs = [
            f'{k}={v if k == "default_factory" else repr(v)}' for k, v in data.items()
        ]
        return f'field({", ".join(kwargs)})'


class DataTypeManager(_DataTypeManager):
    def __init__(
        self,
        python_version: PythonVersion = PythonVersion.PY_38,
        use_standard_collections: bool = False,
        use_generic_container_types: bool = False,
        strict_types: Optional[Sequence[StrictTypes]] = None,
        use_non_positive_negative_number_constrained_types: bool = False,
        use_union_operator: bool = False,
        use_pendulum: bool = False,
        target_datetime_class: DatetimeClassType = DatetimeClassType.Datetime,
    ):
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

        self.type_map: Dict[Types, DataType] = {
            **type_map_factory(self.data_type),
            **datetime_map,
        }
