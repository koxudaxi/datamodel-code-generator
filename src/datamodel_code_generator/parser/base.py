"""Abstract base parser and utilities for schema parsing.

Provides the Parser abstract base class that defines the parsing algorithm,
along with helper functions for model sorting, import resolution, and
code generation.
"""

from __future__ import annotations

import operator
import os.path
import re
import sys
from abc import ABC, abstractmethod
from collections import Counter, OrderedDict, defaultdict
from collections.abc import Callable, Hashable, Sequence
from itertools import groupby
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Optional, Protocol, TypeAlias, TypeVar, cast, runtime_checkable
from urllib.parse import ParseResult
from warnings import warn

from pydantic import BaseModel

from datamodel_code_generator import (
    DEFAULT_SHARED_MODULE_NAME,
    AllExportsCollisionStrategy,
    AllExportsScope,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
    Error,
    FieldTypeCollisionStrategy,
    ModuleSplitMode,
    NamingStrategy,
    ReadOnlyWriteOnlyModelType,
    ReuseScope,
    TargetPydanticVersion,
    YamlValue,
)
from datamodel_code_generator.format import (
    DEFAULT_FORMATTERS,
    CodeFormatter,
    DateClassType,
    DatetimeClassType,
    Formatter,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.imports import (
    IMPORT_ANNOTATIONS,
    IMPORT_LITERAL,
    IMPORT_OPTIONAL,
    IMPORT_UNION,
    Import,
    Imports,
)
from datamodel_code_generator.model import dataclass as dataclass_model
from datamodel_code_generator.model import msgspec as msgspec_model
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.model import pydantic_v2 as pydantic_model_v2
from datamodel_code_generator.model.base import (
    ALL_MODEL,
    GENERIC_BASE_CLASS_NAME,
    GENERIC_BASE_CLASS_PATH,
    UNDEFINED,
    BaseClassDataType,
    ConstraintsBase,
    DataModel,
    DataModelFieldBase,
    WrappedDefault,
)
from datamodel_code_generator.model.enum import Enum, Member
from datamodel_code_generator.model.type_alias import TypeAliasBase, TypeStatement
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.parser._graph import stable_toposort
from datamodel_code_generator.parser._scc import find_circular_sccs, strongly_connected_components
from datamodel_code_generator.reference import ModelResolver, ModelType, Reference
from datamodel_code_generator.types import DataType, DataTypeManager, StrictTypes
from datamodel_code_generator.util import camel_to_snake, model_copy, model_dump

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence

    from datamodel_code_generator import DataclassArguments


@runtime_checkable
class HashableComparable(Hashable, Protocol):
    """Protocol for types that are both hashable and support comparison."""

    def __lt__(self, value: Any, /) -> bool: ...  # noqa: D105
    def __le__(self, value: Any, /) -> bool: ...  # noqa: D105
    def __gt__(self, value: Any, /) -> bool: ...  # noqa: D105
    def __ge__(self, value: Any, /) -> bool: ...  # noqa: D105


ModelName: TypeAlias = str
ModelNames: TypeAlias = set[ModelName]
ModelDeps: TypeAlias = dict[ModelName, set[ModelName]]
OrderIndex: TypeAlias = dict[ModelName, int]

ComponentId: TypeAlias = int
Components: TypeAlias = list[list[ModelName]]
ComponentOf: TypeAlias = dict[ModelName, ComponentId]
ComponentEdges: TypeAlias = dict[ComponentId, set[ComponentId]]

ClassNode: TypeAlias = tuple[ModelName, ...]
ClassGraph: TypeAlias = dict[ClassNode, set[ClassNode]]

ModulePath: TypeAlias = tuple[str, ...]
ModuleModels: TypeAlias = list[tuple[ModulePath, list[DataModel]]]
ForwarderMap: TypeAlias = dict[ModulePath, tuple[ModulePath, list[tuple[str, str]]]]


class ModuleContext(NamedTuple):
    """Context for processing a single module during code generation."""

    module: ModulePath
    module_key: ModulePath
    models: list[DataModel]
    is_init: bool
    imports: Imports
    scoped_model_resolver: ModelResolver


class ParseConfig(NamedTuple):
    """Configuration for the parse operation."""

    with_import: bool
    use_deferred_annotations: bool
    code_formatter: CodeFormatter | None
    module_split_mode: ModuleSplitMode | None
    all_exports_scope: AllExportsScope | None
    all_exports_collision_strategy: AllExportsCollisionStrategy | None


class _KeepModelOrderDeps(NamedTuple):
    strong: ModelDeps
    all: ModelDeps


class _KeepModelOrderComponents(NamedTuple):
    components: Components
    comp_of: ComponentOf


def _collect_keep_model_order_deps(
    model: DataModel,
    *,
    model_names: ModelNames,
    imported: ModelNames,
    use_deferred_annotations: bool,
) -> tuple[set[ModelName], set[ModelName]]:
    """Collect (strong_deps, all_deps) used by keep_model_order sorting.

    - strong_deps: base class references (within-module, non-imported)
    - all_deps: base class refs + (optionally) field refs (within-module, non-imported)
    """
    class_name = model.class_name
    base_class_refs = {b.reference.short_name for b in model.base_classes if b.reference}
    field_refs = {t.reference.short_name for f in model.fields for t in f.data_type.all_data_types if t.reference}

    if use_deferred_annotations and not isinstance(model, (TypeAliasBase, pydantic_model_v2.RootModel)):
        field_refs = set()

    strong = {r for r in base_class_refs if r in model_names and r not in imported and r != class_name}
    deps = {r for r in (base_class_refs | field_refs) if r in model_names and r not in imported and r != class_name}
    return strong, deps


def _build_keep_model_order_dependency_maps(
    models: list[DataModel],
    *,
    model_names: ModelNames,
    imported: ModelNames,
    use_deferred_annotations: bool,
) -> _KeepModelOrderDeps:
    strong_deps: ModelDeps = {}
    all_deps: ModelDeps = {}
    for model in models:
        strong, deps = _collect_keep_model_order_deps(
            model,
            model_names=model_names,
            imported=imported,
            use_deferred_annotations=use_deferred_annotations,
        )
        strong_deps[model.class_name] = strong
        all_deps[model.class_name] = deps
    return _KeepModelOrderDeps(strong=strong_deps, all=all_deps)


def _build_keep_model_order_components(
    all_deps: ModelDeps,
    order_index: OrderIndex,
) -> _KeepModelOrderComponents:
    graph: ClassGraph = {(name,): {(dep,) for dep in deps} for name, deps in all_deps.items()}
    sccs = strongly_connected_components(graph)
    components: Components = [sorted((node[0] for node in scc), key=order_index.__getitem__) for scc in sccs]
    components.sort(key=lambda members: min(order_index[n] for n in members))
    comp_of: ComponentOf = {name: i for i, members in enumerate(components) for name in members}
    return _KeepModelOrderComponents(components=components, comp_of=comp_of)


def _build_keep_model_order_component_edges(
    all_deps: ModelDeps,
    comp_of: ComponentOf,
    num_components: int,
) -> ComponentEdges:
    comp_edges: ComponentEdges = {i: set() for i in range(num_components)}
    for name, deps in all_deps.items():
        name_comp = comp_of[name]
        for dep in deps:
            if (dep_comp := comp_of[dep]) != name_comp:
                comp_edges[dep_comp].add(name_comp)
    return comp_edges


def _build_keep_model_order_component_order(
    components: Components,
    comp_edges: ComponentEdges,
    order_index: OrderIndex,
) -> list[ComponentId]:
    comp_key = [min(order_index[n] for n in members) for members in components]
    return stable_toposort(
        list(range(len(components))),
        comp_edges,
        key=lambda component_id: comp_key[component_id],
    )


def _build_keep_model_ordered_names(
    ordered_comp_ids: list[ComponentId],
    components: Components,
    strong_deps: ModelDeps,
    order_index: OrderIndex,
) -> list[ModelName]:
    ordered_names: list[ModelName] = []
    for component_id in ordered_comp_ids:
        members = components[component_id]
        if len(members) > 1:
            strong_edges: dict[ModelName, set[ModelName]] = {n: set() for n in members}
            member_set = set(members)
            for base in members:
                derived_members = {member for member in members if base in strong_deps.get(member, set()) & member_set}
                strong_edges[base].update(derived_members)
            members = stable_toposort(members, strong_edges, key=order_index.__getitem__)
        ordered_names.extend(members)
    return ordered_names


def _reorder_models_keep_model_order(
    models: list[DataModel],
    imports: Imports,
    *,
    use_deferred_annotations: bool,
) -> None:
    """Reorder models deterministically based on their dependencies.

    Starts from class_name order and only moves models when required to satisfy dependencies.
    Cycles are kept as SCC groups; within each SCC, base-class dependencies are prioritized.
    """
    models.sort(key=lambda x: x.class_name)
    imported: ModelNames = {i for v in imports.values() for i in v}
    model_by_name = {m.class_name: m for m in models}
    model_names: ModelNames = set(model_by_name)
    order_index: OrderIndex = {m.class_name: i for i, m in enumerate(models)}

    deps = _build_keep_model_order_dependency_maps(
        models,
        model_names=model_names,
        imported=imported,
        use_deferred_annotations=use_deferred_annotations,
    )
    comps = _build_keep_model_order_components(deps.all, order_index)
    comp_edges = _build_keep_model_order_component_edges(deps.all, comps.comp_of, len(comps.components))
    ordered_comp_ids = _build_keep_model_order_component_order(comps.components, comp_edges, order_index)
    ordered_names = _build_keep_model_ordered_names(ordered_comp_ids, comps.components, deps.strong, order_index)
    models[:] = [model_by_name[name] for name in ordered_names]


SPECIAL_PATH_FORMAT: str = "#-datamodel-code-generator-#-{}-#-special-#"


def get_special_path(keyword: str, path: list[str]) -> list[str]:
    """Create a special path marker for internal reference tracking."""
    return [*path, SPECIAL_PATH_FORMAT.format(keyword)]


escape_characters = str.maketrans({
    "\u0000": r"\x00",  # Null byte
    "\\": r"\\",
    "'": r"\'",
    "\b": r"\b",
    "\f": r"\f",
    "\n": r"\n",
    "\r": r"\r",
    "\t": r"\t",
})


def to_hashable(item: Any) -> HashableComparable:  # noqa: PLR0911
    """Convert an item to a hashable and comparable representation.

    Returns a value that is both hashable and supports comparison operators.
    Used for caching and deduplication of models.
    """
    if isinstance(
        item,
        (
            list,
            tuple,
        ),
    ):
        try:
            return tuple(sorted((to_hashable(i) for i in item), key=lambda v: (str(type(v)), v)))
        except TypeError:
            # Fallback when mixed, non-comparable types are present; preserve original order
            return tuple(to_hashable(i) for i in item)
    if isinstance(item, dict):
        return tuple(
            sorted(
                (
                    k,
                    to_hashable(v),
                )
                for k, v in item.items()
            )
        )
    if isinstance(item, set):  # pragma: no cover
        return frozenset(to_hashable(i) for i in item)  # type: ignore[return-value]
    if isinstance(item, BaseModel):
        return to_hashable(model_dump(item))
    if item is None:
        return ""
    return item  # type: ignore[return-value]


def dump_templates(templates: list[DataModel]) -> str:
    """Join model templates into a single code string."""
    return "\n\n\n".join(str(m) for m in templates)


def iter_models_field_data_types(
    models: Iterable[DataModel],
) -> Iterator[tuple[DataModel, DataModelFieldBase, DataType]]:
    """Yield (model, field, data_type) for all models, fields, and nested data types."""
    for model in models:
        for field in model.fields:
            for data_type in field.data_type.all_data_types:
                yield model, field, data_type


ReferenceMapSet = dict[str, set[str]]
SortedDataModels = dict[str, DataModel]

MAX_RECURSION_COUNT: int = sys.getrecursionlimit()


def add_model_path_to_list(
    paths: list[str] | None,
    model: DataModel,
    /,
) -> list[str]:
    """
    Auxiliary method which adds model path to list, provided the following hold.

    - model is not a type alias
    - path is not already in the list.

    """
    if paths is None:
        paths = []
    if model.is_alias:
        return paths
    if (path := model.path) in paths:
        return paths
    paths.append(path)
    return paths


def sort_data_models(  # noqa: PLR0912, PLR0915
    unsorted_data_models: list[DataModel],
    sorted_data_models: SortedDataModels | None = None,
    require_update_action_models: list[str] | None = None,
    recursion_count: int = MAX_RECURSION_COUNT,
) -> tuple[list[DataModel], SortedDataModels, list[str]]:
    """Sort data models by dependency order for correct forward references."""
    if sorted_data_models is None:
        sorted_data_models = OrderedDict()
    if require_update_action_models is None:
        require_update_action_models = []
    sorted_model_count: int = len(sorted_data_models)

    unresolved_references: list[DataModel] = []
    for model in unsorted_data_models:
        if not model.reference_classes:
            sorted_data_models[model.path] = model
        elif model.path in model.reference_classes and len(model.reference_classes) == 1:  # only self-referencing
            sorted_data_models[model.path] = model
            add_model_path_to_list(require_update_action_models, model)
        elif (
            not model.reference_classes - {model.path} - sorted_data_models.keys()
        ):  # reference classes have been resolved
            sorted_data_models[model.path] = model
            if model.path in model.reference_classes:
                add_model_path_to_list(require_update_action_models, model)
        else:
            unresolved_references.append(model)
    if unresolved_references:
        if sorted_model_count != len(sorted_data_models) and recursion_count:
            try:
                return sort_data_models(
                    unresolved_references,
                    sorted_data_models,
                    require_update_action_models,
                    recursion_count - 1,
                )
            except RecursionError:  # pragma: no cover
                pass

        # sort on base_class dependency
        while True:
            ordered_models: list[tuple[int, DataModel]] = []
            # Build lookup dict for O(1) index access instead of O(n) list.index()
            path_to_index = {m.path: idx for idx, m in enumerate(unresolved_references)}
            for model in unresolved_references:
                if isinstance(model, pydantic_model_v2.RootModel):
                    indexes = [
                        path_to_index[ref_path]
                        for f in model.fields
                        for t in f.data_type.all_data_types
                        if t.reference and (ref_path := t.reference.path) in path_to_index
                    ]
                else:
                    indexes = [
                        path_to_index[b.reference.path]
                        for b in model.base_classes
                        if b.reference and b.reference.path in path_to_index
                    ]
                if indexes:
                    ordered_models.append((
                        max(indexes),
                        model,
                    ))
                else:
                    ordered_models.append((
                        -1,
                        model,
                    ))
            sorted_unresolved_models = [m[1] for m in sorted(ordered_models, key=operator.itemgetter(0))]
            if sorted_unresolved_models == unresolved_references:
                break
            unresolved_references = sorted_unresolved_models

        # circular reference
        unsorted_data_model_names = set(path_to_index.keys())
        for model in unresolved_references:
            unresolved_model = model.reference_classes - {model.path} - sorted_data_models.keys()
            base_models = [getattr(s.reference, "path", None) for s in model.base_classes]
            update_action_parent = set(require_update_action_models).intersection(base_models)
            if not unresolved_model:
                sorted_data_models[model.path] = model
                if update_action_parent:
                    add_model_path_to_list(require_update_action_models, model)
                continue
            if not unresolved_model - unsorted_data_model_names:
                sorted_data_models[model.path] = model
                add_model_path_to_list(require_update_action_models, model)
                continue
            # unresolved
            unresolved_classes = ", ".join(
                f"[class: {item.path} references: {item.reference_classes}]" for item in unresolved_references
            )
            msg = f"A Parser can not resolve classes: {unresolved_classes}."
            raise Exception(msg)  # noqa: TRY002
    return unresolved_references, sorted_data_models, require_update_action_models


def relative(
    current_module: str,
    reference: str,
    *,
    reference_is_module: bool = False,
    current_is_init: bool = False,
) -> tuple[str, str]:
    """Find relative module path.

    Args:
        current_module: Current module path (e.g., "foo.bar")
        reference: Reference path (e.g., "foo.baz.ClassName" or "foo.baz" if reference_is_module)
        reference_is_module: If True, treat reference as a module path (not module.class)
        current_is_init: If True, treat current_module as a package __init__.py (adds depth)

    Returns:
        Tuple of (from_path, import_name) for constructing import statements
    """
    if current_is_init:
        current_module_path = [*current_module.split("."), "__init__"] if current_module else ["__init__"]
    else:
        current_module_path = current_module.split(".") if current_module else []

    if reference_is_module:
        reference_path = reference.split(".") if reference else []
        name = reference_path[-1] if reference_path else ""
    else:
        *reference_path, name = reference.split(".")

    if current_module_path == reference_path:
        return "", ""

    i = 0
    for x, y in zip(current_module_path, reference_path, strict=False):
        if x != y:
            break
        i += 1

    left = "." * (len(current_module_path) - i)
    right = ".".join(reference_path[i:])

    if not left:
        left = "."
    if not right:
        right = name
    elif "." in right:
        extra, right = right.rsplit(".", 1)
        left += extra

    return left, right


def is_ancestor_package_reference(current_module: str, reference: str) -> bool:
    """Check if reference is in an ancestor package (__init__.py).

    When the reference's module path is an ancestor (prefix) of the current module,
    the reference is in an ancestor package's __init__.py file.

    Args:
        current_module: The current module path (e.g., "v0.mammal.canine")
        reference: The full reference path (e.g., "v0.Animal")

    Returns:
        True if the reference is in an ancestor package, False otherwise.

    Examples:
        - current="v0.animal", ref="v0.Animal" -> True (immediate parent)
        - current="v0.mammal.canine", ref="v0.Animal" -> True (grandparent)
        - current="v0.animal", ref="v0.animal.Dog" -> False (same or child)
        - current="pets", ref="Animal" -> True (root package is immediate parent)
    """
    current_path = current_module.split(".") if current_module else []
    *reference_path, _ = reference.split(".")

    if not current_path:
        return False

    # Case 1: Direct parent package (includes root package when reference_path is empty)
    # e.g., current="pets", ref="Animal" -> current_path[:-1]=[] == reference_path=[]
    if current_path[:-1] == reference_path:
        return True

    # Case 2: Deeper ancestor package (reference_path must be non-empty proper prefix)
    # e.g., current="v0.mammal.canine", ref="v0.Animal" -> ["v0"] is prefix of ["v0","mammal","canine"]
    return (
        len(reference_path) > 0
        and len(reference_path) < len(current_path)
        and current_path[: len(reference_path)] == reference_path
    )


def exact_import(from_: str, import_: str, short_name: str) -> tuple[str, str]:
    """Create exact import path to avoid relative import issues."""
    if from_ == len(from_) * ".":
        # Prevents "from . import foo" becoming "from ..foo import Foo"
        # or "from .. import foo" becoming "from ...foo import Foo"
        # when our imported module has the same parent
        return f"{from_}{import_}", short_name
    return f"{from_}.{import_}", short_name


def get_module_directory(module: tuple[str, ...]) -> tuple[str, ...]:
    """Get the directory portion of a module tuple.

    Note: Module tuples in module_models do NOT include .py extension.
    The last element is either the module name (e.g., "issuing") or empty for root.

    Examples:
        ("pkg",) -> ("pkg",) - root module
        ("pkg", "issuing") -> ("pkg",) - submodule
        ("foo", "bar", "baz") -> ("foo", "bar") - deeply nested module
    """
    if not module:
        return ()
    if len(module) == 1:
        return module
    return module[:-1]


@runtime_checkable
class Child(Protocol):
    """Protocol for objects with a parent reference."""

    @property
    def parent(self) -> Any | None:
        """Get the parent object reference."""
        raise NotImplementedError


T = TypeVar("T")


def get_most_of_parent(value: Any, type_: type[T] | None = None) -> T | None:
    """Traverse parent chain to find the outermost matching parent."""
    if isinstance(value, Child) and (type_ is None or not isinstance(value, type_)):
        return get_most_of_parent(value.parent, type_)
    return value


def title_to_class_name(title: str) -> str:
    """Convert a schema title to a valid Python class name."""
    classname = re.sub(r"[^A-Za-z0-9]+", " ", title)
    return "".join(x for x in classname.title() if not x.isspace())


def _find_base_classes(model: DataModel) -> list[DataModel]:
    """Get direct base class DataModels."""
    return [b.reference.source for b in model.base_classes if b.reference and isinstance(b.reference.source, DataModel)]


def _find_field(original_name: str, models: list[DataModel]) -> DataModelFieldBase | None:
    """Find a field by original_name in the models and their base classes."""
    for model in models:
        for field in model.iter_all_fields():  # pragma: no cover
            if field.original_name == original_name:
                return field
    return None  # pragma: no cover


def _copy_data_types(data_types: list[DataType]) -> list[DataType]:
    """Deep copy a list of DataType objects, preserving references."""
    copied_data_types: list[DataType] = []
    for data_type_ in data_types:
        if data_type_.reference:
            copied_data_types.append(data_type_.__class__(reference=data_type_.reference))
        elif data_type_.data_types:  # pragma: no cover
            copied_data_type = model_copy(data_type_)
            copied_data_type.data_types = _copy_data_types(data_type_.data_types)
            copied_data_types.append(copied_data_type)
        else:
            copied_data_types.append(model_copy(data_type_))
    return copied_data_types


class Result(BaseModel):
    """Generated code result with optional source file reference."""

    body: str
    future_imports: str = ""
    source: Optional[Path] = None  # noqa: UP045


class Source(BaseModel):
    """Schema source file with path and content."""

    path: Path
    text: str = ""
    raw_data: dict[str, YamlValue] | None = None

    @classmethod
    def from_path(cls, path: Path, base_path: Path, encoding: str) -> Source:
        """Create a Source from a file path relative to base_path."""
        return cls(
            path=path.relative_to(base_path),
            text=path.read_text(encoding=encoding),
        )

    @classmethod
    def from_dict(cls, data: dict[str, YamlValue]) -> Source:
        """Create a Source from a dict."""
        return cls(path=Path(), raw_data=data)


class Parser(ABC):
    """Abstract base class for schema parsers.

    Provides the parsing algorithm and code generation. Subclasses implement
    parse_raw() to handle specific schema formats.
    """

    def __init__(  # noqa: PLR0912, PLR0913, PLR0915
        self,
        source: str | Path | list[Path] | ParseResult | dict[str, YamlValue],
        *,
        data_model_type: type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: type[DataModel] = pydantic_model.CustomRootType,
        data_type_manager_type: type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: str | None = None,
        base_class_map: dict[str, str] | None = None,
        additional_imports: list[str] | None = None,
        class_decorators: list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
        target_python_version: PythonVersion = PythonVersionMin,
        dump_resolve_reference_action: Callable[[Iterable[str]], str] | None = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Mapping[str, str] | None = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        allow_extra_fields: bool = False,
        extra_fields: str | None = None,
        use_generic_base_class: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: str | None = None,
        use_standard_collections: bool = False,
        base_path: Path | None = None,
        use_schema_description: bool = False,
        use_field_description: bool = False,
        use_field_description_example: bool = False,
        use_attribute_docstrings: bool = False,
        use_inline_field_description: bool = False,
        use_default_kwarg: bool = False,
        reuse_model: bool = False,
        reuse_scope: ReuseScope | None = None,
        shared_module_name: str = DEFAULT_SHARED_MODULE_NAME,
        encoding: str = "utf-8",
        enum_field_as_literal: LiteralType | None = None,
        enum_field_as_literal_map: dict[str, str] | None = None,
        ignore_enum_constraints: bool = False,
        set_default_enum_member: bool = False,
        use_subclass_enum: bool = False,
        use_specialized_enum: bool = True,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: DefaultPutDict[str, str] | None = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Sequence[StrictTypes] | None = None,
        empty_enum_field_name: str | None = None,
        custom_class_name_generator: Callable[[str], str] | None = title_to_class_name,
        field_extra_keys: set[str] | None = None,
        field_include_all_keys: bool = False,
        field_extra_keys_without_x_prefix: set[str] | None = None,
        model_extra_keys: set[str] | None = None,
        model_extra_keys_without_x_prefix: set[str] | None = None,
        wrap_string_literal: bool | None = None,
        use_title_as_name: bool = False,
        use_operation_id_as_name: bool = False,
        use_unique_items_as_set: bool = False,
        use_tuple_for_fixed_items: bool = False,
        allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints,
        http_headers: Sequence[tuple[str, str]] | None = None,
        http_ignore_tls: bool = False,
        http_timeout: float | None = None,
        use_annotated: bool = False,
        use_serialize_as_any: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
        use_decimal_for_multiple_of: bool = False,
        original_field_name_delimiter: str | None = None,
        use_double_quotes: bool = False,
        use_union_operator: bool = False,
        allow_responses_without_content: bool = False,
        collapse_root_models: bool = False,
        collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None = None,
        collapse_reuse_models: bool = False,
        skip_root_model: bool = False,
        use_type_alias: bool = False,
        special_field_name_prefix: str | None = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
        keep_model_order: bool = False,
        use_one_literal_as_default: bool = False,
        use_enum_values_in_discriminator: bool = False,
        known_third_party: list[str] | None = None,
        custom_formatters: list[str] | None = None,
        custom_formatters_kwargs: dict[str, Any] | None = None,
        use_pendulum: bool = False,
        use_standard_primitive_types: bool = False,
        http_query_parameters: Sequence[tuple[str, str]] | None = None,
        treat_dot_as_module: bool | None = None,
        use_exact_imports: bool = False,
        default_field_extras: dict[str, Any] | None = None,
        target_datetime_class: DatetimeClassType | None = None,
        target_date_class: DateClassType | None = None,
        keyword_only: bool = False,
        frozen_dataclasses: bool = False,
        no_alias: bool = False,
        use_frozen_field: bool = False,
        use_default_factory_for_optional_nested_models: bool = False,
        formatters: list[Formatter] = DEFAULT_FORMATTERS,
        defer_formatting: bool = False,
        parent_scoped_naming: bool = False,
        naming_strategy: NamingStrategy | None = None,
        duplicate_name_suffix: dict[str, str] | None = None,
        dataclass_arguments: DataclassArguments | None = None,
        type_mappings: list[str] | None = None,
        type_overrides: dict[str, str] | None = None,
        read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None,
        field_type_collision_strategy: FieldTypeCollisionStrategy | None = None,
        target_pydantic_version: TargetPydanticVersion | None = None,
    ) -> None:
        """Initialize the Parser with configuration options."""
        self.keyword_only = keyword_only
        self.target_pydantic_version = target_pydantic_version
        self.frozen_dataclasses = frozen_dataclasses
        self.data_type_manager: DataTypeManager = data_type_manager_type(
            python_version=target_python_version,
            use_standard_collections=use_standard_collections,
            use_generic_container_types=use_generic_container_types,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
            use_decimal_for_multiple_of=use_decimal_for_multiple_of,
            strict_types=strict_types,
            use_union_operator=use_union_operator,
            use_pendulum=use_pendulum,
            use_standard_primitive_types=use_standard_primitive_types,
            target_datetime_class=target_datetime_class,
            target_date_class=target_date_class,
            treat_dot_as_module=treat_dot_as_module or False,
            use_serialize_as_any=use_serialize_as_any,
        )
        self.data_model_type: type[DataModel] = data_model_type
        self.data_model_root_type: type[DataModel] = data_model_root_type
        self.data_model_field_type: type[DataModelFieldBase] = data_model_field_type

        self.imports: Imports = Imports(use_exact_imports)
        self.use_exact_imports: bool = use_exact_imports
        self._append_additional_imports(additional_imports=additional_imports)
        self.class_decorators: list[str] = class_decorators or []

        self.base_class: str | None = base_class
        self.base_class_map: dict[str, str] | None = base_class_map
        self.target_python_version: PythonVersion = target_python_version
        self.results: list[DataModel] = []
        self.dump_resolve_reference_action: Callable[[Iterable[str]], str] | None = dump_resolve_reference_action
        self.validation: bool = validation
        self.field_constraints: bool = field_constraints
        self.snake_case_field: bool = snake_case_field
        self.strip_default_none: bool = strip_default_none
        self.apply_default_values_for_required_fields: bool = apply_default_values_for_required_fields
        self.force_optional_for_required_fields: bool = force_optional_for_required_fields
        self.use_schema_description: bool = use_schema_description
        self.use_field_description: bool = use_field_description
        self.use_field_description_example: bool = use_field_description_example
        self.use_inline_field_description: bool = use_inline_field_description
        self.use_default_kwarg: bool = use_default_kwarg
        self.reuse_model: bool = reuse_model
        self.reuse_scope: ReuseScope | None = reuse_scope
        self.shared_module_name: str = shared_module_name
        self.encoding: str = encoding
        self.enum_field_as_literal: LiteralType | None = enum_field_as_literal
        self.enum_field_as_literal_map: dict[str, str] = enum_field_as_literal_map or {}
        self.ignore_enum_constraints: bool = ignore_enum_constraints
        self.set_default_enum_member: bool = set_default_enum_member
        self.use_subclass_enum: bool = use_subclass_enum
        self.use_specialized_enum: bool = use_specialized_enum
        self.strict_nullable: bool = strict_nullable
        self.use_generic_container_types: bool = use_generic_container_types
        self.use_union_operator: bool = use_union_operator
        self.enable_faux_immutability: bool = enable_faux_immutability
        self.custom_class_name_generator: Callable[[str], str] | None = custom_class_name_generator
        self.field_extra_keys: set[str] = field_extra_keys or set()
        self.field_extra_keys_without_x_prefix: set[str] = field_extra_keys_without_x_prefix or set()
        self.model_extra_keys: set[str] = model_extra_keys or set()
        self.model_extra_keys_without_x_prefix: set[str] = model_extra_keys_without_x_prefix or set()
        self.field_include_all_keys: bool = field_include_all_keys

        self.remote_text_cache: DefaultPutDict[str, str] = remote_text_cache or DefaultPutDict()
        self.current_source_path: Path | None = None
        self.use_title_as_name: bool = use_title_as_name
        self.use_operation_id_as_name: bool = use_operation_id_as_name
        self.use_unique_items_as_set: bool = use_unique_items_as_set
        self.use_tuple_for_fixed_items: bool = use_tuple_for_fixed_items
        self.allof_merge_mode: AllOfMergeMode = allof_merge_mode
        self.dataclass_arguments = dataclass_arguments

        if base_path:
            self.base_path = base_path
        elif isinstance(source, Path):
            self.base_path = source.absolute() if source.is_dir() else source.absolute().parent
        else:
            self.base_path = Path.cwd()

        self.source: str | Path | list[Path] | ParseResult | dict[str, YamlValue] = source
        self.custom_template_dir = custom_template_dir
        self.extra_template_data: defaultdict[str, Any] = extra_template_data or defaultdict(dict)

        self.use_generic_base_class: bool = use_generic_base_class
        self.generic_base_class_config: dict[str, Any] = {}

        if allow_population_by_field_name:
            if use_generic_base_class:
                self.generic_base_class_config["allow_population_by_field_name"] = True
            else:
                self.extra_template_data[ALL_MODEL]["allow_population_by_field_name"] = True

        if allow_extra_fields:
            if use_generic_base_class:
                self.generic_base_class_config["allow_extra_fields"] = True
            else:
                self.extra_template_data[ALL_MODEL]["allow_extra_fields"] = True

        if extra_fields:
            if use_generic_base_class:
                self.generic_base_class_config["extra_fields"] = extra_fields
            else:
                self.extra_template_data[ALL_MODEL]["extra_fields"] = extra_fields

        if enable_faux_immutability:
            if use_generic_base_class:
                self.generic_base_class_config["allow_mutation"] = False
            else:
                self.extra_template_data[ALL_MODEL]["allow_mutation"] = False

        if use_attribute_docstrings:
            if use_generic_base_class:
                self.generic_base_class_config["use_attribute_docstrings"] = True
            else:
                self.extra_template_data[ALL_MODEL]["use_attribute_docstrings"] = True

        if target_pydantic_version:
            if use_generic_base_class:
                self.generic_base_class_config["target_pydantic_version"] = target_pydantic_version
            else:
                self.extra_template_data[ALL_MODEL]["target_pydantic_version"] = target_pydantic_version

        self.model_resolver = ModelResolver(
            base_url=source.geturl() if isinstance(source, ParseResult) else None,
            singular_name_suffix="" if disable_appending_item_suffix else None,
            aliases=aliases,
            empty_field_name=empty_enum_field_name,
            snake_case_field=snake_case_field,
            custom_class_name_generator=custom_class_name_generator,
            base_path=self.base_path,
            original_field_name_delimiter=original_field_name_delimiter,
            special_field_name_prefix=special_field_name_prefix,
            remove_special_field_name_prefix=remove_special_field_name_prefix,
            capitalise_enum_members=capitalise_enum_members,
            no_alias=no_alias,
            parent_scoped_naming=parent_scoped_naming,
            treat_dot_as_module=treat_dot_as_module,
            naming_strategy=naming_strategy,
            duplicate_name_suffix_map=duplicate_name_suffix,
        )
        self.class_name: str | None = class_name
        self.wrap_string_literal: bool | None = wrap_string_literal
        self.http_headers: Sequence[tuple[str, str]] | None = http_headers
        self.http_query_parameters: Sequence[tuple[str, str]] | None = http_query_parameters
        self.http_ignore_tls: bool = http_ignore_tls
        self.http_timeout: float | None = http_timeout
        self.use_annotated: bool = use_annotated
        if self.use_annotated and not self.field_constraints:  # pragma: no cover
            msg = "`use_annotated=True` has to be used with `field_constraints=True`"
            raise Exception(msg)  # noqa: TRY002
        self.use_serialize_as_any: bool = use_serialize_as_any
        self.use_non_positive_negative_number_constrained_types = use_non_positive_negative_number_constrained_types
        self.use_double_quotes = use_double_quotes
        self.allow_responses_without_content = allow_responses_without_content
        self.collapse_root_models = collapse_root_models
        self.collapse_root_models_name_strategy = collapse_root_models_name_strategy
        self.collapse_reuse_models = collapse_reuse_models
        self.skip_root_model = skip_root_model
        self.use_type_alias = use_type_alias
        self.capitalise_enum_members = capitalise_enum_members
        self.keep_model_order = keep_model_order
        self.use_one_literal_as_default = use_one_literal_as_default
        self.use_enum_values_in_discriminator = use_enum_values_in_discriminator
        self.known_third_party = known_third_party
        self.custom_formatter = custom_formatters
        self.custom_formatters_kwargs = custom_formatters_kwargs
        self.treat_dot_as_module = treat_dot_as_module
        self.default_field_extras: dict[str, Any] | None = default_field_extras
        self.formatters: list[Formatter] = formatters
        self.defer_formatting: bool = defer_formatting
        self.type_mappings: dict[tuple[str, str], str] = Parser._parse_type_mappings(type_mappings)
        self.type_overrides: dict[str, str] = type_overrides or {}
        self._type_override_imports: dict[str, Import] = {
            key: Import.from_full_path(value) for key, value in self.type_overrides.items()
        }
        self.read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = read_only_write_only_model_type
        self.use_frozen_field: bool = use_frozen_field
        self.use_default_factory_for_optional_nested_models: bool = use_default_factory_for_optional_nested_models
        self.field_type_collision_strategy: FieldTypeCollisionStrategy | None = field_type_collision_strategy

    @property
    def field_name_model_type(self) -> ModelType:
        """Get the ModelType for field name validation based on data_model_type.

        Returns ModelType.PYDANTIC for Pydantic models (which have reserved attributes
        like 'schema', 'model_fields', etc.), and ModelType.CLASS for other model types
        (TypedDict, dataclass, msgspec) which don't have such constraints.
        """
        if issubclass(
            self.data_model_type,
            (pydantic_model.BaseModel, pydantic_model_v2.BaseModel),
        ):
            return ModelType.PYDANTIC
        return ModelType.CLASS

    @staticmethod
    def _parse_type_mappings(type_mappings: list[str] | None) -> dict[tuple[str, str], str]:
        """Parse type mappings from CLI format to internal format.

        Supports two formats:
        - "type+format=target" (e.g., "string+binary=string")
        - "format=target" (e.g., "binary=string", assumes type="string")

        Returns a dict mapping (type, format) tuples to target type names.
        """
        if not type_mappings:
            return {}

        result: dict[tuple[str, str], str] = {}
        for mapping in type_mappings:
            if "=" not in mapping:
                msg = f"Invalid type mapping format: {mapping!r}. Expected 'type+format=target' or 'format=target'."
                raise ValueError(msg)

            source, target = mapping.split("=", 1)
            if "+" in source:
                type_, format_ = source.split("+", 1)
            else:
                # Default to "string" type if only format is specified
                type_ = "string"
                format_ = source

            result[type_, format_] = target

        return result

    @property
    def iter_source(self) -> Iterator[Source]:
        """Iterate over all source files to be parsed."""
        match self.source:
            case str():
                yield Source(path=Path(), text=self.source)
            case dict():
                yield Source.from_dict(self.source)
            case Path() as path:  # pragma: no cover
                if path.is_dir():
                    for p in sorted(path.rglob("*"), key=lambda p: p.name):
                        if p.is_file():
                            yield Source.from_path(p, self.base_path, self.encoding)
                else:
                    yield Source.from_path(path, self.base_path, self.encoding)
            case list() as paths:  # pragma: no cover
                for path in paths:
                    yield Source.from_path(path, self.base_path, self.encoding)
            case _:
                yield Source(
                    path=Path(self.source.path),
                    text=self.remote_text_cache.get_or_put(
                        self.source.geturl(), default_factory=self._get_text_from_url
                    ),
                )

    def _append_additional_imports(self, additional_imports: list[str] | None) -> None:
        if additional_imports is None:
            additional_imports = []

        for additional_import_string in additional_imports:
            if additional_import_string is None:  # pragma: no cover
                continue
            new_import = Import.from_full_path(additional_import_string)
            self.imports.append(new_import)

    def _resolve_base_class(self, class_name: str, custom_base_path: str | None = None) -> str | None:
        """Resolve base class with priority: base_class_map > customBasePath > base_class."""
        if self.base_class_map and class_name in self.base_class_map:
            return self.base_class_map[class_name]
        return custom_base_path or self.base_class

    def _get_text_from_url(self, url: str) -> str:
        from datamodel_code_generator.http import DEFAULT_HTTP_TIMEOUT, get_body  # noqa: PLC0415

        timeout = self.http_timeout if self.http_timeout is not None else DEFAULT_HTTP_TIMEOUT
        return self.remote_text_cache.get_or_put(
            url,
            default_factory=lambda _url: get_body(
                url, self.http_headers, self.http_ignore_tls, self.http_query_parameters, timeout
            ),
        )

    @classmethod
    def get_url_path_parts(cls, url: ParseResult) -> list[str]:
        """Split URL into scheme/host and path components."""
        return [
            f"{url.scheme}://{url.hostname}",
            *url.path.split("/")[1:],
        ]

    @property
    def data_type(self) -> type[DataType]:
        """Get the DataType class from the type manager."""
        return self.data_type_manager.data_type

    @abstractmethod
    def parse_raw(self) -> None:
        """Parse the raw schema source. Must be implemented by subclasses."""
        raise NotImplementedError

    @classmethod
    def _replace_model_in_list(
        cls,
        models: list[DataModel],
        original: DataModel,
        replacement: DataModel,
    ) -> None:
        """Replace model at its position in list."""
        # Use direct assignment instead of insert+remove for O(n) instead of O(2n)
        idx = models.index(original)
        models[idx] = replacement

    def __delete_duplicate_models(self, models: list[DataModel]) -> None:  # noqa: PLR0912
        model_class_names: dict[str, DataModel] = {}
        model_to_duplicate_models: defaultdict[DataModel, list[DataModel]] = defaultdict(list)
        # Use set for O(1) membership checks and collect removals for batch processing
        models_set = set(models)
        models_to_remove: set[DataModel] = set()
        for model in models:
            if model in models_to_remove:  # pragma: no cover
                continue
            if isinstance(model, self.data_model_root_type):
                root_data_type = model.fields[0].data_type

                # backward compatible
                # Remove duplicated root model
                if (
                    root_data_type.reference
                    and not root_data_type.is_dict
                    and not root_data_type.is_list
                    and root_data_type.reference.source in models_set
                    and root_data_type.reference.name
                    == self.model_resolver.get_class_name(model.reference.original_name, unique=False).name
                ):
                    model.reference.replace_children_references(root_data_type.reference)
                    models_to_remove.add(model)
                    for data_type in model.all_data_types:
                        if data_type.reference:
                            data_type.remove_reference()
                    continue

                # Remove self from all DataModel children's base_classes
                for child in model.reference.iter_data_model_children():
                    child.base_classes = [bc for bc in child.base_classes if bc.reference != model.reference]
                    if not child.base_classes:  # pragma: no cover
                        child.set_base_class()

            class_name = model.duplicate_class_name or model.class_name
            if class_name in model_class_names:
                original_model = model_class_names[class_name]
                if model.get_dedup_key(model.duplicate_class_name, use_default=False) == original_model.get_dedup_key(
                    original_model.duplicate_class_name, use_default=False
                ):
                    model_to_duplicate_models[original_model].append(model)
                    continue
            model_class_names[class_name] = model
        for model, duplicate_models in model_to_duplicate_models.items():
            for duplicate_model in duplicate_models:
                duplicate_model.reference.replace_children_references(model.reference)
                # Deduplicate base_classes in all DataModel children
                for child in duplicate_model.reference.iter_data_model_children():
                    child.base_classes = list(
                        {f"{c.module_name}.{c.type_hint}": c for c in child.base_classes}.values()
                    )
                models_to_remove.add(duplicate_model)
        # Batch removal: O(n) instead of O(n²)
        if models_to_remove:
            models[:] = [m for m in models if m not in models_to_remove]

    def __replace_duplicate_name_in_module(self, models: list[DataModel]) -> None:
        scoped_model_resolver = ModelResolver(
            exclude_names={i.alias or i.import_ for m in models for i in m.imports},
            duplicate_name_suffix="Model",
            custom_class_name_generator=(lambda name: name) if self.custom_class_name_generator else None,
        )

        model_names: dict[str, DataModel] = {}
        for model in models:
            class_name: str = model.class_name
            generated_name: str = scoped_model_resolver.add([model.path], class_name, unique=True, class_name=True).name
            if class_name != generated_name:
                model.class_name = generated_name
            model_names[model.class_name] = model

        for model in models:
            duplicate_name = model.duplicate_class_name
            # check only first desired name
            if duplicate_name and duplicate_name not in model_names:
                del model_names[model.class_name]
                model.class_name = duplicate_name
                model_names[duplicate_name] = model

    def __change_from_import(  # noqa: PLR0913, PLR0914
        self,
        models: list[DataModel],
        imports: Imports,
        scoped_model_resolver: ModelResolver,
        *,
        init: bool,
        internal_modules: set[tuple[str, ...]] | None = None,
        model_path_to_module_name: dict[str, str] | None = None,
    ) -> None:
        model_paths = {model.path for model in models}
        internal_modules = internal_modules or set()
        model_path_to_module_name = model_path_to_module_name or {}

        for model in models:
            scoped_model_resolver.add([model.path], model.class_name)
        for model in models:
            before_import = model.imports
            imports.append(before_import)
            current_module_name = model_path_to_module_name.get(model.path, model.module_name)
            for data_type in model.all_data_types:
                if not data_type.reference or data_type.reference.path in model_paths:
                    continue

                ref_module_name = model_path_to_module_name.get(
                    data_type.reference.path,
                    data_type.full_name.rsplit(".", 1)[0] if "." in data_type.full_name else "",
                )
                target_full_name = (
                    f"{ref_module_name}.{data_type.reference.short_name}"
                    if ref_module_name
                    else data_type.reference.short_name
                )

                if isinstance(data_type, BaseClassDataType):
                    left, right = relative(current_module_name, target_full_name)
                    is_ancestor = is_ancestor_package_reference(current_module_name, target_full_name)
                    from_ = left if is_ancestor else (f"{left}{right}" if left.endswith(".") else f"{left}.{right}")
                    import_ = data_type.reference.short_name
                    full_path = from_, import_
                else:
                    from_, import_ = full_path = relative(current_module_name, target_full_name)
                    if imports.use_exact:
                        from_, import_ = exact_import(from_, import_, data_type.reference.short_name)
                    import_ = import_.replace("-", "_")
                    current_module_path = tuple(current_module_name.split(".")) if current_module_name else ()
                    if (  # pragma: no cover
                        len(current_module_path) > 1
                        and current_module_path[-1].count(".") > 0
                        and not self.treat_dot_as_module
                    ):
                        rel_path_depth = current_module_path[-1].count(".")
                        from_ = from_[rel_path_depth:]

                    ref_module = tuple(target_full_name.split(".")[:-1])

                    is_module_class_collision = (
                        ref_module and import_ == data_type.reference.short_name and ref_module[-1] == import_
                    )

                    if from_ and (ref_module in internal_modules or is_module_class_collision):
                        from_ = f"{from_}{import_}" if from_.endswith(".") else f"{from_}.{import_}"
                        import_ = data_type.reference.short_name
                        full_path = from_, import_

                alias = scoped_model_resolver.add(full_path, import_).name

                name = data_type.reference.short_name
                if from_ and import_ and alias != name:
                    data_type.alias = alias if data_type.reference.short_name == import_ else f"{alias}.{name}"

                if init and not target_full_name.startswith(current_module_name + "."):
                    from_ = "." + from_
                imports.append(
                    Import(
                        from_=from_,
                        import_=import_,
                        alias=alias,
                        reference_path=data_type.reference.path,
                    ),
                )
            after_import = model.imports
            if before_import != after_import:
                imports.append(after_import)

    @classmethod
    def __extract_inherited_enum(cls, models: list[DataModel]) -> None:
        for model in models.copy():
            if model.fields:
                continue
            enums: list[Enum] = []
            for base_model in model.base_classes:
                if not base_model.reference:
                    continue
                source_model = base_model.reference.source
                if isinstance(source_model, Enum):
                    enums.append(source_model)
            if enums:
                merged_enum = enums[0].__class__(
                    fields=[f for e in enums for f in e.fields],
                    description=model.description,
                    reference=model.reference,
                )
                cls._replace_model_in_list(models, model, merged_enum)

    def _create_discriminator_data_type(
        self,
        enum_source: Enum | None,
        type_names: list[str],
        discriminator_model: DataModel,
        imports: Imports,
    ) -> DataType:
        """Create a data type for discriminator field, using enum literals if available."""
        if enum_source:
            enum_class_name = enum_source.reference.short_name
            enum_member_literals: list[tuple[str, str]] = []
            for value in type_names:
                member = enum_source.find_member(value)
                if member and member.field.name:
                    enum_member_literals.append((enum_class_name, member.field.name))
                else:  # pragma: no cover
                    enum_member_literals.append((enum_class_name, value))
            data_type = self.data_type(enum_member_literals=enum_member_literals)
            if enum_source.module_path != discriminator_model.module_path:  # pragma: no cover
                imports.append(Import.from_full_path(enum_source.name))
        else:
            data_type = self.data_type(literals=type_names)
        return data_type

    def __apply_discriminator_type(  # noqa: PLR0912, PLR0914, PLR0915
        self,
        models: list[DataModel],
        imports: Imports,
    ) -> None:
        for model in models:  # noqa: PLR1702
            for field in model.fields:
                discriminator = field.extras.get("discriminator")
                if not discriminator or not isinstance(discriminator, dict):
                    continue
                property_name = discriminator.get("propertyName")
                if not property_name:  # pragma: no cover
                    continue
                field_name, alias = self.model_resolver.get_valid_field_name_and_alias(
                    field_name=property_name, model_type=self.field_name_model_type
                )
                discriminator["propertyName"] = field_name
                mapping = discriminator.get("mapping", {})
                for data_type in field.data_type.data_types:
                    if not data_type.reference:  # pragma: no cover
                        continue
                    discriminator_model = data_type.reference.source

                    if (
                        not isinstance(discriminator_model, DataModel) or not discriminator_model.SUPPORTS_DISCRIMINATOR
                    ):  # pragma: no cover
                        continue

                    type_names: list[str] = []

                    def check_paths(
                        model: pydantic_model.BaseModel | pydantic_model_v2.BaseModel | Reference,
                        mapping: dict[str, str],
                        type_names: list[str] = type_names,
                    ) -> None:
                        """Validate discriminator mapping paths for a model."""
                        for name, path in mapping.items():
                            if (model.path.split("#/")[-1] != path.split("#/")[-1]) and (
                                path.startswith("#/") or model.path[:-1] != path.split("/")[-1]
                            ):
                                t_path = path[str(path).find("/") + 1 :]
                                t_disc = model.path[: str(model.path).find("#")].lstrip("../")  # noqa: B005
                                t_disc_2 = "/".join(t_disc.split("/")[1:])
                                if t_path not in {t_disc, t_disc_2}:
                                    continue
                            type_names.append(name)

                    # First try to get the discriminator value from the const field
                    for discriminator_field in discriminator_model.fields:
                        if field_name not in {discriminator_field.original_name, discriminator_field.name}:
                            continue
                        if discriminator_field.extras.get("const"):
                            type_names = [discriminator_field.extras["const"]]
                            break

                    # If no const value found, try to get it from the mapping
                    if not type_names:
                        # Check the main discriminator model path
                        if mapping:
                            check_paths(discriminator_model, mapping)  # pyright: ignore[reportArgumentType]

                            # Check the base_classes if they exist
                            if len(type_names) == 0:
                                for base_class in discriminator_model.base_classes:
                                    check_paths(base_class.reference, mapping)  # pyright: ignore[reportArgumentType]
                        else:
                            for discriminator_field in discriminator_model.fields:
                                if field_name not in {discriminator_field.original_name, discriminator_field.name}:
                                    continue

                                literals = discriminator_field.data_type.literals
                                if literals and len(literals) == 1:  # pragma: no cover
                                    type_names = [str(v) for v in literals]
                                    break

                                enum_source = discriminator_field.data_type.find_source(Enum)
                                if enum_source and len(enum_source.fields) == 1:
                                    first_field = enum_source.fields[0]
                                    raw_default = first_field.default
                                    if isinstance(raw_default, str):
                                        type_names = [raw_default.strip("'\"")]
                                    else:  # pragma: no cover
                                        type_names = [str(raw_default)]
                                    break

                            if not type_names:
                                type_names = [discriminator_model.path.split("/")[-1]]

                    if not type_names:  # pragma: no cover
                        msg = f"Discriminator type is not found. {data_type.reference.path}"
                        raise RuntimeError(msg)

                    enum_from_base: Enum | None = None
                    if self.use_enum_values_in_discriminator:
                        for base_class in discriminator_model.base_classes:
                            if not base_class.reference or not base_class.reference.source:  # pragma: no cover
                                continue
                            base_model = base_class.reference.source
                            if not isinstance(  # pragma: no cover
                                base_model,
                                (
                                    pydantic_model.BaseModel,
                                    pydantic_model_v2.BaseModel,
                                    dataclass_model.DataClass,
                                    msgspec_model.Struct,
                                ),
                            ):
                                continue
                            for base_field in base_model.fields:  # pragma: no branch
                                if field_name not in {base_field.original_name, base_field.name}:  # pragma: no cover
                                    continue
                                enum_from_base = base_field.data_type.find_source(Enum)
                                if enum_from_base:  # pragma: no branch
                                    break
                            if enum_from_base:  # pragma: no branch
                                break

                    has_one_literal = False
                    for discriminator_field in discriminator_model.fields:
                        if field_name not in {discriminator_field.original_name, discriminator_field.name}:
                            continue
                        literals = discriminator_field.data_type.literals
                        const_value = discriminator_field.extras.get("const")
                        expected_value = type_names[0] if type_names else None

                        # Check if literals match (existing behavior)
                        literals_match = len(literals) == 1 and literals[0] == expected_value
                        # Check if const value matches (for msgspec with type: string + const)
                        const_match = const_value is not None and const_value == expected_value

                        if literals_match:
                            has_one_literal = True
                            if isinstance(discriminator_model, msgspec_model.Struct):  # pragma: no cover
                                discriminator_model.add_base_class_kwarg("tag_field", f"'{field_name}'")
                                discriminator_model.add_base_class_kwarg("tag", discriminator_field.represented_default)
                                discriminator_field.extras["is_classvar"] = True
                            # Found the discriminator field, no need to keep looking
                            break

                        # For msgspec with const value but no literal (type: string + const case)
                        if const_match and isinstance(discriminator_model, msgspec_model.Struct):  # pragma: no cover
                            has_one_literal = True
                            discriminator_model.add_base_class_kwarg("tag_field", f"'{field_name}'")
                            discriminator_model.add_base_class_kwarg("tag", repr(const_value))
                            discriminator_field.extras["is_classvar"] = True
                            break

                        enum_source: Enum | None = None
                        if self.use_enum_values_in_discriminator:
                            enum_source = (  # pragma: no cover
                                discriminator_field.data_type.find_source(Enum) or enum_from_base
                            )

                        for field_data_type in discriminator_field.data_type.all_data_types:
                            if field_data_type.reference:  # pragma: no cover
                                field_data_type.remove_reference()

                        discriminator_field.data_type = self._create_discriminator_data_type(
                            enum_source, type_names, discriminator_model, imports
                        )
                        discriminator_field.data_type.parent = discriminator_field
                        discriminator_field.required = True
                        imports.append(discriminator_field.imports)
                        has_one_literal = True
                    if not has_one_literal:
                        new_data_type = self._create_discriminator_data_type(
                            enum_from_base, type_names, discriminator_model, imports
                        )
                        discriminator_model.fields.append(
                            self.data_model_field_type(
                                name=field_name,
                                data_type=new_data_type,
                                required=True,
                                alias=alias,
                            )
                        )
            has_imported_literal = any(import_ == IMPORT_LITERAL for import_ in imports)
            if has_imported_literal:  # pragma: no cover
                imports.append(IMPORT_LITERAL)

    @classmethod
    def _create_set_from_list(cls, data_type: DataType) -> DataType | None:
        if data_type.is_list:
            new_data_type = model_copy(data_type)
            new_data_type.is_list = False
            new_data_type.is_set = True
            for data_type_ in new_data_type.data_types:
                data_type_.parent = new_data_type
            return new_data_type
        if data_type.data_types:  # pragma: no cover
            for nested_data_type in data_type.data_types[:]:
                set_data_type = cls._create_set_from_list(nested_data_type)
                if set_data_type:  # pragma: no cover
                    nested_data_type.swap_with(set_data_type)
            return data_type
        return None  # pragma: no cover

    def __replace_unique_list_to_set(self, models: list[DataModel]) -> None:
        for model in models:
            for model_field in model.fields:
                if not self.use_unique_items_as_set:
                    continue

                if not (model_field.constraints and model_field.constraints.unique_items):
                    continue
                set_data_type = self._create_set_from_list(model_field.data_type)
                if set_data_type:  # pragma: no cover
                    # Check if default list elements are hashable before converting type
                    if isinstance(model_field.default, list):
                        try:
                            converted_default = set(model_field.default)
                        except TypeError:
                            # Elements are not hashable (e.g., contains dicts)
                            # Skip both type and default conversion to keep consistency
                            continue
                        model_field.default = converted_default
                    model_field.replace_data_type(set_data_type)

    @classmethod
    def __set_reference_default_value_to_field(cls, models: list[DataModel]) -> None:
        for model in models:
            for model_field in model.fields:
                if not model_field.data_type.reference or model_field.has_default:
                    continue
                if (
                    isinstance(model_field.data_type.reference.source, DataModel)
                    and model_field.data_type.reference.source.default != UNDEFINED
                ):
                    # pragma: no cover
                    model_field.default = model_field.data_type.reference.source.default

    def __reuse_model(self, models: list[DataModel], require_update_action_models: list[str]) -> None:
        if not self.reuse_model or self.reuse_scope == ReuseScope.Tree:
            return
        model_cache: dict[tuple[HashableComparable, ...], Reference] = {}
        duplicates = []
        for model in models.copy():
            model_key = model.get_dedup_key()
            cached_model_reference = model_cache.get(model_key)
            if cached_model_reference:
                if isinstance(model, Enum) or self.collapse_reuse_models:
                    model.replace_children_in_models(models, cached_model_reference)
                    duplicates.append(model)
                else:
                    inherited_model = model.create_reuse_model(cached_model_reference)
                    if cached_model_reference.path in require_update_action_models:
                        add_model_path_to_list(require_update_action_models, inherited_model)
                    self._replace_model_in_list(models, model, inherited_model)
            else:
                model_cache[model_key] = model.reference

        for duplicate in duplicates:
            models.remove(duplicate)

    def __find_duplicate_models_across_modules(  # noqa: PLR6301
        self,
        module_models: list[tuple[tuple[str, ...], list[DataModel]]],
    ) -> list[tuple[tuple[str, ...], DataModel, tuple[str, ...], DataModel]]:
        """Find duplicate models across all modules by comparing render output and imports."""
        all_models: list[tuple[tuple[str, ...], DataModel]] = []
        for module, models in module_models:
            all_models.extend((module, model) for model in models)

        model_cache: dict[tuple[HashableComparable, ...], tuple[tuple[str, ...], DataModel]] = {}
        duplicates: list[tuple[tuple[str, ...], DataModel, tuple[str, ...], DataModel]] = []

        for module, model in all_models:
            model_key = model.get_dedup_key()
            cached = model_cache.get(model_key)
            if cached:
                canonical_module, canonical_model = cached
                duplicates.append((module, model, canonical_module, canonical_model))
            else:
                model_cache[model_key] = (module, model)

        return duplicates

    def __validate_shared_module_name(
        self,
        module_models: list[tuple[tuple[str, ...], list[DataModel]]],
    ) -> None:
        """Validate that the shared module name doesn't conflict with existing modules."""
        shared_module = self.shared_module_name
        existing_module_names = {module[0] for module, _ in module_models}
        if shared_module in existing_module_names:
            msg = (
                f"Schema file or directory '{shared_module}' conflicts with the shared module name. "
                f"Use --shared-module-name to specify a different name."
            )
            raise Error(msg)

    def __create_shared_module_from_duplicates(  # noqa: PLR0912
        self,
        module_models: list[tuple[tuple[str, ...], list[DataModel]]],
        duplicates: list[tuple[tuple[str, ...], DataModel, tuple[str, ...], DataModel]],
        require_update_action_models: list[str],
    ) -> tuple[tuple[str, ...], list[DataModel]]:
        """Create shared module with canonical models and replace duplicates with inherited models."""
        shared_module = self.shared_module_name

        shared_models: list[DataModel] = []
        canonical_to_shared_ref: dict[DataModel, Reference] = {}
        canonical_models_seen: set[DataModel] = set()

        # Process in order of first appearance in duplicates to ensure stable ordering
        for _, _, _, canonical in duplicates:
            if canonical in canonical_models_seen:
                continue
            canonical_models_seen.add(canonical)
            canonical.file_path = Path(f"{shared_module}.py")
            canonical_to_shared_ref[canonical] = canonical.reference
            shared_models.append(canonical)

        supports_inheritance = issubclass(
            self.data_model_type,
            (
                pydantic_model.BaseModel,
                pydantic_model_v2.BaseModel,
                dataclass_model.DataClass,
            ),
        )

        module_models_sets: dict[tuple[str, ...], set[DataModel]] = {
            module: set(models) for module, models in module_models
        }
        models_to_remove: dict[tuple[str, ...], set[DataModel]] = defaultdict(set)

        for duplicate_module, duplicate_model, _, canonical_model in duplicates:
            shared_ref = canonical_to_shared_ref[canonical_model]
            models_set = module_models_sets.get(duplicate_module)
            if not models_set or duplicate_model not in models_set:  # pragma: no cover
                msg = f"Duplicate model {duplicate_model.name} not found in module {duplicate_module}"
                raise RuntimeError(msg)

            for module, models in module_models:
                if module != duplicate_module:
                    continue
                if isinstance(duplicate_model, Enum) or not supports_inheritance or self.collapse_reuse_models:
                    duplicate_model.replace_children_in_models(models, shared_ref)
                    models_to_remove[module].add(duplicate_model)
                else:
                    inherited_model = duplicate_model.create_reuse_model(shared_ref)
                    if shared_ref.path in require_update_action_models:
                        add_model_path_to_list(require_update_action_models, inherited_model)
                    self._replace_model_in_list(models, duplicate_model, inherited_model)
                break

        for canonical in canonical_models_seen:
            for module, models_set in module_models_sets.items():
                if canonical in models_set:
                    models_to_remove[module].add(canonical)
                    break
            else:  # pragma: no cover
                msg = f"Canonical model {canonical.name} not found in any module"
                raise RuntimeError(msg)

        for module, models in module_models:
            to_remove = models_to_remove.get(module)
            if to_remove:
                models[:] = [m for m in models if m not in to_remove]

        return (shared_module,), shared_models

    def __reuse_model_tree_scope(
        self,
        module_models: list[tuple[tuple[str, ...], list[DataModel]]],
        require_update_action_models: list[str],
    ) -> tuple[tuple[str, ...], list[DataModel]] | None:
        """Deduplicate models across all modules, placing shared models in shared.py."""
        if not self.reuse_model or self.reuse_scope != ReuseScope.Tree:
            return None

        duplicates = self.__find_duplicate_models_across_modules(module_models)
        if not duplicates:
            return None

        self.__validate_shared_module_name(module_models)
        return self.__create_shared_module_from_duplicates(module_models, duplicates, require_update_action_models)

    def __collapse_root_models(  # noqa: PLR0912, PLR0914, PLR0915
        self,
        models: list[DataModel],
        unused_models: list[DataModel],
        imports: Imports,
        scoped_model_resolver: ModelResolver,
    ) -> None:
        if not self.collapse_root_models:
            return

        for model in models:  # noqa: PLR1702
            for model_field in model.fields:
                for data_type in model_field.data_type.all_data_types:
                    reference = data_type.reference
                    if not reference or not isinstance(reference.source, self.data_model_root_type):
                        # If the data type is not a reference, we can't collapse it.
                        # If it's a reference to a root model type, we don't do anything.
                        continue

                    # Use root-type as model_field type
                    root_type_model = reference.source
                    root_type_field = root_type_model.fields[0]

                    if (
                        self.field_constraints
                        and isinstance(root_type_field.constraints, ConstraintsBase)
                        and root_type_field.constraints.has_constraints
                        and any(d for d in model_field.data_type.all_data_types if d.is_dict or d.is_union or d.is_list)
                    ):
                        continue  # pragma: no cover

                    if root_type_field.data_type.reference:
                        if self.collapse_root_models_name_strategy is None:
                            continue

                        inner_reference = root_type_field.data_type.reference
                        inner_model = cast("DataModel", inner_reference.source)

                        if self.collapse_root_models_name_strategy == CollapseRootModelsNameStrategy.Parent:
                            root_model_wrappers = [
                                parent_model
                                for child in inner_reference.children
                                if isinstance(child, DataType)
                                and (parent_model := get_most_of_parent(child, DataModel))
                                and isinstance(parent_model, self.data_model_root_type)
                            ]

                            if len(root_model_wrappers) > 1:
                                warn(
                                    f"Cannot apply 'parent' strategy for '{inner_model.class_name}' - "
                                    f"it is referenced by multiple root models: "
                                    f"{[m.class_name for m in root_model_wrappers]}. Skipping collapse.",
                                    stacklevel=2,
                                )
                                continue

                            direct_refs = [
                                c
                                for c in inner_reference.children
                                if isinstance(c, DataType)
                                and (parent_model := get_most_of_parent(c, DataModel)) is not None
                                and parent_model is not root_type_model
                                and not isinstance(parent_model, self.data_model_root_type)
                            ]

                            if direct_refs:
                                warn(
                                    f"Cannot apply 'parent' strategy for '{inner_model.class_name}' - "
                                    f"it is directly referenced by non-wrapper models. Skipping collapse.",
                                    stacklevel=2,
                                )
                                continue

                            inner_model.class_name = root_type_model.class_name
                            inner_model.reference.name = root_type_model.class_name
                            inner_model.set_reference_path(root_type_model.reference.path)

                        assert isinstance(root_type_model, DataModel)

                        root_type_model.reference.children = [
                            c
                            for c in root_type_model.reference.children
                            if c is not data_type and getattr(c, "parent", None)
                        ]

                        data_type.reference = inner_reference
                        inner_reference.children.append(data_type)

                        imports.remove_referenced_imports(root_type_model.path)
                        if not root_type_model.reference.children:
                            unused_models.append(root_type_model)

                        continue

                    # set copied data_type
                    copied_data_type = model_copy(root_type_field.data_type)
                    if isinstance(data_type.parent, self.data_model_field_type):
                        # for field
                        # override empty field by root-type field
                        model_field.extras = {
                            **root_type_field.extras,
                            **model_field.extras,
                        }
                        model_field.process_const()

                        if self.field_constraints:
                            model_field.constraints = ConstraintsBase.merge_constraints(
                                root_type_field.constraints, model_field.constraints
                            )

                        data_type.parent.data_type = copied_data_type

                    elif isinstance(data_type.parent, DataType) and data_type.parent.is_list:
                        if self.field_constraints:
                            model_field.constraints = ConstraintsBase.merge_constraints(
                                root_type_field.constraints, model_field.constraints
                            )
                        if (  # pragma: no cover
                            isinstance(
                                root_type_field,
                                pydantic_model.DataModelField,
                            )
                            and not model_field.extras.get("discriminator")
                            and not any(t.is_list for t in model_field.data_type.data_types)
                        ):
                            discriminator = root_type_field.extras.get("discriminator")
                            if discriminator:
                                model_field.extras["discriminator"] = discriminator
                        assert isinstance(data_type.parent, DataType)
                        data_type.parent.data_types.remove(data_type)  # pragma: no cover
                        data_type.parent.data_types.append(copied_data_type)

                    elif isinstance(data_type.parent, DataType):
                        # for data_type
                        data_type_id = id(data_type)
                        data_type.parent.data_types = [
                            d for d in (*data_type.parent.data_types, copied_data_type) if id(d) != data_type_id
                        ]
                    else:  # pragma: no cover
                        continue

                    for d in copied_data_type.all_data_types:
                        if d.reference is None:
                            continue
                        from_, import_ = full_path = relative(model.module_name, d.full_name)
                        if from_ and import_:
                            alias = scoped_model_resolver.add(full_path, import_)
                            d.alias = (
                                alias.name
                                if d.reference.short_name == import_
                                else f"{alias.name}.{d.reference.short_name}"
                            )
                            imports.append([
                                Import(
                                    from_=from_,
                                    import_=import_,
                                    alias=alias.name,
                                    reference_path=d.reference.path,
                                )
                            ])

                    original_field = get_most_of_parent(data_type, DataModelFieldBase)
                    if original_field:  # pragma: no cover
                        # TODO: Improve detection of reference type
                        # Use list instead of set because Import is not hashable
                        excluded_imports = [IMPORT_OPTIONAL, IMPORT_UNION]
                        field_imports = [i for i in original_field.imports if i not in excluded_imports]
                        imports.append(field_imports)

                    data_type.remove_reference()

                    assert isinstance(root_type_model, DataModel)
                    root_type_model.reference.children = [
                        c for c in root_type_model.reference.children if getattr(c, "parent", None)
                    ]

                    imports.remove_referenced_imports(root_type_model.path)
                    if not root_type_model.reference.children:
                        unused_models.append(root_type_model)

    def __set_default_enum_member(
        self,
        models: list[DataModel],
    ) -> None:
        if not self.set_default_enum_member:
            return
        for _, model_field, data_type in iter_models_field_data_types(models):
            if not model_field.default:
                continue
            if data_type.reference and isinstance(data_type.reference.source, Enum):  # pragma: no cover
                if isinstance(model_field.default, list):
                    enum_member: list[Member] | (Member | None) = [
                        e for e in (data_type.reference.source.find_member(d) for d in model_field.default) if e
                    ]
                else:
                    enum_member = data_type.reference.source.find_member(model_field.default)
                if not enum_member:
                    continue
                model_field.default = enum_member
                if data_type.alias:
                    if isinstance(enum_member, list):
                        for enum_member_ in enum_member:
                            enum_member_.alias = data_type.alias
                    else:
                        enum_member.alias = data_type.alias

    def __wrap_root_model_default_values(
        self,
        models: list[DataModel],
    ) -> None:
        """Wrap RootModel reference default values with their type constructors."""
        if not self.use_annotated or not self.data_model_type.SUPPORTS_WRAPPED_DEFAULT:
            return
        for model, model_field, data_type in iter_models_field_data_types(models):
            if isinstance(model, (Enum, self.data_model_root_type)):
                continue
            if model_field.default is None:
                continue
            if isinstance(model_field.default, (WrappedDefault, Member)):
                continue
            if isinstance(model_field.default, list):
                continue
            if data_type.reference and isinstance(data_type.reference.source, self.data_model_root_type):
                type_name = data_type.alias or data_type.reference.short_name
                model_field.default = WrappedDefault(
                    value=model_field.default,
                    type_name=type_name,
                )

    def __override_required_field(
        self,
        models: list[DataModel],
    ) -> None:
        for model in models:
            if isinstance(model, (Enum, self.data_model_root_type)):
                continue
            for index, model_field in enumerate(model.fields[:]):
                data_type = model_field.data_type
                if (
                    not model_field.original_name  # noqa: PLR0916
                    or data_type.data_types
                    or data_type.reference
                    or data_type.type
                    or data_type.literals
                    or data_type.dict_key
                ):
                    continue

                original_field = _find_field(model_field.original_name, _find_base_classes(model))
                if not original_field:  # pragma: no cover
                    model.fields.remove(model_field)
                    continue
                copied_original_field = model_copy(original_field)
                if original_field.data_type.reference:
                    data_type = self.data_type_manager.data_type(
                        reference=original_field.data_type.reference,
                    )
                elif original_field.data_type.data_types:
                    data_type = model_copy(original_field.data_type)
                    data_type.data_types = _copy_data_types(original_field.data_type.data_types)
                    for data_type_ in data_type.data_types:
                        data_type_.parent = data_type
                else:
                    data_type = model_copy(original_field.data_type)
                data_type.parent = copied_original_field
                copied_original_field.data_type = data_type
                copied_original_field.parent = model
                copied_original_field.required = True
                model.fields.insert(index, copied_original_field)
                model.fields.remove(model_field)

    def __sort_models(
        self,
        models: list[DataModel],
        imports: Imports,
        *,
        use_deferred_annotations: bool,
    ) -> None:
        if not self.keep_model_order:
            return

        _reorder_models_keep_model_order(models, imports, use_deferred_annotations=use_deferred_annotations)

    def __change_field_name(
        self,
        models: list[DataModel],
    ) -> None:
        if not self.data_model_type.SUPPORTS_FIELD_RENAMING:
            return

        rename_type = self.field_type_collision_strategy == FieldTypeCollisionStrategy.RenameType
        all_class_names = {cast("str", m.class_name) for m in models if m.class_name}

        for model in models:
            if "Enum" in model.base_class or not model.BASE_CLASS:
                continue

            for field in model.fields:
                filed_name = field.name
                reference_type_names: set[str] = set()
                colliding_reference: Reference | None = None

                for data_type in field.data_type.all_data_types:
                    if not data_type.reference:
                        continue
                    reference_type_names.add(data_type.reference.short_name)
                    if rename_type and colliding_reference is None and data_type.reference.short_name == filed_name:
                        colliding_reference = data_type.reference

                if colliding_reference is not None:
                    resolver = ModelResolver(
                        exclude_names=all_class_names.copy(),
                        snake_case_field=self.snake_case_field,
                        remove_suffix_number=True,
                    )
                    source = cast("DataModel", colliding_reference.source)
                    resolver.exclude_names.add(cast("str", filed_name))
                    new_class_name = resolver.add(["type"], cast("str", source.class_name)).name
                    source.class_name = new_class_name
                    all_class_names.add(new_class_name)
                elif not rename_type:
                    resolver = ModelResolver(
                        exclude_names=reference_type_names,
                        snake_case_field=self.snake_case_field,
                        remove_suffix_number=True,
                    )
                    new_filed_name = resolver.add(["field"], cast("str", filed_name)).name
                    if filed_name != new_filed_name:
                        field.alias = filed_name
                        field.name = new_filed_name

    def __set_one_literal_on_default(self, models: list[DataModel]) -> None:
        if not self.use_one_literal_as_default:
            return
        for model in models:
            for model_field in model.fields:
                if not model_field.required or len(model_field.data_type.literals) != 1:
                    continue
                model_field.default = model_field.data_type.literals[0]
                model_field.required = False
                if model_field.nullable is not True:  # pragma: no cover
                    model_field.nullable = False

    def __fix_dataclass_field_ordering(self, models: list[DataModel]) -> None:
        """Fix field ordering for dataclasses with inheritance after defaults are set."""
        for model in models:
            if (inherited := self.__get_dataclass_inherited_info(model)) is None:
                continue
            inherited_names, has_default = inherited
            if not has_default or not any(self.__is_new_required_field(f, inherited_names) for f in model.fields):
                continue

            if self.target_python_version.has_kw_only_dataclass:
                for field in model.fields:
                    if self.__is_new_required_field(field, inherited_names):
                        field.extras["kw_only"] = True
            else:
                warn(
                    f"Dataclass '{model.class_name}' has a field ordering conflict due to inheritance. "
                    f"An inherited field has a default value, but new required fields are added. "
                    f"This will cause a TypeError at runtime. Consider using --target-python-version 3.10 "
                    f"or higher to enable automatic field(kw_only=True) fix.",
                    category=UserWarning,
                    stacklevel=2,
                )
            model.fields = sorted(model.fields, key=dataclass_model.has_field_assignment)

    @classmethod
    def __get_dataclass_inherited_info(cls, model: DataModel) -> tuple[set[str], bool] | None:
        """Get inherited field names and whether any has default. Returns None if not applicable."""
        if not model.SUPPORTS_KW_ONLY:
            return None
        if not model.base_classes or model.dataclass_arguments.get("kw_only"):
            return None

        inherited_names: set[str] = set()
        has_default = False
        for base in model.base_classes:
            if not base.reference or not isinstance(base.reference.source, DataModel):
                continue  # pragma: no cover
            for f in base.reference.source.iter_all_fields():
                if not f.name or f.extras.get("init") is False:
                    continue  # pragma: no cover
                inherited_names.add(f.name)
                if dataclass_model.has_field_assignment(f):
                    has_default = True

        for f in model.fields:
            if f.name not in inherited_names or f.extras.get("init") is False:
                continue
            if dataclass_model.has_field_assignment(f):  # pragma: no branch
                has_default = True
        return (inherited_names, has_default) if inherited_names else None

    def __is_new_required_field(self, field: DataModelFieldBase, inherited: set[str]) -> bool:  # noqa: PLR6301
        """Check if field is a new required init field."""
        return (
            field.name not in inherited
            and field.extras.get("init") is not False
            and not dataclass_model.has_field_assignment(field)
        )

    def __remove_overridden_models(self, models: list[DataModel]) -> list[DataModel]:
        """Remove models that are being overridden by custom types (model-level only).

        Only model-level overrides (keys without dots) cause model removal.
        Scoped overrides (ClassName.field) only affect specific fields.
        """
        if not self.type_overrides:
            return models
        # Only model-level overrides (no dot) cause model removal
        model_level_overrides = {k for k in self.type_overrides if "." not in k}
        return [m for m in models if m.class_name not in model_level_overrides]

    def __apply_type_overrides(self, models: list[DataModel]) -> None:
        """Replace field type references with custom import types.

        Supports two key formats:
        - Model-level: {"CustomType": "my_app.Type"} - applies to all references
        - Scoped: {"User.field": "my_app.Type"} - applies to specific field only

        Scoped overrides take priority over model-level overrides.
        """
        if not self._type_override_imports:
            return
        for model in models:
            for field in model.fields:
                # Check scoped override first: "ClassName.field_name"
                scoped_key = f"{model.class_name}.{field.name}"
                if scoped_key in self._type_override_imports:
                    self._apply_override_to_field(field, self._type_override_imports[scoped_key])
                else:
                    # Apply model-level overrides to nested types
                    self._apply_override_to_data_type(field.data_type)

    def _apply_override_to_field(self, field: DataModelFieldBase, override_import: Import) -> None:  # noqa: PLR6301
        """Apply override to entire field's data_type."""
        field.data_type.import_ = override_import
        field.data_type.alias = override_import.import_
        field.data_type.reference = None
        field.data_type.data_types = []  # Clear nested types

    def _apply_override_to_data_type(self, data_type: DataType) -> None:
        """Recursively apply model-level overrides to a DataType."""
        if data_type.reference and data_type.reference.name in self._type_override_imports:
            override_import = self._type_override_imports[data_type.reference.name]
            data_type.import_ = override_import
            data_type.alias = override_import.import_
            data_type.reference = None
        # Handle nested types (List[CustomType], Optional[CustomType], etc.)
        for nested in data_type.data_types:
            self._apply_override_to_data_type(nested)

    @classmethod
    def __update_type_aliases(cls, models: list[DataModel]) -> None:
        """Update type aliases and RootModels to properly handle forward references per PEP 484."""
        model_index: dict[str, int] = {m.class_name: i for i, m in enumerate(models)}

        for i, model in enumerate(models):
            if not isinstance(model, (TypeAliasBase, pydantic_model_v2.RootModel)):
                continue
            if isinstance(model, TypeStatement):
                continue

            has_forward_ref = False
            for field in model.fields:
                for data_type in field.data_type.all_data_types:
                    if not data_type.reference:
                        continue
                    source = data_type.reference.source
                    if not isinstance(source, DataModel):
                        continue  # pragma: no cover
                    if isinstance(source, TypeStatement):
                        continue  # pragma: no cover
                    if source.module_path != model.module_path:
                        continue
                    name = data_type.reference.short_name
                    source_index = model_index.get(name)
                    if source_index is not None and source_index >= i:
                        data_type.alias = f'"{name}"'
                        has_forward_ref = True

            if has_forward_ref:
                model.has_forward_reference = True

    @classmethod
    def __postprocess_result_modules(cls, results: dict[tuple[str, ...], Result]) -> dict[tuple[str, ...], Result]:
        def process(input_tuple: tuple[str, ...]) -> tuple[str, ...]:
            r = []
            for item in input_tuple:
                p = item.split(".")
                if len(p) > 1:
                    r.extend(p[:-1])
                    r.append(p[-1])
                else:
                    r.append(item)

            if len(r) >= 2:  # noqa: PLR2004
                r = [*r[:-2], f"{r[-2]}.{r[-1]}"]
            return tuple(r)

        results = {process(k): v for k, v in results.items()}

        init_result = next(v for k, v in results.items() if k[-1] == "__init__.py")
        folders = {t[:-1] if t[-1].endswith(".py") else t for t in results}
        for folder in folders:
            for i in range(len(folder)):
                subfolder = folder[: i + 1]
                init_file = (*subfolder, "__init__.py")
                results.update({init_file: init_result})
        return results

    def __change_imported_model_name(  # noqa: PLR6301
        self,
        models: list[DataModel],
        imports: Imports,
        scoped_model_resolver: ModelResolver,
    ) -> None:
        imported_names = {
            imports.alias[from_][i] if i in imports.alias[from_] and i != imports.alias[from_][i] else i
            for from_, import_ in imports.items()
            for i in import_
        }
        for model in models:
            if model.class_name not in imported_names:  # pragma: no cover
                continue

            model.reference.name = scoped_model_resolver.add(  # pragma: no cover
                path=get_special_path("imported_name", model.path.split("/")),
                original_name=model.reference.name,
                unique=True,
                class_name=True,
            ).name

    def __alias_shadowed_imports(  # noqa: PLR6301
        self,
        models: list[DataModel],
        all_model_field_names: set[str],
    ) -> None:
        for _, model_field, data_type in iter_models_field_data_types(models):
            if (
                data_type
                and data_type.import_
                and data_type.type in all_model_field_names
                and data_type.type == model_field.name
            ):
                alias = data_type.type + "_aliased"
                data_type.type = alias
                data_type.import_ = Import(
                    from_=data_type.import_.from_,
                    import_=data_type.import_.import_,
                    alias=alias,
                    reference_path=data_type.import_.reference_path,
                )

    def __apply_generic_base_class(  # noqa: PLR0912, PLR0914, PLR0915
        self,
        processed_models: Sequence[ModuleContext],
    ) -> None:
        if not self.use_generic_base_class or not self.generic_base_class_config:
            return

        all_target_models: set[DataModel] = set()
        modules_with_targets: list[tuple[tuple[str, ...], list[DataModel], list[DataModel], Imports]] = []

        for module, _mod_key, models, _init, imports, _scoped_model_resolver in processed_models:
            if not models:  # pragma: no cover
                continue

            target_models = [
                m for m in models if m.SUPPORTS_GENERIC_BASE_CLASS and not isinstance(m, self.data_model_root_type)
            ]

            if target_models:
                modules_with_targets.append((module, models, target_models, imports))
                all_target_models.update(target_models)

        if not modules_with_targets:
            return

        root_modules: list[tuple[tuple[str, ...], list[DataModel], list[DataModel], Imports]] = []
        for module_entry in modules_with_targets:
            _module, _models, target_models, _imports = module_entry
            has_root_model = False
            for model in target_models:
                parent_refs = [bc.reference for bc in model.base_classes if bc.reference]
                has_target_model_parent = any(ref.source in all_target_models for ref in parent_refs)
                if not has_target_model_parent:
                    has_root_model = True
                    break
            if has_root_model:
                root_modules.append(module_entry)

        if not root_modules:  # pragma: no cover
            root_modules = [modules_with_targets[0]]

        first_root_module, first_root_models, first_root_target_models, _first_root_imports = root_modules[0]
        first_root_file_path = first_root_target_models[0].file_path if first_root_target_models else None

        base_class_ref = Reference(path=GENERIC_BASE_CLASS_PATH, name=GENERIC_BASE_CLASS_NAME)

        base_class_model = self.data_model_type.create_base_class_model(
            config=self.generic_base_class_config,
            reference=base_class_ref,
            custom_template_dir=self.custom_template_dir,
            keyword_only=self.keyword_only,
            treat_dot_as_module=self.treat_dot_as_module,
        )

        if base_class_model is None:
            return

        base_class_model.file_path = first_root_file_path
        first_root_models.insert(0, base_class_model)

        base_class_dt = BaseClassDataType(type=base_class_ref.name, reference=base_class_ref)

        original_base_class = self.data_model_type.BASE_CLASS
        original_import = Import.from_full_path(original_base_class) if original_base_class else None
        first_root_module_name = ".".join(first_root_module[:-1]) if first_root_module else ""
        for module, _models, target_models, imports in modules_with_targets:
            current_module_name = ".".join(module[:-1]) if module else ""
            is_first_root = module == first_root_module
            for model in target_models:
                if original_import:
                    additional_imports = model._additional_imports  # noqa: SLF001
                    model._additional_imports = [i for i in additional_imports if i != original_import]  # noqa: SLF001
                parent_refs = [bc.reference for bc in model.base_classes if bc.reference]
                has_target_model_parent = any(ref.source in all_target_models for ref in parent_refs)
                if has_target_model_parent:
                    pass
                elif parent_refs:  # pragma: no cover
                    model.base_classes.insert(0, base_class_dt)
                else:
                    model.base_classes = [base_class_dt]
            if not is_first_root and original_import:
                imports.remove(original_import)
                from_ = relative(current_module_name, first_root_module_name)[0]
                from_ = (
                    f"{from_}{first_root_module[-1].replace('.py', '')}"
                    if from_.endswith(".")
                    else f"{from_}.{first_root_module[-1].replace('.py', '')}"
                )
                imports.append(Import(from_=from_, import_=base_class_ref.name))

    @classmethod
    def _collect_exports_for_init(
        cls,
        module: tuple[str, ...],
        processed_models: Sequence[ModuleContext],
        scope: AllExportsScope,
    ) -> list[tuple[str, tuple[str, ...], str]]:
        """Collect exports for __init__.py based on scope."""
        exports: list[tuple[str, tuple[str, ...], str]] = []
        base = module[:-1] if module[-1] == "__init__.py" else module
        base_len = len(base)

        for proc_module, _, proc_models, _, _, _ in processed_models:
            if not proc_models or proc_module == module:
                continue
            last = proc_module[-1]
            prefix = proc_module[:-1] if last == "__init__.py" else (*proc_module[:-1], last[:-3])
            if prefix[:base_len] != base or (depth := len(prefix) - base_len) < 1:
                continue
            if scope == AllExportsScope.Children and depth != 1:
                continue
            rel = prefix[base_len:]
            exports.extend(
                (ref.short_name, rel, ".".join(rel))
                for m in proc_models
                if (ref := m.reference) and not ref.short_name.startswith("_")
            )
        return exports

    @classmethod
    def _resolve_export_collisions(
        cls,
        exports: list[tuple[str, tuple[str, ...], str]],
        strategy: AllExportsCollisionStrategy | None,
        reserved: set[str] | None = None,
    ) -> dict[str, list[tuple[str, tuple[str, ...], str]]]:
        """Resolve name collisions in exports based on strategy."""
        reserved = reserved or set()
        by_name: dict[str, list[tuple[str, tuple[str, ...], str]]] = {}
        for item in exports:
            by_name.setdefault(item[0], []).append(item)

        if not (colliding := {n for n, items in by_name.items() if len(items) > 1 or n in reserved}):
            return dict(by_name)
        if (effective := strategy or AllExportsCollisionStrategy.Error) == AllExportsCollisionStrategy.Error:
            cls._raise_collision_error(by_name, colliding)

        used: set[str] = {n for n in by_name if n not in colliding} | reserved
        result = {n: items for n, items in by_name.items() if n not in colliding}

        for name in sorted(colliding):
            for item in sorted(by_name[name], key=lambda x: len(x[1])):
                new_name = cls._make_prefixed_name(
                    item[0], item[1], used, minimal=effective == AllExportsCollisionStrategy.MinimalPrefix
                )
                if new_name in reserved:
                    msg = (
                        f"Cannot resolve collision: '{new_name}' conflicts with __init__.py model. "
                        "Please rename one of the models."
                    )
                    raise Error(msg)
                result[new_name] = [item]
                used.add(new_name)
        return result

    @classmethod
    def _raise_collision_error(
        cls,
        by_name: dict[str, list[tuple[str, tuple[str, ...], str]]],
        colliding: set[str],
    ) -> None:
        """Raise an error with collision details."""
        details = []
        for n in colliding:
            if len(items := by_name[n]) > 1:
                details.append(f"  '{n}' is defined in: {', '.join(f'.{s}' for _, _, s in items)}")
            else:
                details.append(f"  '{n}' conflicts with a model in __init__.py")
        raise Error(
            "Name collision detected with --all-exports-scope:\n"
            + "\n".join(details)
            + "\n\nUse --all-exports-collision-strategy to specify how to handle collisions."
        )

    @staticmethod
    def _make_prefixed_name(name: str, path: tuple[str, ...], used: set[str], *, minimal: bool) -> str:
        """Generate a prefixed name, using minimal or full prefix."""
        if minimal:
            for depth in range(1, len(path) + 1):
                if (candidate := "".join(p.title().replace("_", "") for p in path[-depth:]) + name) not in used:
                    return candidate
        return "".join(p.title().replace("_", "") for p in path) + name

    @classmethod
    def _build_all_exports_code(
        cls,
        resolved: dict[str, list[tuple[str, tuple[str, ...], str]]],
    ) -> Imports:
        """Build import statements from resolved exports."""
        export_imports = Imports()
        for export_name, items in resolved.items():
            for orig, _, short in items:
                export_imports.append(
                    Import(from_=f".{short}", import_=orig, alias=export_name if export_name != orig else None)
                )
        return export_imports

    @classmethod
    def _collect_used_names_from_models(cls, models: list[DataModel]) -> set[str]:
        """Collect identifiers referenced by models before rendering."""
        names: set[str] = set()

        def add(name: str | None) -> None:
            if not name:
                return
            names.add(name.split(".")[0])

        def collect_data_type_names(data_type: DataType) -> None:
            add(data_type.alias or data_type.type)
            if data_type.reference:
                add(data_type.reference.short_name)

        for model in models:
            add(model.class_name)
            add(model.duplicate_class_name)
            for base in model.base_classes:
                add(base.type_hint)
            for import_ in model.imports:
                add(import_.alias or import_.import_.split(".")[-1])
            for field in model.fields:
                if field.extras.get("is_classvar"):
                    continue
                add(field.name)
                add(field.alias)
                field.data_type.walk(collect_data_type_names)
        return names

    def __generate_forwarder_content(  # noqa: PLR6301
        self,
        original_module: tuple[str, ...],
        internal_module: tuple[str, ...],
        class_mappings: list[tuple[str, str]],
        *,
        is_init: bool = False,
    ) -> str:
        """Generate forwarder module content that re-exports classes from _internal.

        Args:
            original_module: The original module tuple (e.g., ("issuing",) or ())
            internal_module: The _internal module tuple (e.g., ("_internal",))
            class_mappings: List of (original_name, new_name) tuples, sorted by original_name
            is_init: True if this is a package __init__.py, False for regular .py files

        Returns:
            The forwarder module content as a string
        """
        original_str = ".".join(original_module)
        internal_str = ".".join(internal_module)
        from_dots, module_name = relative(original_str, internal_str, reference_is_module=True, current_is_init=is_init)
        relative_import = f"{from_dots}{module_name}"

        imports = Imports()
        for original_name, new_name in class_mappings:
            if original_name == new_name:
                imports.append(Import(from_=relative_import, import_=new_name))
            else:
                imports.append(Import(from_=relative_import, import_=new_name, alias=original_name))

        return f"{imports.dump()}\n\n{imports.dump_all()}\n"

    def __compute_internal_module_path(  # noqa: PLR6301
        self,
        scc_modules: set[tuple[str, ...]],
        existing_modules: set[tuple[str, ...]],
        *,
        base_name: str = "_internal",
    ) -> tuple[str, ...]:
        """Compute the internal module path for an SCC."""
        directories = [get_module_directory(m) for m in sorted(scc_modules)]

        if not directories or any(not d for d in directories):
            prefix: tuple[str, ...] = ()
        else:
            path_strings = ["/".join(d) for d in directories]
            common = os.path.commonpath(path_strings)
            prefix = tuple(common.split("/")) if common else ()

        base_module = (base_name,) if not prefix else (*prefix, base_name)

        if base_module in existing_modules:
            counter = 1
            while True:
                candidate = (*prefix, f"{base_name}_{counter}") if prefix else (f"{base_name}_{counter}",)
                if candidate not in existing_modules:
                    return candidate
                counter += 1

        return base_module

    def __collect_scc_models(  # noqa: PLR6301
        self,
        scc: set[tuple[str, ...]],
        result_modules: dict[tuple[str, ...], list[DataModel]],
    ) -> tuple[list[DataModel], dict[int, tuple[str, ...]]]:
        """Collect all models from SCC modules.

        Returns:
            - List of all models in the SCC
            - Mapping from model id to its original module
        """
        all_models: list[DataModel] = []
        model_to_module: dict[int, tuple[str, ...]] = {}
        for scc_module in sorted(scc):
            for model in result_modules[scc_module]:
                all_models.append(model)
                model_to_module[id(model)] = scc_module
        return all_models, model_to_module

    def __rename_and_relocate_scc_models(  # noqa: PLR6301
        self,
        all_scc_models: list[DataModel],
        model_to_original_module: dict[int, tuple[str, ...]],
        internal_module: tuple[str, ...],
        internal_path: Path,
    ) -> tuple[defaultdict[tuple[str, ...], list[tuple[str, str]]], dict[str, str]]:
        """Rename duplicate classes and relocate models to internal module.

        Returns:
            Tuple of:
            - Mapping from original module to list of (original_name, new_name) tuples.
            - Mapping from old reference paths to new reference paths.
        """
        class_name_counts = Counter(model.class_name for model in all_scc_models)
        class_name_seen: dict[str, int] = {}
        internal_module_str = ".".join(internal_module)
        module_class_mappings: defaultdict[tuple[str, ...], list[tuple[str, str]]] = defaultdict(list)
        path_mapping: dict[str, str] = {}

        for model in all_scc_models:
            original_class_name = model.class_name
            original_module = model_to_original_module[id(model)]
            old_path = model.path  # Save old path before updating

            if class_name_counts[original_class_name] > 1:
                seen_count = class_name_seen.get(original_class_name, 0)
                new_class_name = f"{original_class_name}_{seen_count}" if seen_count > 0 else original_class_name
                class_name_seen[original_class_name] = seen_count + 1
            else:
                new_class_name = original_class_name

            model.reference.name = new_class_name
            new_path = f"{internal_module_str}.{new_class_name}"
            model.set_reference_path(new_path)
            model.file_path = internal_path

            module_class_mappings[original_module].append((original_class_name, new_class_name))
            path_mapping[old_path] = new_path

        return module_class_mappings, path_mapping

    def __build_module_dependency_graph(  # noqa: PLR6301
        self,
        module_models_list: list[tuple[tuple[str, ...], list[DataModel]]],
    ) -> dict[tuple[str, ...], set[tuple[str, ...]]]:
        """Build a directed graph of module dependencies."""
        path_to_module: dict[str, tuple[str, ...]] = {}
        for module, models in module_models_list:
            for model in models:
                path_to_module[model.path] = module

        graph: dict[tuple[str, ...], set[tuple[str, ...]]] = {}

        def add_cross_module_edge(ref_path: str, source_module: tuple[str, ...]) -> None:
            """Add edge if ref_path points to a different module."""
            if ref_path in path_to_module:
                target_module = path_to_module[ref_path]
                if target_module != source_module:
                    graph[source_module].add(target_module)

        for module, models in module_models_list:
            graph[module] = set()

            for model in models:
                for data_type in model.all_data_types:
                    if data_type.reference and data_type.reference.source:
                        add_cross_module_edge(data_type.reference.path, module)

                for base_class in model.base_classes:
                    if base_class.reference and base_class.reference.source:
                        add_cross_module_edge(base_class.reference.path, module)

        return graph

    def __resolve_circular_imports(  # noqa: PLR0914
        self,
        module_models_list: list[tuple[tuple[str, ...], list[DataModel]]],
    ) -> tuple[
        list[tuple[tuple[str, ...], list[DataModel]]],
        set[tuple[str, ...]],
        dict[tuple[str, ...], tuple[tuple[str, ...], list[tuple[str, str]]]],
        dict[str, str],
    ]:
        """Resolve circular imports by merging all SCCs into _internal.py modules.

        Uses Tarjan's algorithm to find strongly connected components (SCCs) in the
        module dependency graph. All modules in each SCC are merged into a single
        _internal.py module to break import cycles. Original modules become thin
        forwarders that re-export their classes from _internal.

        Returns:
            - Updated module_models_list with models moved to _internal modules
            - Set of _internal modules created
            - Forwarder map: original_module -> (internal_module, [(original_name, new_name)])
            - Path mapping: old_reference_path -> new_reference_path
        """
        graph = self.__build_module_dependency_graph(module_models_list)

        circular_sccs = find_circular_sccs(graph)

        forwarder_map: dict[tuple[str, ...], tuple[tuple[str, ...], list[tuple[str, str]]]] = {}
        all_path_mappings: dict[str, str] = {}

        if not circular_sccs:
            return module_models_list, set(), forwarder_map, all_path_mappings

        # All circular SCCs are problematic and should be merged into _internal.py
        # to break the import cycles.
        problematic_sccs = circular_sccs

        existing_modules = {module for module, _ in module_models_list}
        internal_modules_created: set[tuple[str, ...]] = set()

        result_modules: dict[tuple[str, ...], list[DataModel]] = {
            module: list(models) for module, models in module_models_list
        }

        for scc in problematic_sccs:
            internal_module = self.__compute_internal_module_path(scc, existing_modules | internal_modules_created)
            internal_modules_created.add(internal_module)
            internal_path = Path("/".join(internal_module))

            all_scc_models, model_to_original_module = self.__collect_scc_models(scc, result_modules)
            module_class_mappings, path_mapping = self.__rename_and_relocate_scc_models(
                all_scc_models, model_to_original_module, internal_module, internal_path
            )
            all_path_mappings.update(path_mapping)

            for scc_module in scc:
                if scc_module in result_modules:  # pragma: no branch
                    result_modules[scc_module] = []
                if scc_module in module_class_mappings:  # pragma: no branch
                    sorted_mappings = sorted(module_class_mappings[scc_module], key=operator.itemgetter(0))
                    forwarder_map[scc_module] = (internal_module, sorted_mappings)
            result_modules[internal_module] = all_scc_models

        new_module_models: list[tuple[tuple[str, ...], list[DataModel]]] = [
            (internal_module, result_modules[internal_module])
            for internal_module in sorted(internal_modules_created)
            if internal_module in result_modules  # pragma: no branch
        ]

        for module, _ in module_models_list:
            if module not in internal_modules_created:  # pragma: no branch
                new_module_models.append((module, result_modules.get(module, [])))

        return new_module_models, internal_modules_created, forwarder_map, all_path_mappings

    def __get_resolve_reference_action_parts(
        self,
        models: list[DataModel],
        require_update_action_models: list[str],
        *,
        use_deferred_annotations: bool,
    ) -> list[str]:
        """Return the trailing rebuild/update calls for the given module's models."""
        if self.dump_resolve_reference_action is None:
            return []

        require_update_action_model_paths = set(require_update_action_models)
        required_paths_in_module = {m.path for m in models if m.path in require_update_action_model_paths}

        if (
            use_deferred_annotations
            and required_paths_in_module
            and self.dump_resolve_reference_action is pydantic_model_v2.dump_resolve_reference_action
        ):
            module_positions = {m.reference.short_name: i for i, m in enumerate(models) if m.reference}
            module_model_names = set(module_positions)

            forward_needed: set[str] = set()
            for model in models:
                if model.path not in required_paths_in_module or not model.reference:
                    continue
                name = model.reference.short_name
                pos = module_positions[name]
                refs = {
                    t.reference.short_name
                    for f in model.fields
                    for t in f.data_type.all_data_types
                    if t.reference and t.reference.short_name in module_model_names
                }
                if name in refs or any(module_positions.get(r, -1) > pos for r in refs):
                    forward_needed.add(model.path)

            # Propagate requirement through inheritance.
            changed = True
            required_filtered = set(forward_needed)
            while changed:
                changed = False
                for model in models:
                    if not model.reference or model.path in required_filtered:
                        continue
                    base_paths = {b.reference.path for b in model.base_classes if b.reference}
                    if base_paths & required_filtered:
                        required_filtered.add(model.path)
                        changed = True

            required_paths_in_module = required_filtered

        return [
            "\n",
            self.dump_resolve_reference_action(
                m.reference.short_name for m in models if m.reference and m.path in required_paths_in_module
            ),
        ]

    def _prepare_parse_config(  # noqa: PLR0913, PLR0917
        self,
        with_import: bool | None,  # noqa: FBT001
        format_: bool | None,  # noqa: FBT001
        settings_path: Path | None,
        disable_future_imports: bool,  # noqa: FBT001
        all_exports_scope: AllExportsScope | None,
        all_exports_collision_strategy: AllExportsCollisionStrategy | None,
        module_split_mode: ModuleSplitMode | None,
    ) -> ParseConfig:
        """Prepare configuration for the parse operation."""
        use_deferred_annotations = bool(
            self.target_python_version.has_native_deferred_annotations or (with_import and not disable_future_imports)
        )

        if (
            with_import
            and not disable_future_imports
            and not self.target_python_version.has_native_deferred_annotations
        ):
            self.imports.append(IMPORT_ANNOTATIONS)

        code_formatter: CodeFormatter | None = None
        if format_:
            code_formatter = CodeFormatter(
                self.target_python_version,
                settings_path,
                self.wrap_string_literal,
                skip_string_normalization=not self.use_double_quotes,
                known_third_party=self.known_third_party,
                custom_formatters=self.custom_formatter,
                custom_formatters_kwargs=self.custom_formatters_kwargs,
                encoding=self.encoding,
                formatters=self.formatters,
                defer_formatting=self.defer_formatting,
            )

        return ParseConfig(
            with_import=bool(with_import),
            use_deferred_annotations=use_deferred_annotations,
            code_formatter=code_formatter,
            module_split_mode=module_split_mode,
            all_exports_scope=all_exports_scope,
            all_exports_collision_strategy=all_exports_collision_strategy,
        )

    def _build_module_structure(
        self,
        sorted_data_models: SortedDataModels,
        require_update_action_models: list[str],
        module_split_mode: ModuleSplitMode | None,
    ) -> tuple[
        ModuleModels,
        set[ModulePath],
        ForwarderMap,
        dict[str, str],
        dict[DataModel, tuple[ModulePath, list[DataModel]]],
        dict[str, str],
    ]:
        """Build module structure from sorted models."""

        def module_key(data_model: DataModel) -> ModulePath:
            if module_split_mode == ModuleSplitMode.Single:
                file_name = camel_to_snake(data_model.class_name)
                return (*data_model.module_path, file_name)
            return tuple(data_model.module_path)

        def sort_key(data_model: DataModel) -> tuple[int, ModulePath]:
            key = module_key(data_model)
            return (len(key), key)

        grouped_models = groupby(
            sorted(sorted_data_models.values(), key=sort_key, reverse=True),
            key=module_key,
        )

        module_models: ModuleModels = []
        model_to_module_models: dict[DataModel, tuple[ModulePath, list[DataModel]]] = {}
        model_path_to_module_name: dict[str, str] = {}

        previous_module: ModulePath = ()
        for module, models in ((k, [*v]) for k, v in grouped_models):
            for model in models:
                model_to_module_models[model] = module, models
                if module_split_mode == ModuleSplitMode.Single:
                    model_path_to_module_name[model.path] = ".".join(module)
            self.__delete_duplicate_models(models)
            self.__replace_duplicate_name_in_module(models)
            if len(previous_module) - len(module) > 1:
                module_models.extend(
                    (previous_module[:parts], []) for parts in range(len(previous_module) - 1, len(module), -1)
                )
            module_models.append((module, models))
            previous_module = module

        shared_module_entry = self.__reuse_model_tree_scope(module_models, require_update_action_models)
        if shared_module_entry:
            module_models.insert(0, shared_module_entry)

        module_models, internal_modules, forwarder_map, path_mapping = self.__resolve_circular_imports(module_models)

        if path_mapping:
            require_update_action_models[:] = [path_mapping.get(path, path) for path in require_update_action_models]

        return (
            module_models,
            internal_modules,
            forwarder_map,
            path_mapping,
            model_to_module_models,
            model_path_to_module_name,
        )

    def _process_single_module(  # noqa: PLR0913, PLR0917
        self,
        module_: ModulePath,
        models: list[DataModel],
        results: dict[ModulePath, Result],
        config: ParseConfig,
        internal_modules: set[ModulePath],
        model_path_to_module_name: dict[str, str],
        require_update_action_models: list[str],
        unused_models: list[DataModel],
    ) -> ModuleContext:
        """Process a single module and return its context."""
        imports = Imports(self.use_exact_imports)
        is_init = False

        if module_:
            if len(module_) == 1:
                parent: ModulePath = ("__init__.py",)
                if parent not in results:
                    results[parent] = Result(body="")
            else:
                for i in range(1, len(module_)):
                    parent = (*module_[:i], "__init__.py")
                    if parent not in results:
                        results[parent] = Result(body="")
            if (*module_, "__init__.py") in results:
                module = (*module_, "__init__.py")
                is_init = True
            else:
                module = tuple(part.replace("-", "_") for part in (*module_[:-1], f"{module_[-1]}.py"))
        else:
            module = ("__init__.py",)

        all_module_fields = {field.name for model in models for field in model.fields if field.name is not None}
        scoped_model_resolver = ModelResolver(exclude_names=all_module_fields)

        self.__alias_shadowed_imports(models, all_module_fields)
        self.__override_required_field(models)
        self.__replace_unique_list_to_set(models)
        self.__change_from_import(
            models,
            imports,
            scoped_model_resolver,
            init=is_init,
            internal_modules=internal_modules,
            model_path_to_module_name=model_path_to_module_name,
        )
        self.__extract_inherited_enum(models)
        self.__set_reference_default_value_to_field(models)
        self.__reuse_model(models, require_update_action_models)
        self.__collapse_root_models(models, unused_models, imports, scoped_model_resolver)
        self.__set_default_enum_member(models)
        self.__wrap_root_model_default_values(models)
        self.__sort_models(models, imports, use_deferred_annotations=config.use_deferred_annotations)
        self.__change_field_name(models)
        self.__apply_discriminator_type(models, imports)
        self.__set_one_literal_on_default(models)
        self.__fix_dataclass_field_ordering(models)
        models = self.__remove_overridden_models(models)
        self.__apply_type_overrides(models)
        self.__update_type_aliases(models)

        return ModuleContext(module, module_, models, is_init, imports, scoped_model_resolver)

    def _finalize_modules(
        self,
        contexts: list[ModuleContext],
        unused_models: list[DataModel],
        model_to_module_models: dict[DataModel, tuple[ModulePath, list[DataModel]]],
        module_to_import: dict[ModulePath, Imports],
    ) -> None:
        """Finalize module processing: apply generic base class and remove unused imports."""
        self.__apply_generic_base_class(contexts)

        for ctx in contexts:
            for model in ctx.models:
                ctx.imports.append(model.imports)

        for unused_model in unused_models:
            module, models = model_to_module_models[unused_model]
            if unused_model in models:  # pragma: no branch
                imports = module_to_import[module]
                imports.remove(unused_model.imports)
                models.remove(unused_model)

        for ctx in contexts:
            used_names = self._collect_used_names_from_models(ctx.models)
            ctx.imports.remove_unused(used_names)

        for ctx in contexts:
            self.__change_imported_model_name(ctx.models, ctx.imports, ctx.scoped_model_resolver)

    def _generate_module_output(  # noqa: PLR0913, PLR0917
        self,
        ctx: ModuleContext,
        config: ParseConfig,
        contexts: list[ModuleContext],
        forwarder_map: ForwarderMap,
        require_update_action_models: list[str],
        future_imports_str: str,
    ) -> Result | None:
        """Generate output for a single module."""
        result: list[str] = []
        export_imports: Imports | None = None

        if config.all_exports_scope is not None and ctx.module[-1] == "__init__.py":
            child_exports = self._collect_exports_for_init(ctx.module, contexts, config.all_exports_scope)
            if child_exports:
                local_model_names = {
                    m.reference.short_name
                    for m in ctx.models
                    if m.reference and not m.reference.short_name.startswith("_")  # pragma: no branch
                }
                resolved_exports = self._resolve_export_collisions(
                    child_exports, config.all_exports_collision_strategy, local_model_names
                )
                export_imports = self._build_all_exports_code(resolved_exports)

        if ctx.models:
            if config.with_import:
                import_parts = [s for s in [future_imports_str, str(self.imports), str(ctx.imports)] if s]
                result += [*import_parts, "\n"]

            if export_imports:
                result += [str(export_imports), ""]
                for m in ctx.models:
                    if m.reference and not m.reference.short_name.startswith("_"):  # pragma: no branch
                        export_imports.add_export(m.reference.short_name)
                result += [export_imports.dump_all(multiline=True) + "\n"]

            code = dump_templates(ctx.models)
            result += [code]

            result += self.__get_resolve_reference_action_parts(
                ctx.models,
                require_update_action_models,
                use_deferred_annotations=config.use_deferred_annotations,
            )

        if not result and ctx.module_key in forwarder_map:
            internal_module, class_mappings = forwarder_map[ctx.module_key]
            forwarder_content = self.__generate_forwarder_content(
                ctx.module_key, internal_module, class_mappings, is_init=ctx.is_init
            )
            result = [forwarder_content]

        if not result and not ctx.is_init:
            return None

        body = "\n".join(result)
        if config.code_formatter:
            try:
                body = config.code_formatter.format_code(body)
            except Exception as exc:  # noqa: BLE001
                warn(
                    f"Failed to format code: {exc!r}. Emitting unformatted output.",
                    stacklevel=1,
                )

        return Result(
            body=body,
            future_imports=future_imports_str,
            source=ctx.models[0].file_path if ctx.models else None,
        )

    def _generate_empty_init_exports(
        self,
        results: dict[ModulePath, Result],
        contexts: list[ModuleContext],
        config: ParseConfig,
        future_imports_str: str,
    ) -> None:
        """Generate exports for empty __init__.py files."""
        if config.all_exports_scope is None:  # pragma: no cover
            return
        processed_init_modules = {ctx.module for ctx in contexts if ctx.module[-1] == "__init__.py"}
        for init_module, init_result in list(results.items()):
            if init_module[-1] != "__init__.py" or init_module in processed_init_modules or init_result.body:
                continue
            child_exports = self._collect_exports_for_init(init_module, contexts, config.all_exports_scope)
            if child_exports:
                resolved = self._resolve_export_collisions(child_exports, config.all_exports_collision_strategy, set())
                export_imports = self._build_all_exports_code(resolved)
                import_parts = [s for s in [future_imports_str, str(self.imports)] if s] if config.with_import else []
                parts = import_parts + (["\n"] if import_parts else [])
                parts += [str(export_imports), "", export_imports.dump_all(multiline=True)]
                body = "\n".join(parts)
                if config.code_formatter:
                    try:
                        body = config.code_formatter.format_code(body)
                    except Exception as exc:  # noqa: BLE001
                        warn(
                            f"Failed to format code: {exc!r}. Emitting unformatted output.",
                            stacklevel=1,
                        )
                results[init_module] = Result(
                    body=body,
                    future_imports=future_imports_str,
                )

    def parse(  # noqa: PLR0913, PLR0914, PLR0917
        self,
        with_import: bool | None = True,  # noqa: FBT001, FBT002
        format_: bool | None = True,  # noqa: FBT001, FBT002
        settings_path: Path | None = None,
        disable_future_imports: bool = False,  # noqa: FBT001, FBT002
        all_exports_scope: AllExportsScope | None = None,
        all_exports_collision_strategy: AllExportsCollisionStrategy | None = None,
        module_split_mode: ModuleSplitMode | None = None,
    ) -> str | dict[tuple[str, ...], Result]:
        """Parse schema and generate code, returning single file or module dict."""
        self.parse_raw()

        config = self._prepare_parse_config(
            with_import,
            format_,
            settings_path,
            disable_future_imports,
            all_exports_scope,
            all_exports_collision_strategy,
            module_split_mode,
        )

        _, sorted_data_models, require_update_action_models = sort_data_models(self.results)

        (
            module_models,
            internal_modules,
            forwarder_map,
            _path_mapping,
            model_to_module_models,
            model_path_to_module_name,
        ) = self._build_module_structure(sorted_data_models, require_update_action_models, module_split_mode)

        results: dict[ModulePath, Result] = {}
        unused_models: list[DataModel] = []
        module_to_import: dict[ModulePath, Imports] = {}
        contexts: list[ModuleContext] = []

        for module_, models in module_models:
            ctx = self._process_single_module(
                module_,
                models,
                results,
                config,
                internal_modules,
                model_path_to_module_name,
                require_update_action_models,
                unused_models,
            )
            module_to_import[module_] = ctx.imports
            contexts.append(ctx)

        self._finalize_modules(contexts, unused_models, model_to_module_models, module_to_import)

        future_imports = self.imports.extract_future()
        future_imports_str = str(future_imports)

        for ctx in contexts:
            result = self._generate_module_output(
                ctx, config, contexts, forwarder_map, require_update_action_models, future_imports_str
            )
            if result is not None:
                results[ctx.module] = result

        if config.all_exports_scope is not None:
            self._generate_empty_init_exports(results, contexts, config, future_imports_str)

        if [*results] == [("__init__.py",)]:
            single_result = results["__init__.py",]
            return single_result.body

        results = {tuple(i.replace("-", "_") for i in k): v for k, v in results.items()}
        return (
            self.__postprocess_result_modules(results)
            if self.treat_dot_as_module
            else {
                tuple((part[: part.rfind(".")].replace(".", "_") + part[part.rfind(".") :]) for part in k): v
                for k, v in results.items()
            }
        )
