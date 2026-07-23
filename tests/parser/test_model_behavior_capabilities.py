"""Tests for output model behavior capabilities consumed by the parser."""

from __future__ import annotations

import inspect
import pickle
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.model import DataModelFieldBase, get_data_model_types
from datamodel_code_generator.model.base import DataModel, _has_field_assignment
from datamodel_code_generator.model.dataclass import (
    DataModelField as DataclassDataModelField,
)
from datamodel_code_generator.model.dataclass import (
    has_field_assignment as dataclass_has_field_assignment,
)
from datamodel_code_generator.model.msgspec import has_field_assignment as msgspec_has_field_assignment
from datamodel_code_generator.model.pydantic_v2.dataclass import (
    has_field_assignment as pydantic_dataclass_has_field_assignment,
)
from datamodel_code_generator.parser.base import Parser
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType

if TYPE_CHECKING:
    from collections.abc import Callable

_BEHAVIOR_CAPABILITIES: dict[
    DataModelType,
    tuple[Callable[[DataModelFieldBase], bool], bool, bool],
] = {
    DataModelType.PydanticV2BaseModel: (_has_field_assignment, True, False),
    DataModelType.PydanticV2Dataclass: (_has_field_assignment, False, False),
    DataModelType.DataclassesDataclass: (_has_field_assignment, True, False),
    DataModelType.TypingTypedDict: (_has_field_assignment, False, False),
    DataModelType.MsgspecStruct: (msgspec_has_field_assignment, False, True),
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
    expected: tuple[Callable[[DataModelFieldBase], bool], bool, bool],
) -> None:
    """Resolve field assignment and tree reuse behavior without backend inspection."""
    model_types = get_data_model_types(output_model_type, target_python_version=PythonVersion.PY_311)
    expected_checker, expected_tree_reuse_inheritance, expected_explicit_deferred_annotations = expected
    model = model_types.data_model(
        reference=Reference(path=output_model_type.name, name=output_model_type.name),
        fields=[],
    )

    assert type(model).FIELD_ASSIGNMENT_CHECKER is expected_checker
    assert Parser._get_field_assignment_checker(model) is expected_checker
    assert model.SUPPORTS_TREE_SCOPE_REUSE_MODEL_INHERITANCE is expected_tree_reuse_inheritance
    assert model.REQUIRES_EXPLICIT_DEFERRED_ANNOTATIONS_FOR_FORWARD_REFS is expected_explicit_deferred_annotations


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
    expected: tuple[Callable[[DataModelFieldBase], bool], bool, bool],
) -> None:
    """Preserve existing behavior for external subclasses of built-in outputs."""
    model_types = get_data_model_types(output_model_type, target_python_version=PythonVersion.PY_311)
    external_model_type = type("ExternalModel", (model_types.data_model,), {})
    expected_checker, expected_tree_reuse_inheritance, expected_explicit_deferred_annotations = expected

    assert issubclass(external_model_type, DataModel)
    assert external_model_type.FIELD_ASSIGNMENT_CHECKER is expected_checker
    assert external_model_type.SUPPORTS_TREE_SCOPE_REUSE_MODEL_INHERITANCE is expected_tree_reuse_inheritance
    assert (
        external_model_type.REQUIRES_EXPLICIT_DEFERRED_ANNOTATIONS_FOR_FORWARD_REFS
        is expected_explicit_deferred_annotations
    )


@pytest.mark.allow_direct_assert
def test_field_assignment_helpers_preserve_public_imports() -> None:
    """Keep public dataclass helper identity and introspection metadata compatible."""
    signature = inspect.signature(dataclass_has_field_assignment)
    field_parameter = signature.parameters["field"]

    assert tuple(signature.parameters) == ("field",)
    assert field_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert field_parameter.default is inspect.Parameter.empty
    assert field_parameter.annotation == "DataModelFieldBase"
    assert signature.return_annotation == "bool"
    assert dataclass_has_field_assignment.__module__ == "datamodel_code_generator.model.dataclass"
    assert dataclass_has_field_assignment.__qualname__ == "has_field_assignment"
    assert pydantic_dataclass_has_field_assignment is dataclass_has_field_assignment
    assert pickle.loads(pickle.dumps(dataclass_has_field_assignment)) is dataclass_has_field_assignment
    assert msgspec_has_field_assignment is not dataclass_has_field_assignment


@pytest.mark.parametrize(
    "field",
    [
        pytest.param(
            DataModelFieldBase(name="required", data_type=DataType(type="str"), required=True),
            id="required",
        ),
        pytest.param(
            DataModelFieldBase(name="optional", data_type=DataType(type="str")),
            id="optional",
        ),
        pytest.param(
            DataModelFieldBase(
                name="stripped-default",
                data_type=DataType(type="str"),
                strip_default_none=True,
            ),
            id="stripped-default",
        ),
        pytest.param(
            DataclassDataModelField(
                name="explicit-field",
                data_type=DataType(type="str"),
                extras={"kw_only": True},
            ),
            id="explicit-field",
        ),
    ],
)
@pytest.mark.allow_direct_assert
def test_public_dataclass_field_assignment_helper_matches_neutral_capability(field: DataModelFieldBase) -> None:
    """Keep the compatibility wrapper behavior identical to the parser capability."""
    assert dataclass_has_field_assignment(field) is _has_field_assignment(field)
