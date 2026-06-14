"""Pydantic v2 dataclass model generator.

Generates pydantic.dataclasses.dataclass decorated classes with validation support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from datamodel_code_generator.model import DataModel, DataModelFieldBase, _rebuild_model_with_datamodel_namespace
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.dataclass import _DataclassReuseMixin, has_field_assignment
from datamodel_code_generator.model.pydantic_v2._config import (
    ConfigAttribute,
    build_base_config_parameters,
)
from datamodel_code_generator.model.pydantic_v2.base_model import (
    Constraints as _Constraints,
)
from datamodel_code_generator.model.pydantic_v2.base_model import (
    DataModelField as DataModelFieldV2,
)
from datamodel_code_generator.model.pydantic_v2.base_model import (
    has_lookaround_pattern,
)
from datamodel_code_generator.model.pydantic_v2.imports import (
    IMPORT_CONFIG_DICT,
    IMPORT_PYDANTIC_DATACLASS,
)
from datamodel_code_generator.model.pydantic_v2.version import PYDANTIC_V2_DATACLASS_ALIAS_NEEDS_FALLBACK

if TYPE_CHECKING:
    from collections import defaultdict
    from pathlib import Path

    from datamodel_code_generator import DataclassArguments
    from datamodel_code_generator.imports import Import
    from datamodel_code_generator.reference import Reference

Constraints = _Constraints


class DataClass(_DataclassReuseMixin, DataModel):
    """DataModel implementation for Pydantic v2 dataclasses."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/dataclass.jinja2"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_PYDANTIC_DATACLASS,)
    REQUIRES_RUNTIME_IMPORTS_WITH_RUFF_CHECK: ClassVar[bool] = True
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_KW_ONLY: ClassVar[bool] = True
    # frozen/allow_mutation are handled as dataclass decorator arguments, not ConfigDict
    _CONFIG_ATTRIBUTES_V2: ClassVar[list[ConfigAttribute]] = [
        ConfigAttribute("allow_population_by_field_name", "populate_by_name", False),  # noqa: FBT003
        ConfigAttribute("populate_by_name", "populate_by_name", False),  # noqa: FBT003
        ConfigAttribute("use_attribute_docstrings", "use_attribute_docstrings", False),  # noqa: FBT003
    ]
    _CONFIG_ATTRIBUTES_V2_11: ClassVar[list[ConfigAttribute]] = [
        ConfigAttribute("allow_population_by_field_name", "validate_by_name", False),  # noqa: FBT003
        ConfigAttribute("populate_by_name", "validate_by_name", False),  # noqa: FBT003
        ConfigAttribute("use_attribute_docstrings", "use_attribute_docstrings", False),  # noqa: FBT003
    ]

    def __init__(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        decorators: list[str] | None = None,
        base_classes: list[Reference] | None = None,
        custom_base_class: str | list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
        methods: list[str] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        frozen: bool = False,
        treat_dot_as_module: bool | None = None,
        dataclass_arguments: DataclassArguments | None = None,
    ) -> None:
        """Initialize pydantic v2 dataclass with sorted fields and ConfigDict support."""
        super().__init__(
            reference=reference,
            fields=sorted(fields, key=has_field_assignment),
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
            frozen=frozen,
            treat_dot_as_module=treat_dot_as_module,
        )

        if dataclass_arguments is not None:
            self.dataclass_arguments = dataclass_arguments
        else:
            self.dataclass_arguments = {}
            if frozen:
                self.dataclass_arguments["frozen"] = True
            if keyword_only:
                self.dataclass_arguments["kw_only"] = True
        self._set_deprecated_decorator()

        config_parameters = build_base_config_parameters(
            extra_template_data=self.extra_template_data,
            all_data_types=self.all_data_types,
            config_attributes_v2=self._CONFIG_ATTRIBUTES_V2,
            config_attributes_v2_11=self._CONFIG_ATTRIBUTES_V2_11,
        )

        if has_lookaround_pattern(self.fields):
            config_parameters["regex_engine"] = '"python-re"'

        if config_parameters:
            self._additional_imports.append(IMPORT_CONFIG_DICT)
            self.extra_template_data["config"] = config_parameters


if PYDANTIC_V2_DATACLASS_ALIAS_NEEDS_FALLBACK:
    import keyword

    class DataModelField(DataModelFieldV2):
        """Field implementation for Pydantic v2 dataclass models.

        Inherits pydantic v2 Field() constraint handling from DataModelFieldV2.
        """

        def __init__(self, **data: Any) -> None:
            """Initialize and make non-identifier aliases safe for dataclass signatures."""
            super().__init__(**data)
            if self.alias is None or (self.alias.isidentifier() and not keyword.iskeyword(self.alias)):
                return

            validation_aliases = list(self.validation_aliases or ())
            if self.alias not in validation_aliases:
                validation_aliases.insert(0, self.alias)
            if self.serialization_alias is None:
                self.serialization_alias = self.alias
            self.validation_aliases = validation_aliases
            self.alias = None

else:

    class DataModelField(DataModelFieldV2):
        """Field implementation for Pydantic v2 dataclass models.

        Inherits pydantic v2 Field() constraint handling from DataModelFieldV2.
        """


_rebuild_model_with_datamodel_namespace(DataModelField)
