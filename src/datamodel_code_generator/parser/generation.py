"""In-memory facts and indexes for parser generation state.

Parser implementations keep creating and naming models through the existing
ModelResolver flow. The store records those objects and owns all parser-side
mutations that affect dependency facts.

Contributor guide:

* Keep ``ModelResolver`` as the only authority for generated names. Register
  models only after the existing parser flow has created and named them.
* Use ``GenerationStore.register_model(model)`` instead of appending to
  ``Parser.results`` or ``GenerationStore.models`` directly.
* Use the store mutation helpers for parser-side changes that affect
  references, fields, base classes, model paths, or model names. Do not assign
  ``data_type.reference``, ``model.fields``, ``model.base_classes``, or
  ``model.reference.name`` directly in parser code.
* Read dependency facts through ``GenerationIndex``. Parser post-processing
  should not treat ``Reference.children`` as the source of truth.
* Preserve output compatibility first. Store/index queries must reproduce the
  existing parse order, naming order, canonical model selection, and
  tie-break behavior before they replace a direct object traversal.

The pre-commit hook backed by ``scripts/check_generation_store_usage.py``
guards the parser package against common direct mutations. When adding a new
store mutation API, add it to ``GENERATION_STORE_MUTATION_METHODS`` so the
checker and its tests stay aligned with the public parser-facing surface.
"""

# ruff: noqa: D105, FURB189

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cache
from typing import TYPE_CHECKING, Any, Literal, SupportsIndex, TypeAlias, TypeVar, overload

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Iterator
    from pathlib import Path


BaseClassDataType: TypeAlias = Any
DataModel: TypeAlias = Any
DataModelFieldBase: TypeAlias = Any
DataType: TypeAlias = Any
ModelId: TypeAlias = int
DataTypeId: TypeAlias = int
DataTypeRole = Literal["field", "base", "nested", "dict_key"]
_OrderedSetItem = TypeVar("_OrderedSetItem")
OrderedSet: TypeAlias = dict[_OrderedSetItem, None]
Reference: TypeAlias = Any
_PYDANTIC_V2_MODEL_MODULE_PREFIX = "datamodel_code_generator.model.pydantic_v2."

GENERATION_STORE_MUTATION_METHODS: frozenset[str] = frozenset({
    "append_field",
    "collapse_root_data_type",
    "defer_refresh",
    "detach_data_type_ref",
    "detach_model_data_type_refs",
    "insert_field",
    "move_model",
    "redirect_model_reference_users",
    "redirect_reference_users",
    "register_model",
    "remove_field",
    "rename_model",
    "replace_data_type_ref",
    "replace_field_type",
    "replace_nested_data_type",
    "reset_base_classes",
    "set_base_classes",
    "set_fields",
    "set_nested_data_types",
    "update_model_reference",
})


def set_model_base_classes(
    model: DataModel,
    base_classes: Iterable[BaseClassDataType],
    generation_store: GenerationStore | None = None,
) -> None:
    """Replace model base classes, refreshing ``generation_store`` when supplied."""
    if generation_store is None:
        model.base_classes = list(base_classes)
    else:
        generation_store.set_base_classes(model, base_classes)


def _outermost_parent(value: object) -> object:
    current = value
    while (parent := getattr(current, "parent", None)) is not None:
        current = parent
    return current


@cache
def _pydantic_v2_dict_key_reference_classes_enabled() -> bool:
    from datamodel_code_generator.model.pydantic_v2.version import (  # noqa: PLC0415
        PYDANTIC_V2_ROOT_MODEL_DICT_KEY_FORWARD_REF_NEEDS_SORTING,
    )

    return PYDANTIC_V2_ROOT_MODEL_DICT_KEY_FORWARD_REF_NEEDS_SORTING


def _include_dict_key_reference_classes(model: DataModel) -> bool:
    return (
        model.__class__.__module__.startswith(_PYDANTIC_V2_MODEL_MODULE_PREFIX)
        and _pydantic_v2_dict_key_reference_classes_enabled()
    )


@dataclass(frozen=True, slots=True)
class ModelFact:
    """A parsed model and the stable facts derived from its reference."""

    id: ModelId
    parse_order: int
    model: DataModel
    reference: Reference
    path: str
    name: str
    class_name: str
    file_path: Path | None


@dataclass(frozen=True, slots=True)
class DataTypeFact:
    """A data type occurrence owned by a parsed model."""

    id: DataTypeId
    data_type: DataType
    owner_model: ModelId
    owner_field_index: int | None
    role: DataTypeRole
    reference: Reference | None


@dataclass(slots=True)
class GenerationFacts:
    """A complete snapshot of derived generation facts."""

    model_facts: dict[ModelId, ModelFact] = field(default_factory=dict)
    data_type_facts: dict[DataTypeId, DataTypeFact] = field(default_factory=dict)
    data_type_fact_by_object: dict[int, DataTypeFact] = field(default_factory=dict)
    model_by_path: dict[str, ModelId] = field(default_factory=dict)
    model_by_ref_id: dict[int, ModelId] = field(default_factory=dict)
    data_types_by_model: dict[ModelId, tuple[DataTypeId, ...]] = field(default_factory=dict)
    reverse_edges: defaultdict[int, OrderedSet[DataTypeId]] = field(default_factory=lambda: defaultdict(dict))


@dataclass(frozen=True, slots=True)
class GenerationBuildResult:
    """Facts and stable id state produced by an index rebuild."""

    facts: GenerationFacts
    model_ids_by_object: dict[int, ModelId]
    next_model_id: int


class _GenerationModelList(list["DataModel"]):
    """List-compatible model collection that invalidates generation facts."""

    def __init__(self, invalidate: Callable[[], None]) -> None:
        """Create a model list with an invalidation callback."""
        super().__init__()
        self._invalidate = invalidate

    def append(self, item: Any) -> None:  # ty: ignore[invalid-method-override]
        """Append a model and invalidate derived facts."""
        super().append(item)
        self._invalidate()

    def extend(self, items: Iterable[Any]) -> None:  # ty: ignore[invalid-method-override]
        """Extend the model list and invalidate derived facts."""
        super().extend(items)
        self._invalidate()

    def insert(self, index: SupportsIndex, item: Any) -> None:  # ty: ignore[invalid-method-override]
        """Insert a model and invalidate derived facts."""
        super().insert(index, item)
        self._invalidate()

    @overload
    def __setitem__(self, index: SupportsIndex, item: Any) -> None:  # pragma: no cover
        pass

    @overload
    def __setitem__(self, index: slice, item: Iterable[Any]) -> None:  # pragma: no cover
        pass

    def __setitem__(
        self,
        index: SupportsIndex | slice,
        item: Any | Iterable[Any],
    ) -> None:  # ty: ignore[invalid-method-override]
        super().__setitem__(index, item)  # type: ignore[arg-type]
        self._invalidate()

    @overload
    def __delitem__(self, index: SupportsIndex) -> None:  # pragma: no cover
        pass

    @overload
    def __delitem__(self, index: slice) -> None:  # pragma: no cover
        pass

    def __delitem__(self, index: SupportsIndex | slice) -> None:  # ty: ignore[invalid-method-override]
        super().__delitem__(index)
        self._invalidate()

    def clear(self) -> None:
        """Remove all models and invalidate derived facts."""
        super().clear()
        self._invalidate()

    def pop(self, index: SupportsIndex = -1) -> Any:
        """Remove and return a model while invalidating derived facts."""
        item = super().pop(index)
        self._invalidate()
        return item

    def remove(self, item: Any) -> None:  # ty: ignore[invalid-method-override]
        """Remove a model and invalidate derived facts."""
        super().remove(item)
        self._invalidate()


class GenerationIndexBuilder:
    """Build a full generation fact snapshot from live parser objects."""

    def build(
        self,
        models: Iterable[DataModel],
        *,
        previous_model_ids_by_object: dict[int, ModelId],
        next_model_id: int,
    ) -> GenerationBuildResult:
        """Build facts while preserving stable model ids for surviving objects."""
        self._models = list(models)
        self._facts = GenerationFacts()
        self._model_ids_by_object = {
            id(model): previous_model_ids_by_object[id(model)]
            for model in self._models
            if id(model) in previous_model_ids_by_object
        }
        self._next_model_id = next_model_id
        self._next_data_type_id = 0

        self._record_models()
        self._record_data_types()

        return GenerationBuildResult(
            facts=self._facts,
            model_ids_by_object=self._model_ids_by_object,
            next_model_id=self._next_model_id,
        )

    def _record_models(self) -> None:
        for parse_order, model in enumerate(self._models):
            model_id = self._model_ids_by_object.get(id(model))
            if model_id is None:
                model_id = self._next_model_id
                self._next_model_id += 1
                self._model_ids_by_object[id(model)] = model_id

            fact = ModelFact(
                id=model_id,
                parse_order=parse_order,
                model=model,
                reference=model.reference,
                path=model.path,
                name=model.reference.name,
                class_name=model.class_name,
                file_path=model.file_path,
            )
            self._facts.model_facts[model_id] = fact
            self._facts.model_by_path[model.path] = model_id
            self._facts.model_by_ref_id[id(model.reference)] = model_id

    def _record_data_types(self) -> None:
        for model_id, model_fact in self._facts.model_facts.items():
            data_type_ids: list[DataTypeId] = []

            for field_index, field_ in enumerate(model_fact.model.fields):
                self._record_data_type_tree(
                    field_.data_type,
                    owner_model=model_id,
                    owner_field_index=field_index,
                    role="field",
                    data_type_ids=data_type_ids,
                )

            for base_class in model_fact.model.base_classes:
                self._record_data_type_tree(
                    base_class,
                    owner_model=model_id,
                    owner_field_index=None,
                    role="base",
                    data_type_ids=data_type_ids,
                )

            self._facts.data_types_by_model[model_id] = tuple(data_type_ids)

    def _record_data_type_tree(
        self,
        data_type: DataType,
        *,
        owner_model: ModelId,
        owner_field_index: int | None,
        role: DataTypeRole,
        data_type_ids: list[DataTypeId],
    ) -> None:
        data_type_id = self._next_data_type_id
        self._next_data_type_id += 1
        fact = DataTypeFact(
            id=data_type_id,
            data_type=data_type,
            owner_model=owner_model,
            owner_field_index=owner_field_index,
            role=role,
            reference=data_type.reference,
        )
        self._facts.data_type_facts[data_type_id] = fact
        self._facts.data_type_fact_by_object[id(data_type)] = fact
        data_type_ids.append(data_type_id)

        if data_type.reference:
            self._facts.reverse_edges[id(data_type.reference)][data_type_id] = None

        nested_role: DataTypeRole = "dict_key" if role == "dict_key" else "nested"
        for nested_data_type in data_type.data_types:
            self._record_data_type_tree(
                nested_data_type,
                owner_model=owner_model,
                owner_field_index=owner_field_index,
                role=nested_role,
                data_type_ids=data_type_ids,
            )

        if data_type.dict_key:
            self._record_data_type_tree(
                data_type.dict_key,
                owner_model=owner_model,
                owner_field_index=owner_field_index,
                role="dict_key",
                data_type_ids=data_type_ids,
            )


class GenerationIndex:
    """Query layer over the current generation facts."""

    def __init__(self, store: GenerationStore) -> None:
        """Create an index over ``store`` facts."""
        self._store = store
        self._reference_classes_cache: dict[ModelId, frozenset[str]] = {}
        self._reference_classes_cache_version = -1

    def _facts(self) -> GenerationFacts:
        return self._store.current_facts()

    def _reset_reference_classes_cache_if_needed(self) -> None:
        if self._reference_classes_cache_version == self._store.facts_version:
            return
        self._reference_classes_cache.clear()
        self._reference_classes_cache_version = self._store.facts_version

    def model_fact(self, model: DataModel) -> ModelFact | None:
        """Return the current fact for ``model`` if it is tracked."""
        facts = self._facts()
        model_id = self._store.model_id(model)
        if model_id is None:
            return None
        return facts.model_facts.get(model_id)

    def model_id_for_reference(self, reference: Reference) -> ModelId | None:
        """Return the tracked model id for ``reference`` if it points to a model."""
        return self._facts().model_by_ref_id.get(id(reference))

    def model_for_reference(self, reference: Reference) -> DataModel | None:
        """Return the tracked model for ``reference`` if it points to a model."""
        facts = self._facts()
        model_id = facts.model_by_ref_id.get(id(reference))
        if model_id is None:
            return None
        return facts.model_facts[model_id].model

    def data_type_facts_for_reference(self, reference: Reference) -> tuple[DataTypeFact, ...]:
        """Return data type occurrences that currently point at ``reference``."""
        facts = self._facts()
        data_type_ids = facts.reverse_edges.get(id(reference))
        if not data_type_ids:
            return ()
        return tuple(facts.data_type_facts[data_type_id] for data_type_id in data_type_ids)

    def has_data_type_references(self, reference: Reference) -> bool:
        """Return whether any tracked data type currently points at ``reference``."""
        return bool(self._facts().reverse_edges.get(id(reference)))

    def has_data_type_references_other_than(self, reference: Reference, excluded_data_type: DataType) -> bool:
        """Return whether tracked data types other than ``excluded_data_type`` point at ``reference``."""
        facts = self._facts()
        data_type_ids = facts.reverse_edges.get(id(reference))
        if not data_type_ids:
            return False
        excluded_data_type_id = id(excluded_data_type)
        return any(
            facts.data_type_facts[data_type_id].data_type is not excluded_data_type
            and id(facts.data_type_facts[data_type_id].data_type) != excluded_data_type_id
            for data_type_id in data_type_ids
        )

    def reference_classes_for_model(self, model: DataModel) -> frozenset[str]:
        """Return reference paths matching ``DataModel.reference_classes`` semantics."""
        facts = self._facts()
        model_id = self._store.model_id(model)
        if model_id is None:
            return frozenset(model.reference_classes)
        self._reset_reference_classes_cache_if_needed()
        if (reference_classes := self._reference_classes_cache.get(model_id)) is not None:
            return reference_classes
        include_dict_key_references = _include_dict_key_reference_classes(model)
        reference_classes = frozenset(
            reference.path
            for data_type_id in facts.data_types_by_model.get(model_id, ())
            if (reference := (fact := facts.data_type_facts[data_type_id]).reference) is not None
            if include_dict_key_references or fact.role != "dict_key"
        ) | frozenset(model.extra_template_data.get("additionalPropertiesReferenceClasses", ()))
        self._reference_classes_cache[model_id] = reference_classes
        return reference_classes

    def owner_model_for_data_type(self, data_type: DataType) -> DataModel | None:
        """Return the tracked model that owns ``data_type`` if known."""
        facts = self._facts()
        fact = facts.data_type_fact_by_object.get(id(data_type))
        if fact is None:
            return None
        return facts.model_facts[fact.owner_model].model

    def root_model_wrappers_for_reference(
        self,
        reference: Reference,
        root_model_type: type[DataModel],
    ) -> list[DataModel]:
        """Return root-model wrappers whose field graph points at ``reference``."""
        facts = self._facts()
        wrappers: list[DataModel] = []
        seen: set[int] = set()
        data_type_ids = facts.reverse_edges.get(id(reference))
        if not data_type_ids:
            return wrappers
        for data_type_id in data_type_ids:
            fact = facts.data_type_facts[data_type_id]
            owner = facts.model_facts[fact.owner_model].model
            if isinstance(owner, root_model_type) and id(owner) not in seen:
                seen.add(id(owner))
                wrappers.append(owner)
        return wrappers

    def root_collapse_reference_usage(
        self,
        reference: Reference,
        *,
        excluded_model: DataModel,
        root_model_type: type[DataModel],
    ) -> tuple[list[DataModel], list[DataTypeFact]]:
        """Return wrapper models and direct non-wrapper refs for root collapse checks."""
        facts = self._facts()
        wrappers: list[DataModel] = []
        direct_refs: list[DataTypeFact] = []
        wrapper_ids: set[int] = set()
        data_type_ids = facts.reverse_edges.get(id(reference))
        if not data_type_ids:
            return wrappers, direct_refs

        for data_type_id in data_type_ids:
            fact = facts.data_type_facts[data_type_id]
            owner = facts.model_facts[fact.owner_model].model
            if isinstance(owner, root_model_type):
                if id(owner) not in wrapper_ids:
                    wrapper_ids.add(id(owner))
                    wrappers.append(owner)
                continue
            if fact.role != "base" and owner is not excluded_model:
                direct_refs.append(fact)
        return wrappers, direct_refs

    def direct_non_root_refs_for_reference(
        self,
        reference: Reference,
        *,
        excluded_model: DataModel,
        root_model_type: type[DataModel],
    ) -> list[DataTypeFact]:
        """Return non-wrapper field references to ``reference`` outside ``excluded_model``."""
        facts = self._facts()
        direct_refs: list[DataTypeFact] = []
        data_type_ids = facts.reverse_edges.get(id(reference))
        if not data_type_ids:
            return direct_refs
        for data_type_id in data_type_ids:
            fact = facts.data_type_facts[data_type_id]
            if fact.role == "base":
                continue
            owner = facts.model_facts[fact.owner_model].model
            if owner is excluded_model or isinstance(owner, root_model_type):
                continue
            direct_refs.append(fact)
        return direct_refs


class GenerationStore:  # noqa: PLR0904
    """Parse-to-output generation facts for a Parser instance."""

    def __init__(self) -> None:
        """Initialize an empty generation store."""
        self.models: _GenerationModelList = _GenerationModelList(self._invalidate)
        self.index = GenerationIndex(self)
        self._facts = GenerationFacts()
        self._model_ids_by_object: dict[int, ModelId] = {}
        self._next_model_id = 0
        self._facts_version = 0
        self._dirty = True
        self._defer_refresh_depth = 0

    @classmethod
    def create_with_results(cls) -> tuple[GenerationStore, list[DataModel]]:
        """Create a store and the public ``Parser.results`` list view together."""
        store = cls()
        return store, store.models

    def _dispose(self, references: Iterable[Reference] = ()) -> None:
        """Drop all facts and model references so the parsed graph can be reclaimed.

        The store, its model list, and its facts hold strong references to every
        model and data type; clearing them removes the last anchors keeping the
        object graph alive once the parser is dropped. Models, fields, data
        types, and references also point at each other in cycles, so their back
        references are severed first to let ordinary reference counting reclaim
        the graph without waiting for a full garbage collection pass.
        """
        for model in self.models:
            for model_field in model.fields:
                for data_type in list(model_field.data_type.all_data_types):
                    data_type.parent = None
                    data_type.reference = None
                model_field.parent = None
            for base_class in model.base_classes:
                for data_type in list(base_class.all_data_types):
                    data_type.parent = None
                    data_type.reference = None
        for reference in references:
            reference.children.clear()
            reference.source = None
        self._facts = GenerationFacts()
        self._model_ids_by_object.clear()
        self.models.clear()
        self._dirty = True

    @property
    def facts(self) -> GenerationFacts:
        """Return the current facts snapshot."""
        return self.current_facts()

    @property
    def facts_version(self) -> int:
        """Return the current facts snapshot version."""
        return self._facts_version

    def current_facts(self) -> GenerationFacts:
        """Return current facts after rebuilding stale data."""
        self.refresh()
        return self._facts

    @property
    def model_facts(self) -> dict[ModelId, ModelFact]:
        """Compatibility access to model facts."""
        self.refresh()
        return self._facts.model_facts

    @property
    def data_type_facts(self) -> dict[DataTypeId, DataTypeFact]:
        """Compatibility access to data type facts."""
        self.refresh()
        return self._facts.data_type_facts

    @property
    def data_type_fact_by_object(self) -> dict[int, DataTypeFact]:
        """Compatibility access to data type facts by object id."""
        self.refresh()
        return self._facts.data_type_fact_by_object

    @property
    def model_by_path(self) -> dict[str, ModelId]:
        """Compatibility access to model ids by path."""
        self.refresh()
        return self._facts.model_by_path

    @property
    def model_by_ref_id(self) -> dict[int, ModelId]:
        """Compatibility access to model ids by reference object id."""
        self.refresh()
        return self._facts.model_by_ref_id

    @property
    def data_types_by_model(self) -> dict[ModelId, tuple[DataTypeId, ...]]:
        """Compatibility access to data type ids by owner model."""
        self.refresh()
        return self._facts.data_types_by_model

    @property
    def reverse_edges(self) -> defaultdict[int, OrderedSet[DataTypeId]]:
        """Compatibility access to reverse reference edges."""
        self.refresh()
        return self._facts.reverse_edges

    def register_model(self, model: DataModel) -> None:
        """Register a parsed model while preserving parser append order."""
        self.models.append(model)

    def model_id(self, model: DataModel) -> ModelId | None:
        """Return the stable store id for ``model`` if it is tracked."""
        return self._model_ids_by_object.get(id(model))

    def _invalidate(self) -> None:
        """Invalidate derived facts after a store-managed mutation."""
        self._dirty = True

    def refresh(self) -> None:
        """Rebuild facts from the live model list."""
        if self._defer_refresh_depth:
            return

        self.refresh_now()

    def refresh_now(self) -> None:
        """Rebuild facts immediately, even inside a deferred mutation block."""
        if not self._dirty:
            return

        result = GenerationIndexBuilder().build(
            self.models,
            previous_model_ids_by_object=self._model_ids_by_object,
            next_model_id=self._next_model_id,
        )
        self._facts = result.facts
        self._model_ids_by_object = result.model_ids_by_object
        self._next_model_id = result.next_model_id
        self._facts_version += 1
        self._dirty = False

    def replace_data_type_ref(self, data_type: DataType, new_reference: Reference | None) -> None:
        """Set ``data_type.reference`` while preserving reverse reference links."""
        self._replace_data_type_reference(data_type, new_reference)
        self._invalidate_after_mutation()

    def detach_data_type_ref(self, data_type: DataType) -> None:
        """Remove ``data_type`` from its reference and invalidate derived facts."""
        self.replace_data_type_ref(data_type, None)

    def update_model_reference(
        self,
        model: DataModel,
        *,
        class_name: str | None = None,
        reference_name: str | None = None,
        new_path: str | None = None,
        new_file_path: Path | None = None,
    ) -> None:
        """Update a model's generated name/path metadata and invalidate facts."""
        if class_name is not None:
            model.class_name = class_name
        if reference_name is not None:
            model.reference.name = reference_name
        if new_path is not None:
            model.set_reference_path(new_path)
        if new_file_path is not None:
            model.file_path = new_file_path
        self._invalidate_after_mutation()

    def rename_model(
        self,
        model: DataModel,
        *,
        class_name: str | None = None,
        reference_name: str | None = None,
    ) -> None:
        """Update a model's generated class or reference name."""
        self.update_model_reference(model, class_name=class_name, reference_name=reference_name)

    def move_model(self, model: DataModel, *, new_path: str, new_file_path: Path | None = None) -> None:
        """Update a model's reference path and optional output file path."""
        self.update_model_reference(model, new_path=new_path, new_file_path=new_file_path)

    def replace_field_type(self, field_: DataModelFieldBase, new_data_type: DataType) -> None:
        """Replace a field's data type and invalidate derived facts."""
        field_.replace_data_type(new_data_type)
        self._invalidate_after_mutation()

    def replace_nested_data_type(
        self,
        parent_data_type: DataType,
        old_data_type: DataType,
        new_data_type: DataType,
    ) -> None:
        """Replace a nested data type with append-position compatibility."""
        old_id = id(old_data_type)
        self.set_nested_data_types(
            parent_data_type,
            (data_type for data_type in (*parent_data_type.data_types, new_data_type) if id(data_type) != old_id),
        )

    def set_nested_data_types(self, data_type: DataType, nested_data_types: Iterable[DataType]) -> None:
        """Replace nested data types and invalidate derived facts."""
        for nested_data_type in data_type.data_types:
            nested_data_type.parent = None
        data_type.data_types = list(nested_data_types)
        for nested_data_type in data_type.data_types:
            nested_data_type.parent = data_type
        self._invalidate_after_mutation()

    def append_field(self, model: DataModel, field_: DataModelFieldBase) -> None:
        """Append a field to ``model`` and invalidate derived facts."""
        model.fields.append(field_)
        self._invalidate_after_mutation()

    def insert_field(self, model: DataModel, index: int, field_: DataModelFieldBase) -> None:
        """Insert a field into ``model`` and invalidate derived facts."""
        model.fields.insert(index, field_)
        self._invalidate_after_mutation()

    def remove_field(self, model: DataModel, field_: DataModelFieldBase) -> None:
        """Remove a field from ``model`` and invalidate derived facts."""
        model.fields.remove(field_)
        self._invalidate_after_mutation()

    def set_fields(self, model: DataModel, fields: Iterable[DataModelFieldBase]) -> None:
        """Replace all fields on ``model`` and invalidate derived facts."""
        model.fields = list(fields)
        self._invalidate_after_mutation()

    def set_base_classes(self, model: DataModel, base_classes: Iterable[BaseClassDataType]) -> None:
        """Replace ``model`` base classes and invalidate derived facts."""
        model.base_classes = list(base_classes)
        self._invalidate_after_mutation()

    def reset_base_classes(self, model: DataModel) -> None:
        """Reset ``model`` to its default base classes and invalidate derived facts."""
        model.set_base_class()
        self._invalidate_after_mutation()

    def redirect_reference_users(self, old_reference: Reference, new_reference: Reference) -> None:
        """Redirect every user of ``old_reference`` to ``new_reference``."""
        self._replace_reference_children(old_reference, new_reference)
        self._invalidate_after_mutation()

    def redirect_model_reference_users(
        self,
        model: DataModel,
        models: list[DataModel],
        new_reference: Reference,
    ) -> None:
        """Redirect ``model`` reference users owned by ``models`` to ``new_reference``."""
        model_ids = {id(candidate) for candidate in models}
        for child in model.reference.children[:]:
            if id(_outermost_parent(child)) in model_ids and hasattr(child, "replace_reference"):
                child.replace_reference(new_reference)
        self._invalidate_after_mutation()

    def collapse_root_data_type(self, data_type: DataType, inner_reference: Reference) -> None:
        """Replace a root-model data type with its inner reference."""
        with self.defer_refresh():
            if data_type.reference:
                self._prune_reference_children(data_type.reference, excluded_child=data_type, require_parent=True)
            self.replace_data_type_ref(data_type, inner_reference)

    def detach_model_data_type_refs(self, model: DataModel) -> None:
        """Detach every referenced data type currently owned by ``model``."""
        with self.defer_refresh():
            for data_type in model.all_data_types:
                if data_type.reference:
                    self.detach_data_type_ref(data_type)

    @contextmanager
    def defer_refresh(self) -> Generator[None, None, None]:
        """Batch mutation invalidations and rebuild derived facts once on exit."""
        self._defer_refresh_depth += 1
        completed = False
        try:
            yield
            completed = True
        finally:
            try:
                if completed and self._defer_refresh_depth == 1:
                    self.refresh_now()
            finally:
                self._defer_refresh_depth -= 1

    @staticmethod
    def _replace_data_type_reference(data_type: DataType, new_reference: Reference | None) -> None:
        if data_type.reference:
            data_type.replace_reference(new_reference)
        else:
            data_type.reference = new_reference
            if new_reference:
                new_reference.children.append(data_type)

    @staticmethod
    def _replace_reference_children(old_reference: Reference, new_reference: Reference) -> None:
        old_reference.replace_children_references(new_reference)

    @staticmethod
    def _prune_reference_children(
        reference: Reference,
        *,
        excluded_child: object | None = None,
        require_parent: bool = False,
    ) -> None:
        reference.children = [
            child
            for child in reference.children
            if child is not excluded_child and (not require_parent or getattr(child, "parent", None))
        ]

    def _invalidate_after_mutation(self) -> None:
        self._invalidate()

    def __iter__(self) -> Iterator[DataModel]:
        return iter(self.models)
