from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional, Set, Tuple

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.improts import IMPORT_DATACLASS, IMPORT_FIELD
from datamodel_code_generator.model.pydantic.base_model import Constraints
from datamodel_code_generator.types import chain_as_tuple


class DataClass(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'dataclass.jinja2'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_DATACLASS,)

    @property
    def imports(self) -> Tuple[Import, ...]:
        if any(f for f in self.fields if f.field):
            return chain_as_tuple(super().imports, (IMPORT_FIELD,))
        return super().imports


class DataModelField(DataModelFieldBase):
    _EXCLUDE_FIELD_KEYS: ClassVar[Set[str]] = {
        'default',
        'default_factory',
        'init',
        'repr',
        'hash',
        'compare',
        'metadata',
        'kw_only',
    }
    constraints: Optional[Constraints] = None

    def self_reference(self) -> bool:
        return isinstance(self.parent, DataClass) and self.parent.reference.path in {
            d.reference.path for d in self.data_type.all_data_types if d.reference
        }

    def __str__(self) -> str:
        data: Dict[str, Any] = {
            k: v for k, v in self.extras.items() if k not in self._EXCLUDE_FIELD_KEYS
        }

        if self.required:
            default_factory = None
        else:
            default_factory = data.pop('default_factory', None)

        field_arguments = sorted(
            f"{k}={repr(v)}" for k, v in data.items() if v is not None
        )

        if not field_arguments and not default_factory:
            if self.nullable and self.required:
                return 'Field(...)'  # Field() is for mypy
            return ""

        if self.use_annotated:
            pass
        elif self.required:
            field_arguments = ['...', *field_arguments]
        elif default_factory:
            field_arguments = [f'default_factory={default_factory}', *field_arguments]
        else:
            field_arguments = [f'{repr(self.default)}', *field_arguments]

        return f'Field({", ".join(field_arguments)})'
