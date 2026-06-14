"""Tests for generation store and index helpers."""

from __future__ import annotations

from pathlib import Path

from inline_snapshot import snapshot

from datamodel_code_generator.model.base import BaseClassDataType
from datamodel_code_generator.model.pydantic_v2 import BaseModel, DataModelField
from datamodel_code_generator.parser.generation import GenerationStore, set_model_base_classes
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def test_generation_store_indexes_model_and_reference_order() -> None:
    """Store facts preserve append order and expose model dependencies."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    data_type_b = DataType(reference=reference_b)
    model_a = BaseModel(fields=[DataModelField(data_type=data_type_b)], reference=reference_a)
    model_b = BaseModel(fields=[], reference=reference_b)
    store = GenerationStore()

    store.register_model(model_a)
    store.register_model(model_b)

    fact_a = store.index.model_fact(model_a)
    fact_b = store.index.model_fact(model_b)
    assert {
        "models": [model.reference.path for model in store.models],
        "facts": [
            (fact_a.path, fact_a.parse_order) if fact_a else None,
            (fact_b.path, fact_b.parse_order) if fact_b else None,
        ],
        "reference_classes": sorted(store.index.reference_classes_for_model(model_a)),
        "model_for_reference_b": store.index.model_for_reference(reference_b) is model_b,
        "data_type_facts_for_reference_b": [
            fact.data_type is data_type_b for fact in store.index.data_type_facts_for_reference(reference_b)
        ],
    } == snapshot(
        {
            "models": ["A", "B"],
            "facts": [("A", 0), ("B", 1)],
            "reference_classes": ["B"],
            "model_for_reference_b": True,
            "data_type_facts_for_reference_b": [True],
        },
    )


def test_generation_facts_remove_legacy_edge_buckets() -> None:
    """Legacy edge buckets should be absent while reverse edges remain populated."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    data_type_b = DataType(reference=reference_b)
    model_a = BaseModel(fields=[DataModelField(data_type=data_type_b)], reference=reference_a)
    model_b = BaseModel(fields=[], reference=reference_b)
    store = GenerationStore()

    store.register_model(model_a)
    store.register_model(model_b)
    facts = store.current_facts()

    assert not hasattr(facts, "field_edges")
    assert not hasattr(facts, "base_edges")
    assert not hasattr(facts, "all_edges")
    assert [list(data_type_ids) for data_type_ids in facts.reverse_edges.values()] == [[0]]


def test_generation_store_replace_data_type_ref_updates_children_and_index() -> None:
    """Reference replacement keeps compatibility children and derived facts aligned."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    reference_c = Reference(path="C", original_name="C", name="C")
    data_type = DataType(reference=reference_b)
    model = BaseModel(fields=[DataModelField(data_type=data_type)], reference=reference_a)
    store = GenerationStore()
    store.register_model(model)
    cached_before_mutation = sorted(store.index.reference_classes_for_model(model))

    store.replace_data_type_ref(data_type, reference_c)

    assert {
        "cached_before_mutation": cached_before_mutation,
        "old_children": [child is data_type for child in reference_b.children],
        "new_children": [child is data_type for child in reference_c.children],
        "reference_classes": sorted(store.index.reference_classes_for_model(model)),
        "has_reference_b": store.index.has_data_type_references(reference_b),
        "has_reference_c": store.index.has_data_type_references(reference_c),
    } == snapshot(
        {
            "cached_before_mutation": ["B"],
            "old_children": [],
            "new_children": [True],
            "reference_classes": ["C"],
            "has_reference_b": False,
            "has_reference_c": True,
        },
    )


def test_generation_index_detects_remaining_reference_users() -> None:
    """Reference user checks can exclude the data type being rewritten."""
    reference_model = Reference(path="Model", original_name="Model", name="Model")
    reference_target = Reference(path="Target", original_name="Target", name="Target")
    first_type = DataType(reference=reference_target)
    second_type = DataType(reference=reference_target)
    model = BaseModel(
        fields=[
            DataModelField(data_type=first_type),
            DataModelField(data_type=second_type),
        ],
        reference=reference_model,
    )
    store = GenerationStore()
    store.register_model(model)

    before_detach = store.index.has_data_type_references_other_than(reference_target, first_type)
    store.detach_data_type_ref(second_type)
    after_detach = store.index.has_data_type_references_other_than(reference_target, first_type)

    assert {"before_detach": before_detach, "after_detach": after_detach} == snapshot(
        {"before_detach": True, "after_detach": False},
    )


def test_generation_index_combines_root_collapse_reference_usage() -> None:
    """Root collapse checks should scan a reference's reverse edges once."""

    class RootModel(BaseModel):
        pass

    reference_inner = Reference(path="Inner", original_name="Inner", name="Inner")
    reference_wrapper = Reference(path="Wrapper", original_name="Wrapper", name="Wrapper")
    reference_direct = Reference(path="Direct", original_name="Direct", name="Direct")
    wrapper_type = DataType(reference=reference_inner)
    duplicate_wrapper_type = DataType(reference=reference_inner)
    direct_type = DataType(reference=reference_inner)
    wrapper_model = RootModel(
        fields=[
            DataModelField(data_type=wrapper_type),
            DataModelField(data_type=duplicate_wrapper_type),
        ],
        reference=reference_wrapper,
    )
    direct_model = BaseModel(fields=[DataModelField(data_type=direct_type)], reference=reference_direct)
    store = GenerationStore()
    store.register_model(wrapper_model)
    store.register_model(direct_model)

    wrappers, direct_refs = store.index.root_collapse_reference_usage(
        reference_inner,
        excluded_model=wrapper_model,
        root_model_type=RootModel,
    )

    assert {
        "wrappers": [model.reference.path for model in wrappers],
        "direct_refs": [fact.data_type is direct_type for fact in direct_refs],
    } == snapshot({"wrappers": ["Wrapper"], "direct_refs": [True]})


def test_generation_store_defer_refresh_batches_mutations() -> None:
    """Batching avoids rebuilding facts once per mutation."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    reference_c = Reference(path="C", original_name="C", name="C")
    data_type = DataType(reference=reference_b)
    model = BaseModel(fields=[DataModelField(data_type=data_type)], reference=reference_a)
    store = GenerationStore()
    store.register_model(model)
    store.refresh()
    version_before_mutation = store.facts_version

    with store.defer_refresh():
        store.replace_data_type_ref(data_type, reference_c)
        store.update_model_reference(model, reference_name="Renamed", new_path="Renamed")
        dirty_after_mutation = store._dirty
        version_after_mutation = store.facts_version
        reference_classes_inside_defer = sorted(store.index.reference_classes_for_model(model))

    version_after_defer = store.facts_version
    reference_classes_after_defer = sorted(store.index.reference_classes_for_model(model))

    assert {
        "version_before_mutation": version_before_mutation,
        "dirty_after_mutation": dirty_after_mutation,
        "version_after_mutation": version_after_mutation,
        "version_after_defer": version_after_defer,
        "model_path": model.path,
        "reference_name": model.reference.name,
        "reference_classes_inside_defer": reference_classes_inside_defer,
        "reference_classes_after_defer": reference_classes_after_defer,
    } == snapshot(
        {
            "version_before_mutation": 1,
            "dirty_after_mutation": True,
            "version_after_mutation": 1,
            "version_after_defer": 2,
            "model_path": "Renamed",
            "reference_name": "Renamed",
            "reference_classes_inside_defer": ["B"],
            "reference_classes_after_defer": ["C"],
        },
    )


def test_generation_store_refresh_now_updates_facts_inside_defer() -> None:
    """Callers that need fresh facts inside a mutation block can refresh explicitly."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    reference_c = Reference(path="C", original_name="C", name="C")
    data_type = DataType(reference=reference_b)
    model = BaseModel(fields=[DataModelField(data_type=data_type)], reference=reference_a)
    store = GenerationStore()
    store.register_model(model)
    store.refresh()

    with store.defer_refresh():
        store.replace_data_type_ref(data_type, reference_c)
        version_after_mutation = store.facts_version
        store.refresh_now()
        version_after_refresh_now = store.facts_version
        reference_classes = sorted(store.index.reference_classes_for_model(model))

    assert {
        "version_after_mutation": version_after_mutation,
        "version_after_refresh_now": version_after_refresh_now,
        "version_after_defer": store.facts_version,
        "reference_classes": reference_classes,
    } == snapshot(
        {
            "version_after_mutation": 1,
            "version_after_refresh_now": 2,
            "version_after_defer": 2,
            "reference_classes": ["C"],
        },
    )


def test_generation_store_nested_defer_refresh_rebuilds_on_outer_exit() -> None:
    """Nested deferred blocks should rebuild facts only when the outer block exits."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    reference_c = Reference(path="C", original_name="C", name="C")
    data_type = DataType(reference=reference_b)
    model = BaseModel(fields=[DataModelField(data_type=data_type)], reference=reference_a)
    store = GenerationStore()
    store.register_model(model)
    store.refresh()

    with store.defer_refresh():
        with store.defer_refresh():
            store.replace_data_type_ref(data_type, reference_c)
        version_after_inner_exit = store.facts_version
        dirty_after_inner_exit = store._dirty

    assert {
        "version_after_inner_exit": version_after_inner_exit,
        "dirty_after_inner_exit": dirty_after_inner_exit,
        "version_after_outer_exit": store.facts_version,
        "reference_classes": sorted(store.index.reference_classes_for_model(model)),
    } == snapshot(
        {
            "version_after_inner_exit": 1,
            "dirty_after_inner_exit": True,
            "version_after_outer_exit": 2,
            "reference_classes": ["C"],
        },
    )


def test_generation_store_records_nested_and_dict_key_roles() -> None:
    """Data type facts should distinguish nested values from dictionary keys."""
    reference_model = Reference(path="Model", original_name="Model", name="Model")
    reference_value = Reference(path="Value", original_name="Value", name="Value")
    reference_key = Reference(path="Key", original_name="Key", name="Key")
    value_type = DataType(reference=reference_value)
    key_type = DataType(reference=reference_key)
    dict_type = DataType(data_types=[value_type], dict_key=DataType(data_types=[key_type]))
    model = BaseModel(fields=[DataModelField(data_type=dict_type)], reference=reference_model)
    store = GenerationStore()

    store.register_model(model)
    store.refresh()

    assert [
        (fact.role, fact.reference.path if fact.reference else None) for fact in store.data_type_facts.values()
    ] == snapshot(
        [
            ("field", None),
            ("nested", "Value"),
            ("dict_key", None),
            ("dict_key", "Key"),
            ("base", None),
        ],
    )
    assert store.index.reference_classes_for_model(model) == snapshot(frozenset({"Value"}))


def test_generation_store_replaces_nested_data_types() -> None:
    """Nested type replacement should keep parent pointers and facts in sync."""
    reference_model = Reference(path="Model", original_name="Model", name="Model")
    reference_old = Reference(path="Old", original_name="Old", name="Old")
    reference_new = Reference(path="New", original_name="New", name="New")
    old_type = DataType(reference=reference_old)
    parent_type = DataType(data_types=[old_type])
    old_type.parent = parent_type
    model = BaseModel(fields=[DataModelField(data_type=parent_type)], reference=reference_model)
    store = GenerationStore()
    store.register_model(model)

    new_type = DataType(reference=reference_new)
    store.set_nested_data_types(parent_type, [new_type])

    assert {
        "old_parent": old_type.parent,
        "new_parent": new_type.parent is parent_type,
        "reference_classes": sorted(store.index.reference_classes_for_model(model)),
    } == snapshot(
        {
            "old_parent": None,
            "new_parent": True,
            "reference_classes": ["New"],
        },
    )


def test_set_model_base_classes_supports_store_and_legacy_fallback() -> None:
    """The helper keeps direct fallback compatibility while updating store facts when available."""
    reference_model = Reference(path="Model", original_name="Model", name="Model")
    reference_base = Reference(path="Base", original_name="Base", name="Base")
    reference_legacy = Reference(path="Legacy", original_name="Legacy", name="Legacy")
    model = BaseModel(fields=[], reference=reference_model)
    store = GenerationStore()
    store.register_model(model)

    set_model_base_classes(model, [BaseClassDataType(reference=reference_base)], store)
    store_reference_classes = sorted(store.index.reference_classes_for_model(model))
    set_model_base_classes(model, [BaseClassDataType(reference=reference_legacy)], None)

    assert {
        "store_reference_classes": store_reference_classes,
        "legacy_base_classes": [base_class.reference.path for base_class in model.base_classes if base_class.reference],
    } == snapshot(
        {
            "store_reference_classes": ["Base"],
            "legacy_base_classes": ["Legacy"],
        },
    )


def test_generation_model_list_invalidates_for_list_compatible_mutations() -> None:
    """The Parser.results-compatible list still invalidates store facts for every list mutation."""

    def make_model(path: str) -> BaseModel:
        return BaseModel(fields=[], reference=Reference(path=path, original_name=path, name=path))

    model_a = make_model("A")
    model_b = make_model("B")
    model_c = make_model("C")
    model_d = make_model("D")
    model_e = make_model("E")
    store = GenerationStore()

    store.models.extend([model_a, model_b])
    store.refresh()
    version_after_extend = store.facts_version
    store.models.insert(1, model_c)
    store.models[0] = model_d
    store.models[1:2] = [model_e]
    del store.models[2:]
    store.models.append(model_a)
    popped = store.models.pop()
    store.models.remove(model_e)
    store.models.clear()

    assert {
        "version_after_extend": version_after_extend,
        "dirty_after_mutations": store._dirty,
        "popped": popped.reference.path,
        "models": [model.reference.path for model in store.models],
        "model_facts": list(store.model_facts.values()),
    } == snapshot(
        {
            "version_after_extend": 1,
            "dirty_after_mutations": True,
            "popped": "A",
            "models": [],
            "model_facts": [],
        },
    )


def test_generation_index_returns_empty_results_for_unknown_objects() -> None:
    """Unknown references and objects should return explicit empty values, not stale facts."""
    reference_model = Reference(path="Model", original_name="Model", name="Model")
    reference_target = Reference(path="Target", original_name="Target", name="Target")
    reference_unknown = Reference(path="Unknown", original_name="Unknown", name="Unknown")
    data_type = DataType(reference=reference_target)
    model = BaseModel(fields=[DataModelField(data_type=data_type)], reference=reference_model)
    unknown_model = BaseModel(
        fields=[DataModelField(data_type=DataType(reference=reference_unknown))],
        reference=reference_unknown,
    )
    unknown_data_type = DataType(reference=reference_unknown)
    store = GenerationStore()
    store.register_model(model)

    assert {
        "unknown_model_fact": store.index.model_fact(unknown_model),
        "known_model_id_for_reference": store.index.model_id_for_reference(reference_model),
        "unknown_model_for_reference": store.index.model_for_reference(reference_unknown),
        "unknown_data_type_facts_for_reference": store.index.data_type_facts_for_reference(reference_unknown),
        "unknown_has_other_refs": store.index.has_data_type_references_other_than(reference_unknown, data_type),
        "known_owner": store.index.owner_model_for_data_type(data_type) is model,
        "unknown_owner": store.index.owner_model_for_data_type(unknown_data_type),
        "unknown_reference_classes": sorted(store.index.reference_classes_for_model(unknown_model)),
        "facts_property": store.facts is store.current_facts(),
        "model_facts_property": len(store.model_facts),
        "data_type_fact_by_object_property": id(data_type) in store.data_type_fact_by_object,
        "model_by_path_property": dict(store.model_by_path),
        "model_by_ref_id_property": sorted(store.model_by_ref_id.values()),
        "data_types_by_model_property": {
            model_id: list(data_type_ids) for model_id, data_type_ids in store.data_types_by_model.items()
        },
        "reverse_edges_property": [list(data_type_ids) for data_type_ids in store.reverse_edges.values()],
    } == snapshot(
        {
            "unknown_model_fact": None,
            "known_model_id_for_reference": 0,
            "unknown_model_for_reference": None,
            "unknown_data_type_facts_for_reference": (),
            "unknown_has_other_refs": False,
            "known_owner": True,
            "unknown_owner": None,
            "unknown_reference_classes": ["Unknown"],
            "facts_property": True,
            "model_facts_property": 1,
            "data_type_fact_by_object_property": True,
            "model_by_path_property": {"Model": 0},
            "model_by_ref_id_property": [0],
            "data_types_by_model_property": {0: [0, 1]},
            "reverse_edges_property": [[0]],
        },
    )


def test_generation_index_exposes_root_collapse_helpers_independently() -> None:
    """Split root-collapse helpers should preserve the combined query's ordering."""

    class RootModel(BaseModel):
        pass

    reference_inner = Reference(path="Inner", original_name="Inner", name="Inner")
    reference_wrapper = Reference(path="Wrapper", original_name="Wrapper", name="Wrapper")
    reference_direct = Reference(path="Direct", original_name="Direct", name="Direct")
    reference_base = Reference(path="Base", original_name="Base", name="Base")
    reference_unknown = Reference(path="Unknown", original_name="Unknown", name="Unknown")
    wrapper_model = RootModel(
        fields=[
            DataModelField(data_type=DataType(reference=reference_inner)),
            DataModelField(data_type=DataType(reference=reference_inner)),
        ],
        reference=reference_wrapper,
    )
    direct_model = BaseModel(
        fields=[DataModelField(data_type=DataType(reference=reference_inner))],
        reference=reference_direct,
    )
    base_model = BaseModel(fields=[], base_classes=[reference_inner], reference=reference_base)
    store = GenerationStore()
    store.register_model(wrapper_model)
    store.register_model(direct_model)
    store.register_model(base_model)

    wrappers = store.index.root_model_wrappers_for_reference(reference_inner, RootModel)
    direct_refs = store.index.direct_non_root_refs_for_reference(
        reference_inner,
        excluded_model=base_model,
        root_model_type=RootModel,
    )
    missing_direct_refs = store.index.direct_non_root_refs_for_reference(
        reference_unknown,
        excluded_model=base_model,
        root_model_type=RootModel,
    )
    missing_root_wrappers = store.index.root_model_wrappers_for_reference(reference_unknown, RootModel)
    missing_wrappers, missing_collapse_direct_refs = store.index.root_collapse_reference_usage(
        reference_unknown,
        excluded_model=base_model,
        root_model_type=RootModel,
    )

    assert {
        "wrappers": [model.reference.path for model in wrappers],
        "direct_refs": [fact.owner_field_index for fact in direct_refs],
        "missing_direct_refs": missing_direct_refs,
        "missing_root_wrappers": missing_root_wrappers,
        "missing_wrappers": missing_wrappers,
        "missing_collapse_direct_refs": missing_collapse_direct_refs,
    } == snapshot(
        {
            "wrappers": ["Wrapper"],
            "direct_refs": [0],
            "missing_direct_refs": [],
            "missing_root_wrappers": [],
            "missing_wrappers": [],
            "missing_collapse_direct_refs": [],
        },
    )


def test_generation_store_updates_model_and_field_metadata() -> None:
    """Model metadata and field mutations should refresh dependent facts through store APIs."""
    reference_model = Reference(path="Model", original_name="Model", name="Model")
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    model = BaseModel(fields=[], reference=reference_model)
    field_a = DataModelField(data_type=DataType(reference=reference_a))
    field_b = DataModelField(data_type=DataType(reference=reference_b))
    store = GenerationStore()
    store.register_model(model)

    store.append_field(model, field_a)
    store.insert_field(model, 0, field_b)
    store.remove_field(model, field_a)
    store.rename_model(model, class_name="RenamedModel", reference_name="Renamed")
    store.move_model(model, new_path="pkg.Renamed", new_file_path=Path("pkg.py"))

    assert {
        "fields": [field.data_type.reference.path for field in model.fields if field.data_type.reference],
        "class_name": model.class_name,
        "reference_name": model.reference.name,
        "path": model.path,
        "file_path": model.file_path,
        "reference_classes": sorted(store.index.reference_classes_for_model(model)),
    } == snapshot(
        {
            "fields": ["B"],
            "class_name": "Renamed",
            "reference_name": "Renamed",
            "path": "pkg.Renamed",
            "file_path": Path("pkg.py"),
            "reference_classes": ["B"],
        },
    )


def test_generation_store_redirects_model_reference_users_by_owner() -> None:
    """Reference redirection should only affect children owned by the requested models."""
    reference_target = Reference(path="Target", original_name="Target", name="Target")
    reference_owner = Reference(path="Owner", original_name="Owner", name="Owner")
    reference_other = Reference(path="Other", original_name="Other", name="Other")
    reference_new = Reference(path="New", original_name="New", name="New")
    target_model = BaseModel(fields=[], reference=reference_target)
    owner_type = DataType(reference=reference_target)
    other_type = DataType(reference=reference_target)
    owner_model = BaseModel(fields=[DataModelField(data_type=owner_type)], reference=reference_owner)
    other_model = BaseModel(fields=[DataModelField(data_type=other_type)], reference=reference_other)
    store = GenerationStore()
    store.register_model(target_model)
    store.register_model(owner_model)
    store.register_model(other_model)

    store.redirect_model_reference_users(target_model, [owner_model], reference_new)

    assert {
        "owner_reference": owner_type.reference.path if owner_type.reference else None,
        "other_reference": other_type.reference.path if other_type.reference else None,
        "old_children": [child is other_type for child in reference_target.children],
        "new_children": [child is owner_type for child in reference_new.children],
        "owner_reference_classes": sorted(store.index.reference_classes_for_model(owner_model)),
        "other_reference_classes": sorted(store.index.reference_classes_for_model(other_model)),
    } == snapshot(
        {
            "owner_reference": "New",
            "other_reference": "Target",
            "old_children": [True],
            "new_children": [True],
            "owner_reference_classes": ["New"],
            "other_reference_classes": ["Target"],
        },
    )


def test_generation_store_collapse_and_attach_reference_edges() -> None:
    """Root collapse and first reference attachment should keep compatibility children aligned."""
    reference_model = Reference(path="Model", original_name="Model", name="Model")
    reference_outer = Reference(path="Outer", original_name="Outer", name="Outer")
    reference_inner = Reference(path="Inner", original_name="Inner", name="Inner")
    reference_attached = Reference(path="Attached", original_name="Attached", name="Attached")
    root_type = DataType(reference=reference_outer)
    unreferenced_root_type = DataType()
    model = BaseModel(fields=[DataModelField(data_type=root_type)], reference=reference_model)
    unattached_type = DataType()
    detached_type = DataType()
    store = GenerationStore()
    store.register_model(model)

    store.collapse_root_data_type(root_type, reference_inner)
    store.collapse_root_data_type(unreferenced_root_type, reference_inner)
    store.replace_data_type_ref(unattached_type, reference_attached)
    store.detach_data_type_ref(detached_type)

    assert {
        "iter_paths": [tracked_model.reference.path for tracked_model in store],
        "root_reference": root_type.reference.path if root_type.reference else None,
        "unreferenced_root_reference": (
            unreferenced_root_type.reference.path if unreferenced_root_type.reference else None
        ),
        "detached_reference": detached_type.reference.path if detached_type.reference else None,
        "old_children": [child is root_type for child in reference_outer.children],
        "inner_children": [child is root_type or child is unreferenced_root_type for child in reference_inner.children],
        "attached_children": [child is unattached_type for child in reference_attached.children],
        "reference_classes": sorted(store.index.reference_classes_for_model(model)),
    } == snapshot(
        {
            "iter_paths": ["Model"],
            "root_reference": "Inner",
            "unreferenced_root_reference": "Inner",
            "detached_reference": None,
            "old_children": [],
            "inner_children": [True, True],
            "attached_children": [True],
            "reference_classes": ["Inner"],
        },
    )
