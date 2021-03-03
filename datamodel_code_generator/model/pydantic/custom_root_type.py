from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.base import DataModel, DataModelFieldBase
from datamodel_code_generator.model.pydantic.imports import IMPORT_EXTRA, IMPORT_FIELD
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import chain_as_tuple


class CustomRootType(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel_root.jinja2'
    BASE_CLASS = 'pydantic.BaseModel'

    def __init__(
        self,
        *,
        reference: Reference,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[Reference]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Any]] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
    ):
        super().__init__(
            fields=fields,
            reference=reference,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            path=path,
            description=description,
        )

        config_parameters: Dict[str, Any] = {}

        if 'additionalProperties' in self.extra_template_data:
            config_parameters['extra'] = 'Extra.allow'
            self._additional_imports.append(IMPORT_EXTRA)

        if config_parameters:
            from datamodel_code_generator.model.pydantic import Config

            self.extra_template_data['config'] = Config.parse_obj(config_parameters)

    @property
    def imports(self) -> Tuple[Import, ...]:
        if any(f for f in self.fields if f.field):
            return chain_as_tuple(super().imports, (IMPORT_FIELD,))
        return super().imports
