"""Built-in immutable option presets for the CLI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Literal

from datamodel_code_generator._registry_render import _render_registry_json
from datamodel_code_generator.config import BaseGenerateConfig
from datamodel_code_generator.enums import DataModelType, InputFileType

if TYPE_CHECKING:
    from typing_extensions import Unpack

    from datamodel_code_generator._types.generate_config_dict import BaseGenerateConfig as BaseGenerateConfigDict
    from datamodel_code_generator.format import PythonVersion

PresetFormat = Literal["json", "markdown"]


class PresetError(Exception):
    """Raised when a preset cannot be resolved."""


class PresetName(str, Enum):
    """Available immutable preset names."""

    Standard20260617 = "standard-20260617"


@dataclass(frozen=True, slots=True)
class PresetContext:
    """Context required to resolve a preset."""

    input_file_type: InputFileType
    output_model_type: DataModelType
    target_python_version: PythonVersion


@dataclass(frozen=True, slots=True)
class PresetInfo:
    """Public preset metadata used by CLI docs."""

    name: PresetName
    summary: str
    description: str
    requires_target_python_version: bool
    option_groups: tuple[PresetOptionGroup, ...]


@dataclass(frozen=True, slots=True)
class PresetOptionGroup:
    """Documented option group for a preset."""

    title: str
    configs: tuple[BaseGenerateConfig, ...]
    description: str
    input_file_types: frozenset[InputFileType] = frozenset()
    output_model_types: frozenset[DataModelType] = frozenset()
    requires_python_strenum: bool = False

    def __post_init__(self) -> None:
        """Validate that each documented config maps to one Boolean CLI option."""
        seen_fields: set[str] = set()
        for config in self.configs:
            updates = preset_config_updates(config)
            if len(updates) != 1:
                msg = f"Preset option group {self.title!r} contains a config with {len(updates)} explicit fields"
                raise PresetError(msg)
            field_name, value = next(iter(updates.items()))
            if field_name in seen_fields:
                msg = f"Preset option group {self.title!r} defines {field_name!r} more than once"
                raise PresetError(msg)
            seen_fields.add(field_name)
            _config_field_to_cli_option(field_name, value=value)

    @property
    def options(self) -> tuple[str, ...]:
        """Return documented CLI options derived from typed config fields."""
        return tuple(option for config in self.configs for option in _preset_config_cli_options(config))

    def applies_to(self, context: PresetContext) -> bool:
        """Return whether this option group applies to a preset context."""
        if self.input_file_types and context.input_file_type not in self.input_file_types:
            return False
        if self.output_model_types and context.output_model_type not in self.output_model_types:
            return False
        return not self.requires_python_strenum or context.target_python_version.has_strenum


def _preset_config(**values: Unpack[BaseGenerateConfigDict]) -> BaseGenerateConfig:
    """Build a preset config from statically checked GenerateConfig fields."""
    return BaseGenerateConfig.model_validate(values)


def preset_config_updates(config: BaseGenerateConfig) -> dict[str, object]:
    """Return only config values explicitly supplied by a preset."""
    values = config.model_dump(exclude_unset=True)
    return {field_name: values[field_name] for field_name in BaseGenerateConfig.model_fields if field_name in values}


def _merge_preset_configs(*configs: BaseGenerateConfig) -> BaseGenerateConfig:
    """Merge preset configs, with later configs taking precedence."""
    values: dict[str, object] = {}
    for config in configs:
        values.update(preset_config_updates(config))
    return BaseGenerateConfig.model_validate(values)


def _preset_config_cli_options(config: BaseGenerateConfig) -> tuple[str, ...]:
    """Return CLI option names represented by the explicit config fields."""
    return tuple(
        _config_field_to_cli_option(field_name, value=value)
        for field_name, value in preset_config_updates(config).items()
    )


def _config_field_to_cli_option(field_name: str, *, value: object) -> str:
    """Translate a typed config field name to its CLI option spelling."""
    if field_name not in BaseGenerateConfig.model_fields:  # pragma: no cover
        msg = f"Preset field {field_name!r} is not a BaseGenerateConfig field"
        raise PresetError(msg)
    if not isinstance(value, bool):  # pragma: no cover
        msg = f"Preset field {field_name!r} cannot be rendered as a Boolean CLI option"
        raise PresetError(msg)
    option_name = field_name.replace("_", "-")
    return f"--no-{option_name}" if value is False else f"--{option_name}"


_USE_STANDARD_COLLECTIONS = _preset_config(use_standard_collections=True)
_USE_UNION_OPERATOR = _preset_config(use_union_operator=True)
_USE_ANNOTATED = _preset_config(use_annotated=True)
_COLLAPSE_ROOT_MODELS = _preset_config(collapse_root_models=True)
_USE_SPECIALIZED_ENUM = _preset_config(use_specialized_enum=True)
_SNAKE_CASE_FIELD = _preset_config(snake_case_field=True)
_ALLOW_POPULATION_BY_FIELD_NAME = _preset_config(allow_population_by_field_name=True)
_USE_FROZEN_FIELD = _preset_config(use_frozen_field=True)
_USE_STANDARD_PRIMITIVE_TYPES = _preset_config(use_standard_primitive_types=True)

_PRESET_INFOS: tuple[PresetInfo, ...] = (
    PresetInfo(
        name=PresetName.Standard20260617,
        summary="Recommended modern Python output for new projects.",
        description=(
            "This immutable preset enables the project-recommended Python output style for new code. "
            "It is output-model aware and keeps stdlib dataclass and TypedDict keys compatible with their input names."
        ),
        requires_target_python_version=True,
        option_groups=(
            PresetOptionGroup(
                title="All output model types",
                configs=(
                    _USE_STANDARD_COLLECTIONS,
                    _USE_UNION_OPERATOR,
                    _USE_ANNOTATED,
                    _COLLAPSE_ROOT_MODELS,
                ),
                description=(
                    "Use built-in collection syntax, PEP 604 unions, Annotated constraints, and inline root wrappers."
                ),
            ),
            PresetOptionGroup(
                title="Python 3.11+ targets",
                configs=(_USE_SPECIALIZED_ENUM,),
                description="Use StrEnum or IntEnum only when the selected target Python version supports it.",
                requires_python_strenum=True,
            ),
            PresetOptionGroup(
                title="Pydantic v2 BaseModel and dataclass output",
                configs=(
                    _SNAKE_CASE_FIELD,
                    _ALLOW_POPULATION_BY_FIELD_NAME,
                    _USE_FROZEN_FIELD,
                ),
                description=(
                    "Generate Pythonic field names while preserving input aliases and readOnly immutability metadata."
                ),
                output_model_types=frozenset({
                    DataModelType.PydanticV2BaseModel,
                    DataModelType.PydanticV2Dataclass,
                }),
            ),
            PresetOptionGroup(
                title="msgspec Struct output",
                configs=(
                    _SNAKE_CASE_FIELD,
                    _USE_STANDARD_PRIMITIVE_TYPES,
                ),
                description="Generate Pythonic field names with aliases and stdlib primitive types for schema formats.",
                output_model_types=frozenset({DataModelType.MsgspecStruct}),
            ),
            PresetOptionGroup(
                title="stdlib dataclass output",
                configs=(_USE_STANDARD_PRIMITIVE_TYPES,),
                description=(
                    "Use stdlib primitive types without renaming input keys because dataclasses do not carry aliases."
                ),
                output_model_types=frozenset({DataModelType.DataclassesDataclass}),
            ),
            PresetOptionGroup(
                title="TypedDict output",
                configs=(
                    _USE_STANDARD_PRIMITIVE_TYPES,
                    _USE_FROZEN_FIELD,
                ),
                description="Use stdlib primitive types and ReadOnly metadata without renaming dictionary keys.",
                output_model_types=frozenset({DataModelType.TypingTypedDict}),
            ),
        ),
    ),
)


def _validate_preset_infos(infos: tuple[PresetInfo, ...]) -> None:
    """Validate preset metadata invariants at import time."""
    preset_names: set[PresetName] = set()
    for info in infos:
        if info.name in preset_names:
            msg = f"Preset {info.name.value!r} is defined more than once"
            raise PresetError(msg)
        preset_names.add(info.name)

        output_model_groups: dict[DataModelType, str] = {}
        for group in info.option_groups:
            if not group.configs:
                msg = f"Preset option group {group.title!r} does not define any configs"
                raise PresetError(msg)
            for output_model_type in group.output_model_types:
                if output_model_type in output_model_groups:
                    msg = (
                        f"Preset {info.name.value!r} maps {output_model_type.value!r} to both "
                        f"{output_model_groups[output_model_type]!r} and {group.title!r}"
                    )
                    raise PresetError(msg)
                output_model_groups[output_model_type] = group.title


_validate_preset_infos(_PRESET_INFOS)


def get_preset_names() -> tuple[str, ...]:
    """Return all public preset names."""
    return tuple(preset.value for preset in PresetName)


def get_latest_preset_name() -> str:
    """Return the latest public preset name."""
    return max(get_preset_names(), key=_preset_name_sort_key)


def get_preset_infos() -> tuple[PresetInfo, ...]:
    """Return public preset metadata."""
    return _PRESET_INFOS


def _preset_name_sort_key(name: str) -> tuple[str, str]:
    prefix, separator, version = name.rpartition("-")
    if separator and version.isdecimal():
        return prefix, version
    return name, ""  # pragma: no cover


def preset_info_as_dict(info: PresetInfo) -> dict[str, object]:
    """Serialize a preset info entry to primitive values."""
    return {
        "name": info.name.value,
        "summary": info.summary,
        "description": info.description,
        "requires_target_python_version": info.requires_target_python_version,
        "option_groups": [
            {
                "title": group.title,
                "options": list(group.options),
                "description": group.description,
            }
            for group in info.option_groups
        ],
    }


def render_presets_json() -> str:
    """Render preset metadata as JSON."""
    return _render_registry_json(preset_info_as_dict(info) for info in _PRESET_INFOS)


def render_presets_markdown() -> str:
    """Render the preset reference page."""
    lines = [
        "# Presets",
        "",
        "<!-- Generated by scripts/build_preset_docs.py. Do not edit manually. -->",
        "",
        (
            "Presets are immutable named groups of CLI options. A preset name never changes behavior; "
            "new recommendations are published as new dated preset names."
        ),
        "",
        (
            "Every preset requires an explicit `--target-python-version` or `target-python-version` in "
            "`pyproject.toml` so generated Python syntax is pinned."
        ),
        "",
    ]
    for info in _PRESET_INFOS:
        target_required = "yes" if info.requires_target_python_version else "no"
        lines.extend((
            f"## `{info.name.value}`",
            "",
            info.summary,
            "",
            info.description,
            "",
            f"- **Requires explicit target Python version:** {target_required}",
            "",
            "| Scope | Options | Notes |",
            "|-------|---------|-------|",
        ))
        for group in info.option_groups:
            options = ", ".join(f"`{option}`" for option in group.options)
            lines.append(f"| {group.title} | {options} | {group.description} |")
        lines.append("")
    return "\n".join(lines)


def render_presets(format_: PresetFormat) -> str:
    """Render presets in the requested format."""
    if format_ == "json":
        return render_presets_json() + "\n"
    return render_presets_markdown().rstrip() + "\n"


def resolve_preset(preset: PresetName | str, context: PresetContext) -> BaseGenerateConfig:
    """Resolve a preset into config updates for the given context."""
    try:
        preset_name = preset if isinstance(preset, PresetName) else PresetName(preset)
    except ValueError as exc:
        names = ", ".join(get_preset_names())
        msg = f"Unknown preset: {preset!r}. Available presets: {names}"
        raise PresetError(msg) from exc

    return _resolve_preset_info(_get_preset_info(preset_name), context)


def _get_preset_info(preset_name: PresetName) -> PresetInfo:
    """Return preset metadata for a known preset name."""
    for info in _PRESET_INFOS:
        if info.name is preset_name:
            return info

    msg = f"Unsupported preset: {preset_name.value}"  # pragma: no cover
    raise PresetError(msg)  # pragma: no cover


def _resolve_preset_info(info: PresetInfo, context: PresetContext) -> BaseGenerateConfig:
    """Resolve preset metadata into config updates for the given context."""
    applicable_groups = tuple(group for group in info.option_groups if group.applies_to(context))
    if not any(group.output_model_types for group in applicable_groups):
        msg = (  # pragma: no cover
            f"Unsupported output model type for preset {info.name.value}: {context.output_model_type.value}"
        )
        raise PresetError(msg)  # pragma: no cover

    return _merge_preset_configs(*(config for group in applicable_groups for config in group.configs))
