"""Built-in immutable option presets for the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal

from datamodel_code_generator._registry_render import _render_registry_json
from datamodel_code_generator.cli_options import CLI_OPTION_META
from datamodel_code_generator.config import BaseGenerateConfig
from datamodel_code_generator.enums import DataModelType, InputFileType

if TYPE_CHECKING:
    from collections.abc import Mapping

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


@dataclass(frozen=True, slots=True, init=False)
class PresetConfig:
    """Typed immutable config updates supplied by a preset group."""

    values: Mapping[str, object]

    def __init__(self, **values: Unpack[BaseGenerateConfigDict]) -> None:
        """Build immutable preset updates from statically checked GenerateConfig fields."""
        object.__setattr__(self, "values", MappingProxyType(dict(values)))


@dataclass(frozen=True, slots=True)
class PresetOptionGroup:
    """Documented option group for a preset."""

    title: str
    config: PresetConfig
    description: str
    input_file_types: frozenset[InputFileType] = frozenset()
    output_model_types: frozenset[DataModelType] = frozenset()
    requires_python_strenum: bool = False
    options: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Cache documented CLI options derived from typed config fields."""
        options = tuple(
            _config_field_to_cli_option(field_name, value=value) for field_name, value in self.config.values.items()
        )
        object.__setattr__(self, "options", options)

    def applies_to(self, context: PresetContext) -> bool:
        """Return whether this option group applies to a preset context."""
        if self.input_file_types and context.input_file_type not in self.input_file_types:  # pragma: no cover
            return False
        if self.output_model_types and context.output_model_type not in self.output_model_types:
            return False
        return not self.requires_python_strenum or context.target_python_version.has_strenum


def _merge_preset_configs(*configs: PresetConfig) -> PresetConfig:
    """Merge preset configs, rejecting conflicting explicit updates."""
    values: dict[str, object] = {}
    for config in configs:
        for field_name, value in config.values.items():
            if field_name in values and values[field_name] != value:  # pragma: no cover
                msg = f"Preset field {field_name!r} is configured with both {values[field_name]!r} and {value!r}"
                raise PresetError(msg)
            values[field_name] = value
    BaseGenerateConfig.model_validate(values)
    return PresetConfig(**values)


def _config_field_to_cli_option(field_name: str, *, value: object) -> str:
    """Translate a typed config field name to its CLI option spelling."""
    if field_name not in BaseGenerateConfig.model_fields:  # pragma: no cover
        msg = f"Preset field {field_name!r} is not a BaseGenerateConfig field"
        raise PresetError(msg)
    if not isinstance(value, bool):  # pragma: no cover
        msg = f"Preset field {field_name!r} cannot be rendered as a Boolean CLI option"
        raise PresetError(msg)
    option_name = field_name.replace("_", "-")
    option = f"--{option_name}"
    if option not in CLI_OPTION_META:  # pragma: no cover
        msg = f"Preset field {field_name!r} does not map to a documented CLI option"
        raise PresetError(msg)
    if value is True:
        return option

    negative_option = f"--no-{option_name}"  # pragma: no cover
    if negative_option not in CLI_OPTION_META:  # pragma: no cover
        msg = f"Preset field {field_name!r} does not map to a documented negative CLI option"
        raise PresetError(msg)
    return negative_option  # pragma: no cover


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
                config=PresetConfig(
                    use_standard_collections=True,
                    use_union_operator=True,
                    use_annotated=True,
                    collapse_root_models=True,
                ),
                description=(
                    "Use built-in collection syntax, PEP 604 unions, Annotated constraints, and inline root wrappers."
                ),
            ),
            PresetOptionGroup(
                title="Python 3.11+ targets",
                config=PresetConfig(use_specialized_enum=True),
                description="Use StrEnum or IntEnum only when the selected target Python version supports it.",
                requires_python_strenum=True,
            ),
            PresetOptionGroup(
                title="Pydantic v2 BaseModel and dataclass output",
                config=PresetConfig(
                    snake_case_field=True,
                    allow_population_by_field_name=True,
                    use_frozen_field=True,
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
                config=PresetConfig(
                    snake_case_field=True,
                    use_standard_primitive_types=True,
                ),
                description="Generate Pythonic field names with aliases and stdlib primitive types for schema formats.",
                output_model_types=frozenset({DataModelType.MsgspecStruct}),
            ),
            PresetOptionGroup(
                title="stdlib dataclass output",
                config=PresetConfig(use_standard_primitive_types=True),
                description=(
                    "Use stdlib primitive types without renaming input keys because dataclasses do not carry aliases."
                ),
                output_model_types=frozenset({DataModelType.DataclassesDataclass}),
            ),
            PresetOptionGroup(
                title="TypedDict output",
                config=PresetConfig(
                    use_standard_primitive_types=True,
                    use_frozen_field=True,
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
        if info.name in preset_names:  # pragma: no cover
            msg = f"Preset {info.name.value!r} is defined more than once"
            raise PresetError(msg)
        preset_names.add(info.name)

        output_model_groups: dict[DataModelType, str] = {}
        for group in info.option_groups:
            if not group.config.values:  # pragma: no cover
                msg = f"Preset option group {group.title!r} does not define any config fields"
                raise PresetError(msg)
            for output_model_type in group.output_model_types:
                if output_model_type in output_model_groups:  # pragma: no cover
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
    rendered: str
    match format_:
        case "json":
            rendered = render_presets_json() + "\n"
        case "markdown":
            rendered = render_presets_markdown().rstrip() + "\n"
        case _:  # pragma: no cover
            msg = f"Unsupported preset docs format: {format_!r}"
            raise PresetError(msg)
    return rendered


def resolve_preset(preset: PresetName | str, context: PresetContext) -> PresetConfig:
    """Resolve a preset into config updates for the given context."""
    try:
        preset_name = preset if isinstance(preset, PresetName) else PresetName(preset)
    except ValueError as exc:  # pragma: no cover
        names = ", ".join(get_preset_names())
        msg = f"Unknown preset: {preset!r}. Available presets: {names}"
        raise PresetError(msg) from exc

    return _resolve_preset_info(_get_preset_info(preset_name), context)


def _get_preset_info(preset_name: PresetName) -> PresetInfo:
    """Return preset metadata for a known preset name."""
    for info in _PRESET_INFOS:
        if info.name is preset_name:  # pragma: no branch
            return info

    msg = f"Unsupported preset: {preset_name.value}"  # pragma: no cover
    raise PresetError(msg)  # pragma: no cover


def _resolve_preset_info(info: PresetInfo, context: PresetContext) -> PresetConfig:
    """Resolve preset metadata into config updates for the given context."""
    applicable_groups = tuple(group for group in info.option_groups if group.applies_to(context))
    if not any(group.output_model_types for group in applicable_groups):
        msg = (  # pragma: no cover
            f"Unsupported output model type for preset {info.name.value}: {context.output_model_type.value}"
        )
        raise PresetError(msg)  # pragma: no cover

    return _merge_preset_configs(*(group.config for group in applicable_groups))
