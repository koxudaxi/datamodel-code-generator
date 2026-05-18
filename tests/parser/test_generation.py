"""Tests for generation store and index helpers."""

from __future__ import annotations

from inline_snapshot import snapshot

from datamodel_code_generator.model.pydantic_v2 import BaseModel, DataModelField
from datamodel_code_generator.parser.generation import GenerationStore
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
    direct_type = DataType(reference=reference_inner)
    wrapper_model = RootModel(fields=[DataModelField(data_type=wrapper_type)], reference=reference_wrapper)
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

    with store.defer_refresh():
        store.replace_data_type_ref(data_type, reference_c)
        store.update_model_reference(model, reference_name="Renamed", new_path="Renamed")
        dirty_after_mutation = store._dirty
        reference_classes = sorted(store.index.reference_classes_for_model(model))
        dirty_after_query = store._dirty

    assert {
        "dirty_after_mutation": dirty_after_mutation,
        "dirty_after_query": dirty_after_query,
        "model_path": model.path,
        "reference_name": model.reference.name,
        "reference_classes": reference_classes,
    } == snapshot(
        {
            "dirty_after_mutation": True,
            "dirty_after_query": False,
            "model_path": "Renamed",
            "reference_name": "Renamed",
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
