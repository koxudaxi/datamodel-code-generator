"""Pydantic v2 BaseModel implementation.

Provides Constraints, DataModelField, and BaseModel for Pydantic v2
with support for Field() constraints and ConfigDict.
"""

from __future__ import annotations

import json
import keyword
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast
from warnings import warn

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic.alias_generators import to_camel, to_pascal, to_snake

from datamodel_code_generator import Error
from datamodel_code_generator.enums import AliasGenerator
from datamodel_code_generator.imports import IMPORT_ANNOTATED, IMPORT_ANY, IMPORT_DICT, IMPORT_UNION, Import
from datamodel_code_generator.model import _rebuild_model_with_datamodel_namespace
from datamodel_code_generator.model.base import (
    ALL_MODEL,
    UNDEFINED,
    BaseClassDataType,
    DataModel,
    DataModelFieldBase,
    _get_template_with_custom_dir,
)
from datamodel_code_generator.model.imports import IMPORT_CLASSVAR
from datamodel_code_generator.model.pydantic_base import (
    BaseModelBase,
    _PydanticFieldRenderPlan,
)
from datamodel_code_generator.model.pydantic_base import Constraints as _Constraints
from datamodel_code_generator.model.pydantic_base import (
    DataModelField as _PydanticBaseDataModelField,
)
from datamodel_code_generator.model.pydantic_v2._config import (
    ConfigAttribute,
    build_base_config_parameters,
)
from datamodel_code_generator.model.pydantic_v2._output_context import (
    ANNOTATED_CONSTRAINTS_CONTEXT as _ANNOTATED_CONSTRAINTS_CONTEXT,
)
from datamodel_code_generator.model.pydantic_v2.imports import (
    IMPORT_ALIAS_CHOICES,
    IMPORT_ALIAS_GENERATOR_TO_CAMEL,
    IMPORT_ALIAS_GENERATOR_TO_PASCAL,
    IMPORT_ALIAS_GENERATOR_TO_SNAKE,
    IMPORT_BASE_MODEL,
    IMPORT_CONFIG_DICT,
    IMPORT_FIELD,
    IMPORT_FIELD_VALIDATOR,
    IMPORT_MISSING,
    IMPORT_MODEL_VALIDATOR,
    IMPORT_TYPE_ADAPTER,
    IMPORT_VALIDATION_INFO,
    IMPORT_VALIDATOR_FUNCTION_WRAP_HANDLER,
)
from datamodel_code_generator.model.pydantic_v2.version import (
    PYDANTIC_V2_FIELD_DEPRECATED_NEEDS_JSON_SCHEMA_EXTRA,
    _get_dict_key_reference_classes_capability,
)
from datamodel_code_generator.model.runtime_validation import (
    SchemaRuntimeValidation,
    _is_internal_schema_runtime_validation,
    unique_items_path_uses_regex,
)
from datamodel_code_generator.python_literal import (
    _normalize_string,
    represent_untrusted_python_value,
)
from datamodel_code_generator.reference import ModelResolver, ModelType
from datamodel_code_generator.types import chain_as_tuple

if TYPE_CHECKING:
    from jinja2 import Template
    from typing_extensions import TypedDict, Unpack

    from datamodel_code_generator.model.pydantic_v2._schema_runtime_validation import (
        SchemaRuntimeValidationModulePlan,
    )
    from datamodel_code_generator.reference import Reference
    from datamodel_code_generator.types import DataType


class _RawRepr:
    """Wrapper to prevent repr() from adding quotes around a value."""

    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return self.value


class Constraints(_Constraints):
    """Pydantic v2 field constraints with pattern support."""

    # To override existing pattern alias
    regex: Optional[str] = Field(None, alias="regex")  # noqa: UP045
    pattern: Optional[str] = Field(None, alias="pattern")  # noqa: UP045

    @model_validator(mode="before")
    def validate_min_max_items(cls, values: Any) -> dict[str, Any]:  # noqa: N805
        """Validate and convert minItems/maxItems to minLength/maxLength."""
        if not isinstance(values, dict):  # pragma: no cover
            return values
        min_items = values.pop("minItems", None)
        if min_items is not None:
            values["minLength"] = min_items
        max_items = values.pop("maxItems", None)
        if max_items is not None:
            values["maxLength"] = max_items
        return values


DataModelFieldV1 = _PydanticBaseDataModelField  # deprecated re-export, pydantic-v1 output removed in #3031

_ALIAS_GENERATOR_TEMPLATE_DATA_KEY = "alias_generator"
_ALIAS_GENERATOR_INTERNAL_KEY = "_alias_generator"
_NO_ALIAS_INTERNAL_KEY = "_no_alias"
_MISSING_SENTINEL = "MISSING"
_CONFIG_ITEMS_TEMPLATE_DATA_KEY = "config_items"
_MIN_QUOTED_STRING_LENGTH = 2
_LEGACY_CONFIG_LITERAL_STRINGS: frozenset[str] = frozenset({"False", "None", "True"})
_LEGACY_PYDANTIC_EXTRA_TEMPLATE_PATTERN = re.compile(
    r"{%-?\s*(?:if|elif)\s+(?:not\s+)?field\.use_pydantic_extra_annotation_assignment\b"
)
_LEGACY_PYDANTIC_EXTRA_POST_CLASS_PATTERN = re.compile(
    r"(?m)^(?P<class_name>[^.\s]+)[ \t]*\.[ \t]*__annotations__[ \t]*"
    r"\[[ \t]*(?P<quote>['\"])__pydantic_extra__(?P=quote)[ \t]*\][ \t]*=[^\r\n]*\r?\n"
    r"(?:[ \t]*\r?\n)*"
    r"(?P=class_name)[ \t]*\.[ \t]*model_rebuild[ \t]*"
    r"\([ \t]*force[ \t]*=[ \t]*True[ \t]*\)[ \t]*(?:#[^\r\n]*)?(?:\r?\n)?"
)
_ALIAS_GENERATOR_IMPORTS: dict[str, Import] = {
    AliasGenerator.ToCamel.value: IMPORT_ALIAS_GENERATOR_TO_CAMEL,
    AliasGenerator.ToPascal.value: IMPORT_ALIAS_GENERATOR_TO_PASCAL,
    AliasGenerator.ToSnake.value: IMPORT_ALIAS_GENERATOR_TO_SNAKE,
}


@lru_cache(maxsize=16)
def _uses_legacy_pydantic_extra_template(template_file_path: str) -> bool:
    """Return whether a custom template uses the pre-0.68.1 typed-extra property."""
    template_source = Path(template_file_path).read_text(encoding="utf-8")
    return bool(_LEGACY_PYDANTIC_EXTRA_TEMPLATE_PATTERN.search(template_source))


def _strip_legacy_pydantic_extra_post_class_assignment(rendered: str, class_name: str) -> str | None:
    """Remove the unsupported post-class typed-extra assignment for the rendered model."""
    if (
        assignment := next(
            (
                match
                for match in _LEGACY_PYDANTIC_EXTRA_POST_CLASS_PATTERN.finditer(rendered)
                if match["class_name"] == class_name
            ),
            None,
        )
    ) is None:
        return None
    return f"{rendered[: assignment.start()]}{rendered[assignment.end() :]}"


class _LegacyPydanticExtraTemplate:
    """Adapt pre-0.68.1 custom templates without affecting normal render paths."""

    __slots__ = ("_template",)

    def __init__(self, template: Template) -> None:
        self._template = template

    def __getattr__(self, name: str) -> Any:
        return getattr(self._template, name)

    def _warn_template_update(self, status: str) -> None:
        warn(
            f"Legacy custom template {self._template.filename!r} {status} for Pydantic typed-extra compatibility. "
            "Update the template to declare __pydantic_extra__ in the class body and remove the post-class "
            "annotation assignment and model_rebuild(force=True).",
            stacklevel=3,
        )

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Render typed extras in the class body and remove the unsupported legacy tail."""
        if (
            field := next(
                (
                    field
                    for field in kwargs.get("fields", ())
                    if getattr(field, "use_pydantic_extra_annotations_dict", False)
                ),
                None,
            )
        ) is None:
            return self._template.render(*args, **kwargs)

        annotation_line = f"    '__pydantic_extra__': {field.pydantic_extra_type_hint},"
        kwargs["class_body_lines"] = [
            "__annotations__ = {",
            annotation_line,
            "}",
            *(kwargs.get("class_body_lines") or ()),
        ]
        rendered = self._template.render(*args, **kwargs)
        if annotation_line not in rendered:
            self._warn_template_update("could not be fully rewritten automatically")
            return rendered
        if (adapted := _strip_legacy_pydantic_extra_post_class_assignment(rendered, kwargs["class_name"])) is None:
            self._warn_template_update("could not be fully rewritten automatically")
            return rendered
        self._warn_template_update("was rewritten automatically")
        return adapted


def _adapt_legacy_pydantic_extra_template(template: Template) -> Template:
    """Wrap only custom templates that use the removed typed-extra property."""
    match template.filename:
        case str() as filename if _uses_legacy_pydantic_extra_template(filename):
            return cast("Template", _LegacyPydanticExtraTemplate(template))
    return template


def _alias_generator_name(value: Any) -> str | None:
    generator_name: str | None = None
    match value:
        case AliasGenerator():
            generator_name = value.value
        case str():
            normalized_value = _normalize_string(value)
            if normalized_value in _ALIAS_GENERATOR_IMPORTS:
                generator_name = normalized_value
    return generator_name


def _generate_alias(generator_name: str, field_name: str) -> str:
    generated_alias = field_name
    match generator_name:
        case AliasGenerator.ToCamel.value:
            generated_alias = to_camel(field_name)
        case AliasGenerator.ToPascal.value:
            generated_alias = to_pascal(field_name)
        case AliasGenerator.ToSnake.value:
            generated_alias = to_snake(field_name)
    return generated_alias


def _config_dict_items(config: Any) -> list[tuple[str, Any]]:
    if config is None:
        return []

    if isinstance(config, dict):
        return list(config.items())

    dump = getattr(config, "model_dump", None) or getattr(config, "dict", None)
    if not dump:
        return []
    values = dump(exclude_unset=True)
    return list(values.items()) if isinstance(values, dict) else []


def _safe_config_value(value: Any) -> str:
    """Serialize a ConfigDict value without treating a user string as Python."""
    return represent_untrusted_python_value(value)


def _decode_legacy_quoted_config_string(value: str) -> str:
    """Decode the simple quoted strings emitted by older template-data files.

    This is deliberately not a Python-literal parser.  Existing configuration
    fixtures use ``'allow'`` and ``"python-re"`` spellings; accepting only
    an unescaped matching quote preserves those values while strings with escape
    syntax remain ordinary data and are safely serialized below.
    """
    if (
        len(value) >= _MIN_QUOTED_STRING_LENGTH
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
        and "\\" not in value[1:-1]
    ):
        return value[1:-1]
    return value


def _safe_config_dict_items(config: Any) -> list[tuple[str, str]]:
    """Return Python-source-safe ConfigDict arguments for built-in templates."""
    safe_items: list[tuple[str, str]] = []
    for field_name, value in _config_dict_items(config):
        if not isinstance(field_name, str):
            continue
        normalized_field_name = _normalize_string(field_name)
        if not normalized_field_name.isidentifier() or keyword.iskeyword(normalized_field_name):
            continue
        normalized_value = _normalize_string(value) if isinstance(value, str) else value
        if normalized_field_name == _ALIAS_GENERATOR_TEMPLATE_DATA_KEY and (
            name := _alias_generator_name(normalized_value)
        ):
            safe_items.append((normalized_field_name, name))
            continue
        if isinstance(normalized_value, str) and normalized_value in _LEGACY_CONFIG_LITERAL_STRINGS:
            safe_items.append((normalized_field_name, normalized_value))
            continue
        if isinstance(normalized_value, str):
            normalized_value = _decode_legacy_quoted_config_string(normalized_value)
        rendered_value = _safe_config_value(normalized_value)
        if normalized_field_name == "regex_engine" and isinstance(normalized_value, str):
            # Keep the existing double-quoted spelling for generated regex
            # engine settings while escaping every string character safely.
            rendered_value = json.dumps(normalized_value, ensure_ascii=False)
        safe_items.append((normalized_field_name, rendered_value))
    return safe_items


_PYDANTIC_V2_BASE_FIELD_KEYS: frozenset[str] = frozenset({
    "default",
    "default_factory",
    "alias",
    "alias_priority",
    "validation_alias",
    "serialization_alias",
    "title",
    "description",
    "examples",
    "exclude",
    "discriminator",
    "json_schema_extra",
    "frozen",
    "validate_default",
    "repr",
    "init_var",
    "kw_only",
    "pattern",
    "strict",
    "gt",
    "ge",
    "lt",
    "le",
    "multiple_of",
    "allow_inf_nan",
    "max_digits",
    "decimal_places",
    "min_length",
    "max_length",
    "union_mode",
})


if PYDANTIC_V2_FIELD_DEPRECATED_NEEDS_JSON_SCHEMA_EXTRA:
    _PYDANTIC_V2_DEFAULT_FIELD_KEYS = _PYDANTIC_V2_BASE_FIELD_KEYS
else:
    _PYDANTIC_V2_DEFAULT_FIELD_KEYS = _PYDANTIC_V2_BASE_FIELD_KEYS | {"deprecated"}


class DataModelField(_PydanticBaseDataModelField):
    """Pydantic v2 field with Field() constraints and json_schema_extra support."""

    SUPPORTS_ANNOTATED_CONSTRAINTS: ClassVar[bool] = True
    ANNOTATED_CONSTRAINTS_CONTEXT: ClassVar[object | None] = _ANNOTATED_CONSTRAINTS_CONTEXT
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    _EXCLUDE_FIELD_KEYS: ClassVar[set[str]] = {
        "alias",
        "default",
        "gt",
        "ge",
        "lt",
        "le",
        "multiple_of",
        "min_length",
        "max_length",
        "pattern",
    }
    _DEFAULT_FIELD_KEYS: ClassVar[frozenset[str]] = _PYDANTIC_V2_DEFAULT_FIELD_KEYS
    constraints: Optional[Constraints] = None  # noqa: UP045
    can_have_extra_keys: ClassVar[bool] = False
    _PYDANTIC_EXTRA_FIELD_NAME: ClassVar[str] = "__pydantic_extra__"
    _PYDANTIC_EXTRA_PLAIN_ANNOTATION_KEY: ClassVar[str] = "pydantic_extra_plain_annotation"

    @field_validator("extras")
    def validate_extras(cls, values: Any) -> dict[str, Any]:  # noqa: N805
        """Validate and convert example to examples list."""
        if not isinstance(values, dict):  # pragma: no cover
            return values
        if "examples" in values:
            return values

        if "example" in values:
            values["examples"] = [values.pop("example")]
        return values

    def process_const(self) -> None:
        """Process const field constraint using literal type."""
        self._process_const_as_literal()

    @property
    def use_missing_sentinel_default(self) -> bool:
        """Return whether this field should use the Pydantic MISSING sentinel as its default."""
        if not self.use_missing_sentinel:
            return False
        if self.is_class_var or self.required or self.has_default or self.has_default_factory_in_field:
            return False
        return self.default is None or self.default is UNDEFINED

    @property
    def represented_default(self) -> str:
        """Get the rendered default value for the field."""
        if self.use_missing_sentinel_default:
            return _MISSING_SENTINEL
        return super().represented_default

    def should_strip_default_none(self, *, keep_optional: bool = False) -> bool:
        """Return whether an actual None default should be omitted."""
        if self.use_missing_sentinel_default:
            return False
        return super().should_strip_default_none(keep_optional=keep_optional)

    @property
    def fall_back_to_nullable(self) -> bool:
        """Return whether optional fields should fall back to nullable type hints."""
        if not self.use_missing_sentinel_default:
            return super().fall_back_to_nullable
        return bool(self.nullable or self.type_has_null)

    def _requires_null_default_field(self) -> bool:
        if self.use_missing_sentinel_default:
            return False
        if self.required or self.default is not None or self.has_default_factory:
            return False
        return self.data_type.type == "None"

    def _has_field_statement(self) -> bool:
        if self._requires_null_default_field():
            return True
        if self.is_class_var:
            return False
        if self._alias_generator_name_from_parent() is None:
            return super()._has_field_statement()
        return self._has_processed_field_statement()

    def _has_processed_field_statement(self) -> bool:
        """Return whether the processed render plan contains a Field() call."""
        return bool(self._get_field_render_plan().rendered)

    def _get_field_render_plan(self) -> _PydanticFieldRenderPlan:
        """Include the explicit null default required by Pydantic v2."""
        plan = super()._get_field_render_plan()
        if plan.rendered or not self._requires_null_default_field():
            return plan
        return self._get_single_argument_field_render_plan(
            "None",
            assignment_argument="default=None" if self.use_default_kwarg else None,
        )

    @property
    def type_hint(self) -> str:
        """Get the type hint including MISSING when this field uses the sentinel default."""
        type_hint = super().type_hint
        if not self.use_missing_sentinel_default:
            return type_hint
        return self._type_hint_with_missing_sentinel(type_hint)

    def _type_hint_with_missing_sentinel(self, type_hint: str) -> str:
        match (self._use_union_operator, type_hint):
            case (_, ""):
                return _MISSING_SENTINEL
            case (True, _):
                return f"{type_hint} | {_MISSING_SENTINEL}"
            case (False, _):
                return f"Union[{type_hint}, {_MISSING_SENTINEL}]"
        return type_hint

    @property
    def is_pydantic_extra_field(self) -> bool:
        """Return whether this field represents Pydantic typed extra values."""
        return self.name == self._PYDANTIC_EXTRA_FIELD_NAME

    @property
    def use_pydantic_extra_plain_annotation(self) -> bool:
        """Return whether typed extras can use a regular class annotation."""
        return bool(
            self.is_pydantic_extra_field
            and self.parent
            and self.parent.extra_template_data.get(self._PYDANTIC_EXTRA_PLAIN_ANNOTATION_KEY)
        )

    @property
    def use_pydantic_extra_annotations_dict(self) -> bool:
        """Return whether typed extras need a class-body __annotations__ dict."""
        return self.is_pydantic_extra_field and not self.use_pydantic_extra_plain_annotation

    @property
    def use_pydantic_extra_annotation_assignment(self) -> bool:
        """Support the typed-extra property used by pre-0.68.1 custom templates."""
        return self.use_pydantic_extra_annotations_dict

    @property
    def pydantic_extra_type_hint(self) -> str:
        """Return a Dict-based type hint for Pydantic 2.0 typed extras."""
        data_type = self.data_type
        if not (data_type.is_dict and data_type.use_standard_collections and not data_type.use_generic_container):
            return self.type_hint
        return self._type_hint_from_data_type(data_type.model_copy(update={"use_standard_collections": False}))

    def _process_data_in_str(self, data: dict[str, Any]) -> None:
        if self.const:
            # const is removed in pydantic 2.0
            data.pop("const")

        # unique_items is not supported in pydantic 2.0
        data.pop("unique_items", None)

        if self.use_frozen_field and self.read_only:
            data["frozen"] = True

        if "union_mode" in data:
            if self.data_type.is_union:
                data["union_mode"] = data.pop("union_mode").value
            else:
                data.pop("union_mode")

        self._update_alias_for_alias_generator(data)
        has_alias = "alias" in data
        alias = data.get("alias")

        # Handle multiple aliases using AliasChoices (Pydantic v2 feature)
        if self.validation_aliases:
            unique_validation_aliases = list(dict.fromkeys(self.validation_aliases))
            serialization_alias = (
                self.serialization_alias
                if self.serialization_alias is not None
                else alias
                if has_alias
                else unique_validation_aliases[0]
            )
            # Remove single alias if present (validation_aliases takes precedence)
            data.pop("alias", None)
            # Format as AliasChoices(...) - use _RawRepr to prevent double-quoting
            aliases_repr = ", ".join(repr(a) for a in unique_validation_aliases)
            data["validation_alias"] = _RawRepr(f"AliasChoices({aliases_repr})")
            if self.use_serialization_alias and serialization_alias is not None and serialization_alias != self.name:
                data["serialization_alias"] = serialization_alias

        if self.serialization_alias is not None and (self.serialization_alias != self.name or has_alias):
            data["serialization_alias"] = self.serialization_alias

        if self.use_serialization_alias and "alias" in data:
            serialization_alias = self.serialization_alias if self.serialization_alias is not None else data["alias"]
            data.pop("alias")
            if serialization_alias != self.name:
                data["serialization_alias"] = serialization_alias

        # **extra is not supported in pydantic 2.0
        extra_field_keys = tuple(k for k in data if k not in self._DEFAULT_FIELD_KEYS)
        existing_json_schema_extra = data.get("json_schema_extra") or {}
        json_schema_extra = {
            **existing_json_schema_extra,
            **{k: data[k] for k in extra_field_keys},
        }
        if json_schema_extra:
            data["json_schema_extra"] = json_schema_extra
            for key in extra_field_keys:
                data.pop(key)

    def _update_alias_for_alias_generator(self, data: dict[str, Any]) -> None:
        if self.name is None or self.is_pydantic_extra_field:
            return
        if (generator_name := self._alias_generator_name_from_parent()) is None:
            return
        alias = data.get("alias")
        if alias is None and self._automatic_alias_disabled_for_alias_generator():
            return
        if (wire_name := alias if alias is not None else self.original_name) is None:
            return
        if _generate_alias(generator_name, self.name) == wire_name:
            data.pop("alias", None)
            return
        data["alias"] = wire_name

    def _alias_generator_name_from_parent(self) -> str | None:
        if self.parent is None:
            return None
        alias_generator = self.parent.extra_template_data.get(_ALIAS_GENERATOR_TEMPLATE_DATA_KEY)
        if alias_generator is None:
            alias_generator = self.parent.extra_template_data.get(_ALIAS_GENERATOR_INTERNAL_KEY)
        return _alias_generator_name(alias_generator)

    def _automatic_alias_disabled_for_alias_generator(self) -> bool:
        if self.parent is None:
            return False
        return bool(self.parent.extra_template_data.get(_NO_ALIAS_INTERNAL_KEY))

    def _has_discriminator_in_data_type(self) -> bool:
        """Check if any nested DataType has a discriminator."""
        if not self.data_type.discriminator and not self.data_type.data_types and self.data_type.dict_key is None:
            return False
        return any(dt.discriminator for dt in self.data_type.all_data_types)

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get all required imports including AliasChoices and Field for discriminator."""
        base_imports = super().imports
        extra_imports: list[Import] = []
        if self.use_missing_sentinel_default:
            extra_imports.append(IMPORT_MISSING)
            if not self._use_union_operator and IMPORT_UNION not in base_imports:
                extra_imports.append(IMPORT_UNION)
        if self.is_class_var:
            extra_imports.append(IMPORT_CLASSVAR)
        if self.validation_aliases:
            extra_imports.append(IMPORT_ALIAS_CHOICES)
        if IMPORT_ANNOTATED in base_imports and self._has_discriminator_in_data_type():
            extra_imports.append(IMPORT_FIELD)
        if self.use_pydantic_extra_annotations_dict:
            extra_imports.append(IMPORT_DICT)
        if extra_imports:
            return chain_as_tuple(base_imports, tuple(extra_imports))
        return base_imports


_LOOKAROUND_PATTERN: re.Pattern[str] = re.compile(r"\(\?<?[=!]")


if TYPE_CHECKING:

    class _ParserSimpleFieldData(TypedDict, total=False):
        name: str | None
        default: object | None
        required: bool
        alias: str | None
        validation_aliases: list[str] | None
        serialization_alias: str | None
        data_type: DataType
        constraints: Constraints | dict[str, object] | None
        strip_default_none: bool
        nullable: bool | None
        extras: dict[str, object] | None
        use_annotated: bool
        use_serialize_as_any: bool
        has_default: bool
        use_field_description: bool
        use_field_description_example: bool
        use_inline_field_description: bool
        const: bool
        original_name: str | None
        use_default_kwarg: bool
        use_missing_sentinel: bool
        type_has_null: bool | None
        read_only: bool
        write_only: bool
        use_frozen_field: bool
        use_serialization_alias: bool
        use_default_factory_for_optional_nested_models: bool
        use_default_with_required: bool


_PARSER_SIMPLE_FIELD_DEFAULTS = MappingProxyType({
    name: None if field_info.is_required() or field_info.default_factory is not None else field_info.default
    for name, field_info in DataModelField.model_fields.items()
})
_PARSER_SIMPLE_FIELD_HAS_PRIVATE_STATE = DataModelField.__pydantic_post_init__ is not None
_SET_PARSER_FIELD_ATTRIBUTE = object.__setattr__


def _construct_parser_simple_field(**data: Unpack[_ParserSimpleFieldData]) -> DataModelField:
    """Construct a parser-normalized simple field without Pydantic validation."""
    match (
        data.get("constraints"),
        data.get("extras"),
        data.get("const", False),
    ):
        case (None, None | {} as extras, False) if not extras and "data_type" in data:
            pass
        case _:
            return DataModelField(**data)

    # Keep Pydantic's private instance layout in this one compatibility boundary.
    values = _PARSER_SIMPLE_FIELD_DEFAULTS.copy()
    values.update(data)
    values["extras"] = {}
    field = object.__new__(DataModelField)
    _SET_PARSER_FIELD_ATTRIBUTE(field, "__dict__", values)
    _SET_PARSER_FIELD_ATTRIBUTE(field, "__pydantic_fields_set__", set(data))
    _SET_PARSER_FIELD_ATTRIBUTE(field, "__pydantic_extra__", None)
    _SET_PARSER_FIELD_ATTRIBUTE(field, "__pydantic_private__", {} if _PARSER_SIMPLE_FIELD_HAS_PRIVATE_STATE else None)
    if (data_type := field.data_type).reference or data_type.data_types:
        data_type.parent = field
    return field


def has_lookaround_pattern(
    fields: list[DataModelFieldBase],
    *,
    follow_references: bool = False,
    _visited: set[int] | None = None,
) -> bool:
    """Check if any field has a regex pattern with lookaround assertions.

    When ``follow_references`` is True, also inspect patterns reachable through referenced
    models (generated type aliases/root types) -- needed for Pydantic v2 dataclasses, where
    alias patterns are compiled with the consuming dataclass's config rather than their own.
    """
    if _visited is None:
        _visited = set()
    for field in fields:
        pattern = isinstance(field.constraints, Constraints) and field.constraints.pattern
        if pattern and _LOOKAROUND_PATTERN.search(pattern):
            return True
        for data_type in field.data_type.all_data_types:
            pattern = (data_type.kwargs or {}).get("pattern")
            if pattern and _LOOKAROUND_PATTERN.search(pattern):
                return True
            if not follow_references or data_type.reference is None:
                continue
            source = data_type.reference.source
            source_fields = getattr(source, "fields", None)
            if source_fields is not None and id(source) not in _visited:
                _visited.add(id(source))
                if has_lookaround_pattern(source_fields, follow_references=True, _visited=_visited):
                    return True
    return False


class BaseModel(BaseModelBase):
    """Pydantic v2 BaseModel with ConfigDict and pattern-based regex_engine support."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/BaseModel.jinja2"
    SCHEMA_RUNTIME_VALIDATION_HELPERS_TEMPLATE_FILE_PATH: ClassVar[str] = (
        "pydantic_v2/schema_runtime_validation_helpers.jinja2"
    )
    SCHEMA_RUNTIME_VALIDATION_BASE_CLASS_NAME: ClassVar[str] = "_JsonSchemaRuntimeValidationBase"
    _SCHEMA_RUNTIME_VALIDATION_MODULE_PLAN_CACHE_KEY: ClassVar[str] = "_schema_runtime_validation_module_plan"
    _CORE_VALIDATION_BASE_MARKER: ClassVar[str] = "_core_validation_base"
    _PROPERTY_COUNT_VALIDATION_BASE_MARKER: ClassVar[str] = "_property_count_validation_base"
    BASE_CLASS: ClassVar[str] = "pydantic.BaseModel"
    BASE_CLASS_NAME: ClassVar[str] = "BaseModel"
    BASE_CLASS_ALIAS: ClassVar[str] = "_BaseModel"
    SUPPORTS_TREE_SCOPE_REUSE_MODEL_INHERITANCE: ClassVar[bool] = True
    FIELD_NAME_MODEL_TYPE: ClassVar[ModelType] = ModelType.PYDANTIC
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_INHERITED_DISCRIMINATOR_ENUM: ClassVar[bool] = True
    SUPPORTS_FIELD_RENAMING: ClassVar[bool] = True
    SUPPORTS_ANNOTATED_CONSTRAINTS: ClassVar[bool] = True
    ANNOTATED_CONSTRAINTS_CONTEXT: ClassVar[object | None] = _ANNOTATED_CONSTRAINTS_CONTEXT
    SUPPORTS_CONFIG_EXTRA: ClassVar[bool] = True
    SUPPORTS_ARBITRARY_TYPES_ALLOWED: ClassVar[bool] = True
    CUSTOM_TEMPLATE_ADAPTER = staticmethod(_adapt_legacy_pydantic_extra_template)
    _INCLUDE_DICT_KEY_REFERENCE_CLASSES = _get_dict_key_reference_classes_capability()
    TYPED_EXTRA_FIELD_NAME: ClassVar[str] = "__pydantic_extra__"
    TYPED_EXTRA_PLAIN_ANNOTATION_TEMPLATE_DATA_KEY: ClassVar[str] = "pydantic_extra_plain_annotation"
    # In Pydantic 2.11+, populate_by_name is deprecated in favor of validate_by_name + validate_by_alias
    # Default to V2 compatible (populate_by_name) unless target_pydantic_version is specified
    _CONFIG_ATTRIBUTES_V2: ClassVar[list[ConfigAttribute]] = [
        ConfigAttribute("allow_population_by_field_name", "populate_by_name", False),  # noqa: FBT003
        ConfigAttribute("populate_by_name", "populate_by_name", False),  # noqa: FBT003
        ConfigAttribute("allow_mutation", "frozen", True),  # noqa: FBT003
        ConfigAttribute("frozen", "frozen", False),  # noqa: FBT003
        ConfigAttribute("use_attribute_docstrings", "use_attribute_docstrings", False),  # noqa: FBT003
    ]
    _CONFIG_ATTRIBUTES_V2_11: ClassVar[list[ConfigAttribute]] = [
        ConfigAttribute("allow_population_by_field_name", "validate_by_name", False),  # noqa: FBT003
        ConfigAttribute("populate_by_name", "validate_by_name", False),  # noqa: FBT003
        ConfigAttribute("allow_mutation", "frozen", True),  # noqa: FBT003
        ConfigAttribute("frozen", "frozen", False),  # noqa: FBT003
        ConfigAttribute("use_attribute_docstrings", "use_attribute_docstrings", False),  # noqa: FBT003
    ]

    @classmethod
    def resolve_nested_constrained_model_type(
        cls,
        configured_root_model_type: type[DataModel],  # noqa: ARG003
    ) -> type[DataModel]:
        """Use a runtime-compatible alias for nested constrained values."""
        from datamodel_code_generator.model.type_alias import TypeAliasTypeBackport  # noqa: PLC0415

        return TypeAliasTypeBackport

    @classmethod
    def prepare_module_code(cls, models: list[DataModel]) -> None:
        """Plan shared schema validation helpers before imports are collected."""
        cls._get_schema_runtime_validation_module_plan(models, scan_later_models=True)

    @classmethod
    def render_module_code(cls, models: list[DataModel]) -> str:
        """Render shared schema runtime validation helpers for the module once."""
        if (module_plan := cls._get_schema_runtime_validation_module_plan(models)) is None:
            return ""

        _runtime_models, runtime_validations = cls._get_schema_runtime_validation_models(models)
        if not module_plan.has_property_count:
            return cls._render_core_schema_runtime_validation_helpers(
                module_plan.base_class_name,
                runtime_validations,
                models,
            )
        helper_base_class_names = dict(module_plan.helper_base_class_names)
        if not helper_base_class_names:
            return ""
        return cls._render_property_count_validation_helpers(
            helper_base_class_names,
            runtime_validations,
            models,
        )

    @classmethod
    def _get_schema_runtime_validation_module_plan(
        cls,
        models: list[DataModel],
        *,
        scan_later_models: bool = False,
    ) -> SchemaRuntimeValidationModulePlan | None:
        """Build one compact helper plan, reusing it for the final renderer."""
        if not models or (
            (module_plan := models[0].__dict__.get(cls._SCHEMA_RUNTIME_VALIDATION_MODULE_PLAN_CACHE_KEY)) is None
            and not models[0].extra_template_data.get("schema_runtime_validation_enabled")
            and (
                not scan_later_models
                or not any(model.extra_template_data.get("schema_runtime_validation_enabled") for model in models[1:])
            )
        ):
            return None
        if module_plan is not None:
            return cast("SchemaRuntimeValidationModulePlan", module_plan)

        from datamodel_code_generator.model.pydantic_v2._schema_runtime_validation import (  # noqa: PLC0415
            SchemaRuntimeValidationModulePlan,
            plan_schema_runtime_validation_bases,
        )

        runtime_models, runtime_validations = cls._get_schema_runtime_validation_models(models)
        if not runtime_models:
            return None

        configured_base_class_name = runtime_models[0].extra_template_data.get("schema_validator_base_class_name")
        normalized_base_class_name = (
            _normalize_string(configured_base_class_name) if isinstance(configured_base_class_name, str) else None
        )
        base_class_name = (
            normalized_base_class_name
            if (
                normalized_base_class_name is not None
                and normalized_base_class_name.isidentifier()
                and not keyword.iskeyword(normalized_base_class_name)
            )
            else cls.SCHEMA_RUNTIME_VALIDATION_BASE_CLASS_NAME
        )
        runtime_validation_by_model = {
            id(model): runtime_validations[index] for index, model in enumerate(runtime_models)
        }
        has_property_count = any(runtime_validation.property_count for runtime_validation in runtime_validations)
        if not has_property_count:
            local_model_ids = {id(model) for model in models}
            for model in runtime_models:
                model._set_internal_template_data(  # noqa: SLF001
                    "schema_runtime_validation_base_class_name",
                    base_class_name,
                )
                model._set_internal_template_data(  # noqa: SLF001
                    "schema_runtime_validation_use_base",
                    not cls._inherits_schema_runtime_validation_base(
                        model,
                        seen=set(),
                        local_model_ids=local_model_ids,
                    ),
                )
            cls._add_schema_runtime_validation_helper_imports(
                runtime_models[0],
                runtime_validations,
                has_local_core_helper=True,
                uses_generated_generic_base_class=cls._has_generated_generic_base_class(models),
            )
            module_plan = SchemaRuntimeValidationModulePlan(
                base_class_name,
                has_property_count=False,
            )
            models[0].__dict__[cls._SCHEMA_RUNTIME_VALIDATION_MODULE_PLAN_CACHE_KEY] = module_plan
            return module_plan

        missing_capabilities_by_model = plan_schema_runtime_validation_bases(
            runtime_models,
            runtime_validation_by_model,
            get_base_models=cls._get_schema_runtime_validation_base_models,
            get_external_capabilities=cls._get_external_schema_runtime_validation_capabilities,
            get_model_requirements=cls._get_schema_runtime_validation_requirements,
        )
        helper_capabilities = frozenset(missing_capabilities_by_model.values()) - {(False, False)}
        if not helper_capabilities:
            for model in runtime_models:
                cls._set_schema_runtime_validation_base(model, None, (False, False))
            module_plan = SchemaRuntimeValidationModulePlan(
                base_class_name,
                has_property_count=True,
            )
            models[0].__dict__[cls._SCHEMA_RUNTIME_VALIDATION_MODULE_PLAN_CACHE_KEY] = module_plan
            return module_plan

        helper_base_class_names = cls._get_schema_runtime_validation_base_class_names(
            base_class_name,
            helper_capabilities,
            models,
        )
        for model in runtime_models:
            missing_capabilities = missing_capabilities_by_model[id(model)]
            cls._set_schema_runtime_validation_base(
                model,
                helper_base_class_names.get(missing_capabilities),
                missing_capabilities,
            )
        cls._add_schema_runtime_validation_helper_imports(
            runtime_models[0],
            runtime_validations,
            has_local_core_helper=any(capabilities[0] for capabilities in helper_base_class_names),
            uses_generated_generic_base_class=cls._has_generated_generic_base_class(models),
        )
        module_plan = SchemaRuntimeValidationModulePlan(
            base_class_name,
            has_property_count=True,
            helper_base_class_names=tuple(helper_base_class_names.items()),
        )
        models[0].__dict__[cls._SCHEMA_RUNTIME_VALIDATION_MODULE_PLAN_CACHE_KEY] = module_plan
        return module_plan

    @classmethod
    def _has_local_generated_generic_base_class(cls, models: list[DataModel]) -> bool:
        """Return whether this module renders its configured ``BaseModel`` before helpers."""
        if not models or models[0].class_name != cls.BASE_CLASS_NAME:
            return False
        return models[0].base_class == cls.BASE_CLASS_ALIAS

    @classmethod
    def _has_generated_generic_base_class(cls, models: list[DataModel]) -> bool:
        """Return whether local helpers can inherit a generated generic ``BaseModel``."""
        if cls._has_local_generated_generic_base_class(models):
            return True
        return any(
            isinstance(base_class.reference.source, DataModel)
            and base_class.reference.source.class_name == cls.BASE_CLASS_NAME
            and base_class.reference.source.base_class == cls.BASE_CLASS_ALIAS
            for model in models
            for base_class in model.base_classes
            if base_class.reference is not None
        )

    @classmethod
    def get_module_code_insertion_index(cls, models: list[DataModel]) -> int:
        """Emit a generated generic base before helpers that inherit from it."""
        return 1 if cls._has_local_generated_generic_base_class(models) else 0

    def invalidate_render_caches(self) -> None:
        """Clear the compact module plan with the model's other render caches."""
        super().invalidate_render_caches()
        self.__dict__.pop(self._SCHEMA_RUNTIME_VALIDATION_MODULE_PLAN_CACHE_KEY, None)

    @classmethod
    def invalidate_module_code_cache(cls, models: list[DataModel]) -> None:
        """Discard the one module plan after parser-side import collision renames."""
        if models:
            models[0].__dict__.pop(cls._SCHEMA_RUNTIME_VALIDATION_MODULE_PLAN_CACHE_KEY, None)

    @staticmethod
    def _get_schema_runtime_validation_models(
        models: list[DataModel],
    ) -> tuple[list[DataModel], list[SchemaRuntimeValidation]]:
        """Return parser-owned runtime-validation models and their metadata."""
        runtime_models = [
            model
            for model in models
            if _is_internal_schema_runtime_validation(
                model._internal_template_data.get("schema_runtime_validation")  # noqa: SLF001
            )
            and model._internal_template_data["schema_runtime_validation"]  # noqa: SLF001
        ]
        runtime_validations = [
            model._internal_template_data["schema_runtime_validation"]  # noqa: SLF001
            for model in runtime_models
        ]
        return runtime_models, runtime_validations

    @classmethod
    def _add_schema_runtime_validation_helper_imports(
        cls,
        model: DataModel,
        runtime_validations: list[SchemaRuntimeValidation],
        *,
        has_local_core_helper: bool,
        uses_generated_generic_base_class: bool = False,
    ) -> None:
        """Add imports only when this module renders a shared runtime helper."""
        additional_imports = model._additional_imports  # noqa: SLF001
        helper_imports = (IMPORT_MODEL_VALIDATOR, IMPORT_ANY, IMPORT_CLASSVAR)
        if not uses_generated_generic_base_class:
            helper_imports += (IMPORT_BASE_MODEL,)
        for import_ in helper_imports:
            if import_ not in additional_imports:
                additional_imports.append(import_)
        has_unique_items_regex_paths = any(
            unique_items_path_uses_regex(rule.path)
            for runtime_validation in runtime_validations
            for rule in runtime_validation.unique_items
        )
        has_pattern_properties = any(
            runtime_validation.pattern_properties for runtime_validation in runtime_validations
        )
        if has_local_core_helper and (has_pattern_properties or has_unique_items_regex_paths):
            helper_validation_imports = (
                (Import(import_="re"), IMPORT_TYPE_ADAPTER) if has_pattern_properties else (Import(import_="re"),)
            )
            for import_ in helper_validation_imports:
                if import_ not in additional_imports:
                    additional_imports.append(import_)
        model.clear_imports_cache()

    @staticmethod
    def _has_core_schema_runtime_validation(runtime_validation: SchemaRuntimeValidation) -> bool:
        """Return whether a validation needs the existing template-rendered helper."""
        return bool(
            runtime_validation.pattern_properties
            or runtime_validation.required_groups
            or runtime_validation.conditional_required
            or runtime_validation.unique_items
        )

    @staticmethod
    def _get_schema_runtime_validation_base_models(model: DataModel) -> list[DataModel]:
        """Return generated model bases that can supply runtime-validation helpers."""
        return [
            base_class.reference.source
            for base_class in model.base_classes
            if base_class.reference and isinstance(base_class.reference.source, DataModel)
        ]

    @classmethod
    def _get_external_schema_runtime_validation_capabilities(cls, model: DataModel) -> tuple[bool, bool]:
        """Return reusable capabilities supplied by another generated module.

        Core helpers are specialized to the rules rendered in their module;
        reusing one could shadow a child rule with a method it does not have.
        Property-count helpers are invariant, so they remain reusable.
        """
        internal_template_data = model._internal_template_data  # noqa: SLF001
        runtime_validation = internal_template_data.get("schema_runtime_validation")
        if isinstance(runtime_validation, SchemaRuntimeValidation) and _is_internal_schema_runtime_validation(
            runtime_validation
        ):
            property_count = bool(runtime_validation.property_count)
        else:
            property_count = False
        return (
            False,
            property_count or bool(internal_template_data.get(cls._PROPERTY_COUNT_VALIDATION_BASE_MARKER)),
        )

    @classmethod
    def _set_schema_runtime_validation_base(
        cls,
        model: DataModel,
        base_class_name: str | None,
        capabilities: tuple[bool, bool],
    ) -> None:
        """Record the one local helper base, if any, used by a generated model."""
        if base_class_name is not None:
            model._set_internal_template_data("schema_runtime_validation_base_class_name", base_class_name)  # noqa: SLF001
        uses_base_class = capabilities != (False, False)
        model._set_internal_template_data("schema_runtime_validation_use_base", uses_base_class)  # noqa: SLF001
        model._set_internal_template_data(cls._CORE_VALIDATION_BASE_MARKER, capabilities[0])  # noqa: SLF001
        model._set_internal_template_data(cls._PROPERTY_COUNT_VALIDATION_BASE_MARKER, capabilities[1])  # noqa: SLF001

    @classmethod
    def _get_schema_runtime_validation_requirements(
        cls,
        model: DataModel,
        runtime_validation: SchemaRuntimeValidation,
    ) -> tuple[bool, bool]:
        """Return the helper capabilities required by one generated model."""
        return (
            cls._has_core_schema_runtime_validation(runtime_validation)
            or (bool(runtime_validation.property_count) and cls._has_custom_schema_runtime_validation_helper(model)),
            bool(runtime_validation.property_count),
        )

    @classmethod
    def _has_custom_schema_runtime_validation_helper(cls, model: DataModel) -> bool:
        """Return whether this model overrides the shared schema-validator helper template."""
        return bool(
            model.custom_template_dir
            and (model.custom_template_dir / cls.SCHEMA_RUNTIME_VALIDATION_HELPERS_TEMPLATE_FILE_PATH).is_file()
        )

    @classmethod
    def _get_schema_runtime_validation_base_class_names(
        cls,
        base_class_name: str,
        helper_capabilities: frozenset[tuple[bool, bool]],
        models: list[DataModel],
    ) -> dict[tuple[bool, bool], str]:
        """Allocate at most one shared helper for each missing capability set."""
        if (True, True) in helper_capabilities:
            primary_capabilities = (True, True)
        elif (False, True) in helper_capabilities:
            primary_capabilities = (False, True)
        else:
            primary_capabilities = (True, False)
        base_class_names = {primary_capabilities: base_class_name}
        reserved_names = {base_class_name}
        for capabilities, suffix in (
            ((True, False), "Core"),
            ((False, True), "PropertyCount"),
            ((True, True), "Combined"),
        ):
            if capabilities not in helper_capabilities or capabilities == primary_capabilities:
                continue
            base_class_names[capabilities] = cls._get_unique_schema_runtime_validation_base_class_name(
                base_class_name,
                suffix,
                models,
                reserved_names,
            )
            reserved_names.add(base_class_names[capabilities])
        return base_class_names

    @staticmethod
    def _get_unique_schema_runtime_validation_base_class_name(
        base_class_name: str,
        suffix: str,
        models: list[DataModel],
        reserved_names: set[str] | None = None,
    ) -> str:
        """Choose a synthetic helper name that cannot collide with generated models."""
        class_names = {model.class_name for model in models}
        class_names.update(
            base_class.reference.source.class_name
            for model in models
            for base_class in model.base_classes
            if base_class.reference and isinstance(base_class.reference.source, DataModel)
        )
        class_names.update(
            data_type.reference.source.class_name
            for model in models
            for field in model.fields
            for data_type in field.data_type.all_data_types
            if data_type.reference and isinstance(data_type.reference.source, DataModel)
        )
        if reserved_names:
            class_names.update(reserved_names)
        candidate = f"{base_class_name}{suffix}"
        number = 2
        while candidate in class_names:
            candidate = f"{base_class_name}{suffix}{number}"
            number += 1
        return candidate

    @classmethod
    def _render_property_count_validation_helpers(
        cls,
        helper_base_class_names: dict[tuple[bool, bool], str],
        runtime_validations: list[SchemaRuntimeValidation],
        models: list[DataModel],
    ) -> str:
        """Render only the shared helpers needed for local missing capabilities."""
        from datamodel_code_generator.model.pydantic_v2._schema_runtime_validation import (  # noqa: PLC0415
            render_property_count_validation_base,
        )

        core_runtime_validations = [
            runtime_validation
            for runtime_validation in runtime_validations
            if cls._has_core_schema_runtime_validation(runtime_validation)
        ]
        requires_combined_base = (True, True) in helper_base_class_names
        core_base_class_name = helper_base_class_names.get((True, False))
        if requires_combined_base and core_base_class_name is None:
            core_base_class_name = cls._get_unique_schema_runtime_validation_base_class_name(
                helper_base_class_names[True, True],
                "Core",
                models,
                set(helper_base_class_names.values()),
            )

        helpers: list[str] = []
        if core_base_class_name is not None:
            helpers.append(
                cls._render_core_schema_runtime_validation_helpers(
                    core_base_class_name,
                    core_runtime_validations,
                    models,
                ).rstrip()
            )
        if (property_base_class_name := helper_base_class_names.get((False, True))) is not None:
            helpers.append(render_property_count_validation_base(property_base_class_name, "BaseModel"))
        if (combined_base_class_name := helper_base_class_names.get((True, True))) is not None:
            helpers.append(
                render_property_count_validation_base(
                    combined_base_class_name,
                    cast("str", core_base_class_name),
                )
            )
        return "\n\n\n".join(helpers) + "\n"

    @classmethod
    def _render_core_schema_runtime_validation_helpers(
        cls,
        base_class_name: str,
        runtime_validations: list[SchemaRuntimeValidation],
        models: list[DataModel],
    ) -> str:
        """Render the unchanged core runtime-validation helper template."""
        custom_template_dir = next(
            (model.custom_template_dir for model in models if model.custom_template_dir is not None),
            None,
        )
        context = {
            "schema_runtime_validation_base_class_name": base_class_name,
            "has_pattern_properties": any(
                runtime_validation.pattern_properties for runtime_validation in runtime_validations
            ),
            "has_required_groups": any(
                runtime_validation.required_groups for runtime_validation in runtime_validations
            ),
            "has_conditional_required": any(
                runtime_validation.conditional_required for runtime_validation in runtime_validations
            ),
            "has_unique_items": any(runtime_validation.unique_items for runtime_validation in runtime_validations),
            "has_unique_items_regex_paths": any(
                unique_items_path_uses_regex(rule.path)
                for runtime_validation in runtime_validations
                for rule in runtime_validation.unique_items
            ),
        }
        if custom_template_dir is None and cls.__module__.startswith("datamodel_code_generator.model."):
            from datamodel_code_generator.model._compiled_templates import get_builtin_renderer  # noqa: PLC0415

            if renderer := get_builtin_renderer(cls.SCHEMA_RUNTIME_VALIDATION_HELPERS_TEMPLATE_FILE_PATH):
                return renderer(**context)

        if context["has_unique_items"] and custom_template_dir is not None:
            custom_template_path = custom_template_dir / cls.SCHEMA_RUNTIME_VALIDATION_HELPERS_TEMPLATE_FILE_PATH
            if custom_template_path.is_file():
                msg = (
                    f"Custom schema runtime validation helper {custom_template_path} overrides do not yet support "
                    "generated uniqueItems validation. Remove the helper override or disable schema validators."
                )
                raise Error(msg)
        template = _get_template_with_custom_dir(
            Path(cls.SCHEMA_RUNTIME_VALIDATION_HELPERS_TEMPLATE_FILE_PATH),
            custom_template_dir,
        )
        return template.render(**context)

    @classmethod
    def _inherits_schema_runtime_validation_base(
        cls,
        model: DataModel,
        *,
        seen: set[str],
        local_model_ids: set[int] | None = None,
    ) -> bool:
        """Return whether a model already inherits the generated runtime validation base."""
        if model.reference.path in seen:
            return False
        seen.add(model.reference.path)
        for base_class in model.base_classes:
            if not base_class.reference or not isinstance(base_class.reference.source, DataModel):
                continue
            base_model = base_class.reference.source
            if local_model_ids is not None and id(base_model) not in local_model_ids:
                continue
            if (
                _is_internal_schema_runtime_validation(
                    base_model._internal_template_data.get("schema_runtime_validation")  # noqa: SLF001
                )
                and base_model._internal_template_data["schema_runtime_validation"]  # noqa: SLF001
            ):
                return True
            if cls._inherits_schema_runtime_validation_base(
                base_model,
                seen=seen,
                local_model_ids=local_model_ids,
            ):
                return True
        return False

    @classmethod
    def create_typed_extra_field(
        cls,
        *,
        field_model: type[DataModelFieldBase],
        data_type: DataType,
    ) -> DataModelFieldBase:
        """Create the Pydantic v2 typed extra field."""
        return field_model(
            name=cls.TYPED_EXTRA_FIELD_NAME,
            data_type=data_type,
            required=True,
            original_name=cls.TYPED_EXTRA_FIELD_NAME,
        )

    def __init__(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        decorators: list[str] | None = None,
        base_classes: list[Reference] | None = None,
        custom_base_class: str | list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, Any] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        treat_dot_as_module: bool | None = None,
    ) -> None:
        """Initialize BaseModel with ConfigDict generation from template data."""
        super().__init__(
            reference=reference,
            fields=fields,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            path=path,
            description=description,
            default=default,
            nullable=nullable,
            keyword_only=keyword_only,
            treat_dot_as_module=treat_dot_as_module,
        )
        self._prepare_schema_runtime_validation_config()
        config_parameters: dict[str, Any] = dict(
            build_base_config_parameters(
                extra_template_data=self.extra_template_data,
                all_data_types=self.all_data_types if self.SUPPORTS_ARBITRARY_TYPES_ALLOWED else (),
                config_attributes_v2=self._CONFIG_ATTRIBUTES_V2,
                config_attributes_v2_11=self._CONFIG_ATTRIBUTES_V2_11,
                include_extra=self.SUPPORTS_CONFIG_EXTRA,
            )
        )

        if has_lookaround_pattern(self.fields):
            config_parameters["regex_engine"] = '"python-re"'

        if alias_generator := _alias_generator_name(self.extra_template_data.get(_ALIAS_GENERATOR_TEMPLATE_DATA_KEY)):
            config_parameters[_ALIAS_GENERATOR_TEMPLATE_DATA_KEY] = alias_generator
            self._additional_imports.append(_ALIAS_GENERATOR_IMPORTS[alias_generator])

        config = self.extra_template_data.get("config")
        if isinstance(config, dict):
            config_parameters.update(dict(config.items()))
        elif config_items := _config_dict_items(config):
            config_parameters.update(dict(config_items))

        # Handle json_schema_extra from schema extensions (x-* fields)
        model_extras = self.extra_template_data.get("model_extras")
        if model_extras:
            existing = cast("dict[str, Any]", config_parameters.get("json_schema_extra") or {})
            config_parameters["json_schema_extra"] = {**existing, **model_extras}

        if config_parameters:
            from datamodel_code_generator.model.pydantic_v2 import ConfigDict  # noqa: PLC0415

            self.extra_template_data["config"] = ConfigDict.model_validate(config_parameters)
            self._set_internal_template_data(
                _CONFIG_ITEMS_TEMPLATE_DATA_KEY,
                _safe_config_dict_items(self.extra_template_data["config"]),
            )
            self._additional_imports.append(IMPORT_CONFIG_DICT)
        else:
            self.extra_template_data.pop("config", None)
            self._pop_internal_template_data(_CONFIG_ITEMS_TEMPLATE_DATA_KEY)

        self._process_schema_runtime_validation()
        self._process_validators()

    def _get_schema_runtime_validation(self) -> SchemaRuntimeValidation | None:
        internal_runtime_validation = self._internal_template_data.get("schema_runtime_validation")
        if _is_internal_schema_runtime_validation(internal_runtime_validation) and internal_runtime_validation:
            return internal_runtime_validation
        runtime_validation = self.extra_template_data.get("schema_runtime_validation")
        if _is_internal_schema_runtime_validation(runtime_validation) and runtime_validation:
            return runtime_validation
        return None

    def _prepare_schema_runtime_validation_config(self) -> None:
        """Prepare Pydantic config required by schema-derived runtime validators."""
        runtime_validation = self._get_schema_runtime_validation()
        if runtime_validation is None:
            return
        self.extra_template_data.pop("schema_runtime_validation", None)
        self._set_internal_template_data("schema_runtime_validation", runtime_validation)
        if runtime_validation.pattern_properties:
            self.extra_template_data["force_extra_allow"] = True

    def _process_schema_runtime_validation(self) -> None:
        """Add imports required by schema-derived runtime validators."""
        runtime_validation = self._get_schema_runtime_validation()
        if runtime_validation is None:
            return

        if (property_count_rule := runtime_validation.property_count) is not None:
            from datamodel_code_generator.model.pydantic_v2._schema_runtime_validation import (  # noqa: PLC0415
                render_property_count_rule,
            )

            property_count_line = render_property_count_rule(property_count_rule)
            if property_count_line not in self._internal_template_data.get("class_body_lines", ()):
                self._append_internal_template_data("class_body_lines", property_count_line)

        if runtime_validation.unique_items:
            from datamodel_code_generator.model.pydantic_v2._schema_runtime_validation import (  # noqa: PLC0415
                render_unique_items_rules,
            )

            unique_items_lines = render_unique_items_rules(runtime_validation.unique_items)
            class_body_lines = self._internal_template_data.get("class_body_lines", ())
            if unique_items_lines[0] not in class_body_lines:
                for line in unique_items_lines:
                    self._append_internal_template_data("class_body_lines", line)

        if runtime_validation.property_count is not None or runtime_validation.unique_items:
            self._additional_imports.append(IMPORT_ANY)
            self._additional_imports.append(IMPORT_CLASSVAR)

        for data_type in runtime_validation.data_types:
            self._additional_imports.extend(data_type.all_imports)

    def _process_validators(self) -> None:
        """Process validator definitions and prepare them for template rendering."""
        self.extra_template_data.pop("prepared_validators", None)
        validators = self.extra_template_data.get("validators")
        if not validators:
            return

        from datamodel_code_generator.validators import format_validation_error, normalize_validators  # noqa: PLC0415

        try:
            validators = normalize_validators(validators)
        except ValidationError as e:
            msg = f"Invalid validators configuration: {format_validation_error(e)}"
            raise Error(msg) from e

        prepared_validators: list[dict[str, Any]] = []
        scoped_resolver = ModelResolver(custom_class_name_generator=lambda name: name)
        for validator in validators:
            fields = validator.get("fields") or [validator.get("field")]
            fields = [f for f in fields if f]
            if not fields:
                continue

            function_path: str = validator["function"]
            function_name = function_path.rsplit(".", 1)[-1]
            mode = validator.get("mode", "after")

            fields_str = ", ".join(repr(f) for f in fields)

            base_method_name = f"{function_name}_validator"
            method_name = scoped_resolver.add([base_method_name], base_method_name, unique=True, class_name=True).name

            mode_str = f"mode={mode!r}"

            prepared_validators.append({
                "fields_str": fields_str,
                "mode_str": mode_str,
                "method_name": method_name,
                "function_name": function_name,
                "mode": mode,
            })

            self._additional_imports.append(Import.from_full_path(function_path))

        if prepared_validators:
            self._set_internal_template_data("prepared_validators", prepared_validators)
            self._additional_imports.append(IMPORT_FIELD_VALIDATOR)
            self._additional_imports.append(IMPORT_ANY)

            modes = {v["mode"] for v in prepared_validators}
            if modes - {"plain"}:
                self._additional_imports.append(IMPORT_VALIDATION_INFO)
            if "wrap" in modes:
                self._additional_imports.append(IMPORT_VALIDATOR_FUNCTION_WRAP_HANDLER)

    @classmethod
    def create_base_class_model(
        cls,
        config: dict[str, Any],
        reference: Reference,
        custom_template_dir: Path | None = None,
        keyword_only: bool = False,  # noqa: FBT001, FBT002
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
    ) -> BaseModel | None:
        """Create a shared base class model for DRY configuration.

        Creates a BaseModel that inherits from pydantic's BaseModel (aliased as _BaseModel)
        with the specified configuration. Updates the reference path and name in place.
        """
        reference.path = f"#/{cls.BASE_CLASS_NAME}"
        reference.name = cls.BASE_CLASS_NAME

        extra_data: defaultdict[str, dict[str, Any]] = defaultdict(dict)
        for key, value in config.items():
            extra_data[ALL_MODEL][key] = value

        base_model = cls(
            reference=reference,
            fields=[],
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_data,
            keyword_only=keyword_only,
            treat_dot_as_module=treat_dot_as_module,
        )

        base_model.base_classes = [BaseClassDataType(type=cls.BASE_CLASS_ALIAS)]
        base_model._additional_imports = [
            imp
            for imp in base_model._additional_imports
            if not (imp.from_ == IMPORT_BASE_MODEL.from_ and imp.import_ == IMPORT_BASE_MODEL.import_)
        ]
        base_model._additional_imports.append(
            Import(from_=IMPORT_BASE_MODEL.from_, import_=IMPORT_BASE_MODEL.import_, alias=cls.BASE_CLASS_ALIAS)
        )

        return base_model


_rebuild_model_with_datamodel_namespace(DataModelField)
