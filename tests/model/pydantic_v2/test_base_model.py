"""Tests for Pydantic v2 BaseModel generation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from datamodel_code_generator.model.pydantic_v2.base_model import BaseModel, DataModelField
from datamodel_code_generator.model.runtime_validation import RequiredGroupsRule, SchemaRuntimeValidation
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType
from tests.conftest import assert_output

EXPECTED_PYDANTIC_V2_MODEL_PATH = Path(__file__).parents[2] / "data" / "expected" / "model" / "pydantic_v2"


def _schema_runtime_validation() -> SchemaRuntimeValidation:
    return SchemaRuntimeValidation(
        required_groups=[
            RequiredGroupsRule(
                keyword="oneOf",
                groups=((("value",),),),
            )
        ]
    )


def test_base_model_methods_render_once_after_all_fields() -> None:
    """Render model methods once after every field declaration."""
    model = BaseModel(
        fields=[
            DataModelField(name="first", data_type=DataType(type="str"), required=True),
            DataModelField(name="second", data_type=DataType(type="int"), required=True),
        ],
        reference=Reference(name="Model", path="Model"),
    )
    model.methods.append('def generated_method(self) -> str:\n        return "ok"')

    rendered = model.render()

    assert_output(
        f"method count: {rendered.count('def generated_method(')}\n\n{rendered}\n",
        EXPECTED_PYDANTIC_V2_MODEL_PATH / "base_model_methods_once.txt",
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
