"""Pydantic v2 dataclass model generator.

Generates pydantic.dataclasses.dataclass decorated classes with validation support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from datamodel_code_generator.imports import IMPORT_ANNOTATED
from datamodel_code_generator.model import DataModel, DataModelFieldBase, _rebuild_model_with_datamodel_namespace
from datamodel_code_generator.model import dataclass as _dataclass_module
from datamodel_code_generator.model.base import UNDEFINED, _has_field_assignment
from datamodel_code_generator.model.dataclass import _DataclassReuseMixin
from datamodel_code_generator.model.pydantic_v2._config import (
    ConfigAttribute,
    build_base_config_parameters,
)
from datamodel_code_generator.model.pydantic_v2._output_context import (
    ANNOTATED_CONSTRAINTS_CONTEXT as _ANNOTATED_CONSTRAINTS_CONTEXT,
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
from datamodel_code_generator.model.pydantic_v2.version import (
    PYDANTIC_V2_DATACLASS_ALIAS_NEEDS_FALLBACK,
    _get_dict_key_reference_classes_capability,
)

has_field_assignment = _dataclass_module.has_field_assignment


def _has_pydantic_dataclass_field_assignment(field: DataModelFieldBase) -> bool:
    """Check assignments that must remain visible to Python dataclasses."""
    if field.use_annotated and getattr(field, "requires_dataclass_field_assignment", False):
        return bool(field.field)
    return _has_field_assignment(field)


def _get_pydantic_dataclass_field_default_info(field: DataModelFieldBase) -> tuple[bool, bool]:
    """Return Pydantic dataclass constructor-default semantics."""
    return field._get_constructor_default_info()  # noqa: SLF001  # output-owned field policy hook


def _pydantic_dataclass_field_participates_in_constructor(field: DataModelFieldBase) -> bool:
    """Return whether a Pydantic dataclass field participates in __init__."""
    return field.extras.get("x-is-classvar") is not True


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
    FIELD_ASSIGNMENT_CHECKER = staticmethod(_has_pydantic_dataclass_field_assignment)
    FIELD_DEFAULT_CLASSIFIER = staticmethod(_get_pydantic_dataclass_field_default_info)
    FIELD_PARTICIPATES_IN_CONSTRUCTOR = staticmethod(_pydantic_dataclass_field_participates_in_constructor)
    USES_DATACLASS_ARGUMENTS: ClassVar[bool] = True
    SUPPORTS_REQUIRED_INHERITED_FIELD_ASSIGNMENT: ClassVar[bool] = True
    REQUIRES_EXPLICIT_INHERITED_FACTORY_OVERRIDE: ClassVar[bool] = True
    REQUIRED_ASSIGNMENT_COUNTS_AS_CONSTRUCTOR_DEFAULT: ClassVar[bool] = True
    REQUIRES_RUNTIME_IMPORTS_WITH_RUFF_CHECK: ClassVar[bool] = True
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_KW_ONLY: ClassVar[bool] = True
    SUPPORTS_ANNOTATED_CONSTRAINTS: ClassVar[bool] = True
    ANNOTATED_CONSTRAINTS_CONTEXT: ClassVar[object | None] = _ANNOTATED_CONSTRAINTS_CONTEXT
    _INCLUDE_DICT_KEY_REFERENCE_CLASSES = _get_dict_key_reference_classes_capability()
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
            fields=sorted(fields, key=_has_pydantic_dataclass_field_assignment),
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

        if config_parameters:
            self._additional_imports.append(IMPORT_CONFIG_DICT)
            self.extra_template_data["config"] = config_parameters

        self._lookaround_regex_engine_checked = False

    def _apply_lookaround_regex_engine(self) -> None:
        """Force the python-re regex engine when a lookaround pattern is reachable.

        Runs lazily because referenced patterns are only linked after ``__init__``; the
        result is memoized to keep ``imports`` cheap.
        """
        if self._lookaround_regex_engine_checked:
            return
        self._lookaround_regex_engine_checked = True
        if not has_lookaround_pattern(self.fields, follow_references=True):
            return
        # Merge into any config from __init__; a duplicate ConfigDict import is deduped on render.
        config = self.extra_template_data.setdefault("config", {})
        config["regex_engine"] = '"python-re"'
        self._additional_imports.append(IMPORT_CONFIG_DICT)
        self.clear_imports_cache()

    @property
    def imports(self) -> tuple[Import, ...]:
        """Return model imports, ensuring the lookaround regex engine config is applied."""
        self._apply_lookaround_regex_engine()
        return super().imports

    def render(self, *, class_name: str | None = None) -> str:
        """Render the dataclass, ensuring the lookaround regex engine config is applied."""
        self._apply_lookaround_regex_engine()
        return super().render(class_name=class_name)


class _PydanticDataclassField(DataModelFieldV2):
    """Adapt Annotated fields to the existing dataclass template contract."""

    _DATACLASS_ASSIGNMENT_KEYS: ClassVar[frozenset[str]] = frozenset({
        "default_factory",
        "init",
        "init_var",
        "kw_only",
        "repr",
    })

    def _get_constructor_default_info(self) -> tuple[bool, bool]:
        """Return constructor-default semantics from structured field state."""
        if self.is_class_var:
            self.__dict__["_computed_default_factory"] = None
            return False, False
        if not _has_pydantic_dataclass_field_assignment(self) or (self.required and not self.use_default_with_required):
            return False, False
        if self.__dict__.get("_computed_default_factory"):
            return True, False
        return True, True

    @property
    def requires_dataclass_field_assignment(self) -> bool:
        """Check whether Annotated metadata must also be visible to dataclasses."""
        if (
            self._has_forced_field_assignment
            or not self._DATACLASS_ASSIGNMENT_KEYS.isdisjoint(self.extras)
            or self.has_default_factory_in_field
        ):
            return True
        return bool(
            self.use_default_factory_for_optional_nested_models
            and not self.required
            and (self.default is None or self.default is UNDEFINED)
            and self._get_default_factory_for_optional_nested_model()
        )

    @property
    def dataclass_field(self) -> str | None:
        """Render a Field() assignment that preserves Python dataclass defaults."""
        if not (result := str(self)):
            return None
        if (
            self.has_default_factory_in_field
            or (self.required and not self.use_default_with_required)
            or self.should_strip_default_none(keep_optional=True)
        ):
            return result
        arguments = result.removeprefix("Field(").removesuffix(")")
        separator = ", " if arguments else ""
        default_argument = f"default={self.represented_default}" if self.use_default_kwarg else self.represented_default
        return f"Field({default_argument}{separator}{arguments})"

    def _has_field_statement(self) -> bool:
        """Include a required assignment forced by dataclass inheritance."""
        if self._has_forced_field_assignment:
            self.__dict__["_computed_default_factory"] = None
            return True
        return super()._has_field_statement()

    def __str__(self) -> str:
        """Render a forced required assignment for the dataclass constructor."""
        return super().__str__() or ("Field(...)" if self._has_forced_field_assignment else "")

    @property
    def _requires_unannotated_dataclass_assignment(self) -> bool:
        return self.use_annotated and self.requires_dataclass_field_assignment

    @property
    def annotated(self) -> str | None:
        """Keep assignments visible to legacy dataclass templates."""
        if self._requires_unannotated_dataclass_assignment:
            return None
        return super().annotated

    @property
    def field(self) -> str | None:
        """Render dataclass-visible metadata on the assignment when required."""
        if self._requires_unannotated_dataclass_assignment:
            return self.dataclass_field
        return super().field

    def _rendered_field_values(self) -> tuple[str | None, str | None]:
        """Keep built-in rendering consistent with the public field properties."""
        if self._requires_unannotated_dataclass_assignment:
            return self.dataclass_field, None
        return super()._rendered_field_values()

    @property
    def imports(self) -> tuple[Import, ...]:
        """Drop Annotated when dataclass metadata moves to the assignment."""
        imports = super().imports
        if not self._requires_unannotated_dataclass_assignment:
            return imports
        return tuple(import_ for import_ in imports if import_ != IMPORT_ANNOTATED)


if PYDANTIC_V2_DATACLASS_ALIAS_NEEDS_FALLBACK:
    import keyword

    class DataModelField(_PydanticDataclassField):
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

        @property
        def requires_dataclass_field_assignment(self) -> bool:
            """Keep legacy alias metadata on the assignment Pydantic 2.0 consumes."""
            return (
                bool(self.validation_aliases or self.serialization_alias) or super().requires_dataclass_field_assignment
            )

else:

    class DataModelField(_PydanticDataclassField):
        """Field implementation for Pydantic v2 dataclass models.

        Inherits pydantic v2 Field() constraint handling from DataModelFieldV2.
        """


_rebuild_model_with_datamodel_namespace(DataModelField)
