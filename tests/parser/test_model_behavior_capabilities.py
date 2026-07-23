"""Tests for output model behavior capabilities consumed by the parser."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.model.base import has_field_assignment
from datamodel_code_generator.model.dataclass import has_field_assignment as dataclass_has_field_assignment
from datamodel_code_generator.model.msgspec import has_field_assignment as msgspec_has_field_assignment
from datamodel_code_generator.model.pydantic_v2.dataclass import (
    has_field_assignment as pydantic_dataclass_has_field_assignment,
)
from datamodel_code_generator.parser.base import Parser
from datamodel_code_generator.reference import Reference

if TYPE_CHECKING:
    from collections.abc import Callable

    from datamodel_code_generator.model.base import DataModel, DataModelFieldBase

_BEHAVIOR_CAPABILITIES: dict[
    DataModelType,
    tuple[Callable[[DataModelFieldBase], bool], bool],
] = {
    DataModelType.PydanticV2BaseModel: (has_field_assignment, True),
    DataModelType.PydanticV2Dataclass: (has_field_assignment, False),
    DataModelType.DataclassesDataclass: (has_field_assignment, True),
    DataModelType.TypingTypedDict: (has_field_assignment, False),
    DataModelType.MsgspecStruct: (msgspec_has_field_assignment, False),
}


@pytest.mark.allow_direct_assert
def test_behavior_capability_matrix_covers_every_data_model_type() -> None:
    """Require each canonical output target to keep an intentional contract."""
    assert set(_BEHAVIOR_CAPABILITIES) == set(DataModelType)


@pytest.mark.parametrize(
    ("output_model_type", "expected"),
    [
        pytest.param(output_model_type, capabilities, id=output_model_type.name)
        for output_model_type, capabilities in _BEHAVIOR_CAPABILITIES.items()
    ],
)
@pytest.mark.allow_direct_assert
def test_standard_models_declare_parser_behavior_capabilities(
    output_model_type: DataModelType,
    expected: tuple[Callable[[DataModelFieldBase], bool], bool],
) -> None:
    """Resolve field assignment and tree reuse behavior without backend inspection."""
    model_types = get_data_model_types(output_model_type, target_python_version=PythonVersion.PY_311)
    expected_checker, expected_tree_reuse_inheritance = expected
    model = model_types.data_model(
        reference=Reference(path=output_model_type.name, name=output_model_type.name),
        fields=[],
    )

    assert type(model).FIELD_ASSIGNMENT_CHECKER is expected_checker
    assert Parser._get_field_assignment_checker(model) is expected_checker
    assert model.SUPPORTS_TREE_SCOPE_REUSE_MODEL_INHERITANCE is expected_tree_reuse_inheritance


@pytest.mark.parametrize(
    ("output_model_type", "expected"),
    [
        pytest.param(output_model_type, capabilities, id=output_model_type.name)
        for output_model_type, capabilities in _BEHAVIOR_CAPABILITIES.items()
    ],
)
@pytest.mark.allow_direct_assert
def test_external_model_subclasses_inherit_parser_behavior_capabilities(
    output_model_type: DataModelType,
    expected: tuple[Callable[[DataModelFieldBase], bool], bool],
) -> None:
    """Preserve existing behavior for external subclasses of built-in outputs."""
    model_types = get_data_model_types(output_model_type, target_python_version=PythonVersion.PY_311)
    external_model_type = cast("type[DataModel]", type("ExternalModel", (model_types.data_model,), {}))
    expected_checker, expected_tree_reuse_inheritance = expected

    assert external_model_type.FIELD_ASSIGNMENT_CHECKER is expected_checker
    assert external_model_type.SUPPORTS_TREE_SCOPE_REUSE_MODEL_INHERITANCE is expected_tree_reuse_inheritance


@pytest.mark.allow_direct_assert
def test_field_assignment_helpers_preserve_public_imports() -> None:
    """Keep dataclass helper imports compatible while sharing the neutral implementation."""
    assert dataclass_has_field_assignment is has_field_assignment
    assert pydantic_dataclass_has_field_assignment is has_field_assignment
    assert msgspec_has_field_assignment is not has_field_assignment
