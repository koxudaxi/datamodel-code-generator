from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.base import DataModel, DataModelFieldBase
from datamodel_code_generator.model.pydantic.imports import IMPORT_EXTRA, IMPORT_FIELD
from datamodel_code_generator.reference import Reference


class CustomRootType(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel_root.jinja2'
    BASE_CLASS = 'pydantic.BaseModel'

    def __init__(
        self,
        name: str,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[str]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Any]] = None,
        imports: Optional[List[Import]] = None,
        auto_import: bool = True,
        reference_classes: Optional[List[str]] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
        reference: Optional[Reference] = None,
    ):
        super().__init__(
            name,
            fields=fields,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            imports=imports,
            auto_import=auto_import,
            reference_classes=reference_classes,
            path=path,
            description=description,
            reference=reference,
        )

        config_parameters: Dict[str, Any] = {}

        if 'additionalProperties' in self.extra_template_data:
            config_parameters['extra'] = 'Extra.allow'
            self.imports.append(IMPORT_EXTRA)

        if config_parameters:
            from datamodel_code_generator.model.pydantic import Config

            self.extra_template_data['config'] = Config.parse_obj(config_parameters)

        for field in fields:
            if field.field:
                self.imports.append(IMPORT_FIELD)
