"""Built-in immutable option presets for the CLI."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from datamodel_code_generator._registry_render import _render_registry_json
from datamodel_code_generator.enums import DataModelType, InputFileType

if TYPE_CHECKING:
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
class PresetOptionGroup:
    """Documented option group for a preset."""

    title: str
    options: tuple[str, ...]
    description: str


@dataclass(frozen=True, slots=True)
class PresetInfo:
    """Public preset metadata used by CLI docs."""

    name: PresetName
    summary: str
    description: str
    requires_target_python_version: bool
    option_groups: tuple[PresetOptionGroup, ...]


@dataclass(frozen=True, slots=True)
class PresetPatch:
    """Config values supplied by a preset.

    ``None`` means the preset leaves the option untouched.
    """

    use_standard_collections: bool | None = None
    use_union_operator: bool | None = None
    use_annotated: bool | None = None
    use_specialized_enum: bool | None = None
    snake_case_field: bool | None = None
    allow_population_by_field_name: bool | None = None
    collapse_root_models: bool | None = None
    use_standard_primitive_types: bool | None = None
    use_frozen_field: bool | None = None

    def merge(self, other: PresetPatch) -> PresetPatch:
        """Merge two patches, with ``other`` taking precedence."""
        values = self.updates()
        values.update(other.updates())
        return PresetPatch(**values)

    def updates(self) -> dict[str, Any]:
        """Return only values explicitly supplied by the patch."""
        return {field.name: value for field in fields(self) if (value := getattr(self, field.name)) is not None}


_STANDARD_BASE_PATCH = PresetPatch(
    use_standard_collections=True,
    use_union_operator=True,
    use_annotated=True,
    collapse_root_models=True,
)
_STANDARD_SPECIALIZED_ENUM_PATCH = PresetPatch(use_specialized_enum=True)
_STANDARD_PYDANTIC_PATCH = PresetPatch(
    snake_case_field=True,
    allow_population_by_field_name=True,
    use_frozen_field=True,
)
_STANDARD_MSGSPEC_PATCH = PresetPatch(
    snake_case_field=True,
    use_standard_primitive_types=True,
)
_STANDARD_DATACLASS_PATCH = PresetPatch(use_standard_primitive_types=True)
_STANDARD_TYPED_DICT_PATCH = PresetPatch(
    use_standard_primitive_types=True,
    use_frozen_field=True,
)

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
                options=(
                    "--use-standard-collections",
                    "--use-union-operator",
                    "--use-annotated",
                    "--collapse-root-models",
                ),
                description=(
                    "Use built-in collection syntax, PEP 604 unions, Annotated constraints, and inline root wrappers."
                ),
            ),
            PresetOptionGroup(
                title="Python 3.11+ targets",
                options=("--use-specialized-enum",),
                description="Use StrEnum or IntEnum only when the selected target Python version supports it.",
            ),
            PresetOptionGroup(
                title="Pydantic v2 BaseModel and dataclass output",
                options=(
                    "--snake-case-field",
                    "--allow-population-by-field-name",
                    "--use-frozen-field",
                ),
                description=(
                    "Generate Pythonic field names while preserving input aliases and readOnly immutability metadata."
                ),
            ),
            PresetOptionGroup(
                title="msgspec Struct output",
                options=(
                    "--snake-case-field",
                    "--use-standard-primitive-types",
                ),
                description="Generate Pythonic field names with aliases and stdlib primitive types for schema formats.",
            ),
            PresetOptionGroup(
                title="stdlib dataclass output",
                options=("--use-standard-primitive-types",),
                description=(
                    "Use stdlib primitive types without renaming input keys because dataclasses do not carry aliases."
                ),
            ),
            PresetOptionGroup(
                title="TypedDict output",
                options=(
                    "--use-standard-primitive-types",
                    "--use-frozen-field",
                ),
                description="Use stdlib primitive types and ReadOnly metadata without renaming dictionary keys.",
            ),
        ),
    ),
)


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
    return name, ""


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


def resolve_preset(preset: PresetName | str, context: PresetContext) -> PresetPatch:
    """Resolve a preset into config updates for the given context."""
    try:
        preset_name = preset if isinstance(preset, PresetName) else PresetName(preset)
    except ValueError as exc:
        names = ", ".join(get_preset_names())
        msg = f"Unknown preset: {preset!r}. Available presets: {names}"
        raise PresetError(msg) from exc

    match preset_name:
        case PresetName.Standard20260617:
            return _resolve_standard_20260617(context)


def _resolve_standard_20260617(context: PresetContext) -> PresetPatch:
    patch = _STANDARD_BASE_PATCH
    if context.target_python_version.has_strenum:
        patch = patch.merge(_STANDARD_SPECIALIZED_ENUM_PATCH)

    match context.output_model_type:
        case DataModelType.PydanticV2BaseModel | DataModelType.PydanticV2Dataclass:
            return patch.merge(_STANDARD_PYDANTIC_PATCH)
        case DataModelType.MsgspecStruct:
            return patch.merge(_STANDARD_MSGSPEC_PATCH)
        case DataModelType.DataclassesDataclass:
            return patch.merge(_STANDARD_DATACLASS_PATCH)
        case DataModelType.TypingTypedDict:
            return patch.merge(_STANDARD_TYPED_DICT_PATCH)
