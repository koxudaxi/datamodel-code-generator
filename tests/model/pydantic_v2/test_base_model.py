"""Tests for Pydantic v2 BaseModel generation helpers."""

from __future__ import annotations

import pytest

from datamodel_code_generator import DataModelType
from datamodel_code_generator.config import JSONSchemaParserConfig
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.model.pydantic_v2.base_model import (
    BaseModel,
    Constraints,
    DataModelField,
    _construct_parser_simple_field,
)
from datamodel_code_generator.model.runtime_validation import RequiredGroupsRule, SchemaRuntimeValidation
from datamodel_code_generator.parser.base import _get_builtin_pydantic_v2_field_constructor
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def _schema_runtime_validation() -> SchemaRuntimeValidation:
    return SchemaRuntimeValidation(
        required_groups=[
            RequiredGroupsRule(
                keyword="oneOf",
                groups=((("value",),),),
            )
        ]
    )


@pytest.mark.allow_direct_assert
def test_schema_runtime_validation_base_inheritance_detects_transitive_base() -> None:
    """Detect inherited runtime validation bases through non-runtime intermediate models."""
    runtime_base = BaseModel(fields=[], reference=Reference(name="RuntimeBase", path="#/RuntimeBase"))
    runtime_base.extra_template_data["schema_runtime_validation"] = _schema_runtime_validation()

    intermediate = BaseModel(
        fields=[],
        reference=Reference(name="Intermediate", path="#/Intermediate"),
        base_classes=[runtime_base.reference],
    )
    runtime_leaf = BaseModel(
        fields=[],
        reference=Reference(name="RuntimeLeaf", path="#/RuntimeLeaf"),
        base_classes=[intermediate.reference],
    )

    assert BaseModel._inherits_schema_runtime_validation_base(runtime_leaf, seen=set())
    assert not BaseModel._inherits_schema_runtime_validation_base(
        runtime_leaf,
        seen={runtime_leaf.reference.path},
    )


@pytest.mark.allow_direct_assert
def test_schema_runtime_validation_helpers_are_gated_by_parser_option() -> None:
    """Avoid scanning and rendering runtime helpers for the normal Pydantic v2 path."""
    runtime_model = BaseModel(fields=[], reference=Reference(name="RuntimeModel", path="#/RuntimeModel"))
    runtime_model.extra_template_data["schema_runtime_validation"] = _schema_runtime_validation()

    assert not BaseModel.render_module_code([runtime_model])

    runtime_model.extra_template_data["schema_runtime_validation_enabled"] = True

    assert "_JsonSchemaRuntimeValidationBase" in BaseModel.render_module_code([runtime_model])


@pytest.mark.allow_direct_assert
def test_parser_simple_field_matches_validated_field() -> None:
    """Keep every fast-constructor field and private slot equivalent to Pydantic."""
    representative_values = {
        "name": "item_name",
        "default": "'item'",
        "required": True,
        "alias": "item-name",
        "validation_aliases": ["item_name", "item-name"],
        "serialization_alias": "itemName",
        "constraints": None,
        "strip_default_none": True,
        "nullable": True,
        "parent": None,
        "extras": {},
        "use_annotated": True,
        "use_serialize_as_any": True,
        "has_default": True,
        "use_field_description": True,
        "use_field_description_example": True,
        "use_inline_field_description": True,
        "const": False,
        "original_name": "item-name",
        "use_default_kwarg": True,
        "use_missing_sentinel": True,
        "use_one_literal_as_default": True,
        "type_has_null": True,
        "read_only": True,
        "write_only": True,
        "use_frozen_field": True,
        "use_serialization_alias": True,
        "use_default_factory_for_optional_nested_models": True,
        "use_default_with_required": True,
    }
    assert representative_values.keys() | {"data_type"} == DataModelField.model_fields.keys()
    assert {
        name for name, field_info in DataModelField.model_fields.items() if field_info.default_factory is not None
    } == {"extras"}

    pydantic_slots = {
        slot
        for model_type in DataModelField.__mro__
        for slot in getattr(model_type, "__slots__", ())
        if slot.startswith("__pydantic_")
    }
    for values in ({}, representative_values):
        data_type = DataType(type="str")
        validated = DataModelField(**values, data_type=data_type)
        constructed = _construct_parser_simple_field(**values, data_type=data_type)

        assert constructed.__dict__ == validated.__dict__
        assert {slot: getattr(constructed, slot) for slot in pydantic_slots} == {
            slot: getattr(validated, slot) for slot in pydantic_slots
        }
        assert constructed.model_dump() == validated.model_dump()
        assert constructed.model_dump(exclude_unset=True) == validated.model_dump(exclude_unset=True)
        assert repr(constructed) == repr(validated)
        assert constructed.type_hint == validated.type_hint
        assert constructed.field == validated.field


@pytest.mark.allow_direct_assert
def test_parser_simple_field_preserves_parent_and_fresh_extras() -> None:
    """Set reference parents and never share the mutable extras default."""
    first_type = DataType(reference=Reference(path="#/First", name="First"))
    second_type = DataType(reference=Reference(path="#/Second", name="Second"))
    first = _construct_parser_simple_field(data_type=first_type)
    second = _construct_parser_simple_field(data_type=second_type)

    assert first_type.parent is first
    assert second_type.parent is second
    assert first.extras == second.extras == {}
    assert first.extras is not second.extras


@pytest.mark.allow_direct_assert
def test_parser_simple_field_falls_back_for_processed_values() -> None:
    """Retain Pydantic validation for constraints, extras, and const fields."""
    constrained = _construct_parser_simple_field(data_type=DataType(type="str"), constraints={})
    with_extras = _construct_parser_simple_field(
        data_type=DataType(type="str"),
        extras={"example": "sample"},
    )
    const = _construct_parser_simple_field(
        data_type=DataType(type="str"),
        extras={"const": "fixed"},
    )

    assert isinstance(constrained.constraints, Constraints)
    assert with_extras.extras == {"examples": ["sample"]}
    assert const.const
    assert const.data_type.literals == ["fixed"]


@pytest.mark.allow_direct_assert
def test_parser_simple_field_constructor_requires_exact_builtin_type() -> None:
    """Keep custom field subclasses on their public constructors."""

    class CustomDataModelField(DataModelField):
        pass

    assert _get_builtin_pydantic_v2_field_constructor(DataModelField) is _construct_parser_simple_field
    assert _get_builtin_pydantic_v2_field_constructor(CustomDataModelField) is None


@pytest.mark.allow_direct_assert
def test_parser_neutral_field_uses_internal_constructor() -> None:
    """Construct schema-free fields through the parser-owned fast path."""
    data_model_types = get_data_model_types(DataModelType.PydanticV2BaseModel)
    parser = JsonSchemaParser(
        "{}",
        config=JSONSchemaParserConfig(
            data_model_type=data_model_types.data_model,
            data_model_root_type=data_model_types.root_model,
            data_model_field_type=data_model_types.field_model,
            data_type_manager_type=data_model_types.data_type_manager,
            dump_resolve_reference_action=data_model_types.dump_resolve_reference_action,
        ),
    )
    data_type = DataType(type="str")

    field = parser.get_object_field(
        field_name="value",
        field=None,
        required=True,
        field_type=data_type,
        alias=None,
        original_field_name="value",
    )

    assert type(field) is DataModelField
    assert field.name == "value"
    assert field.required
    assert field.data_type is data_type
