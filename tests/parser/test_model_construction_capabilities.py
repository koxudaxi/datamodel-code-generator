"""Tests for output model construction capabilities."""

from __future__ import annotations

import ast
import inspect
from typing import TYPE_CHECKING, ClassVar, cast

import pytest

from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.model import base as model_base_module
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.model.base import DataModel
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from datamodel_code_generator.reference import ModelType, Reference

if TYPE_CHECKING:
    from datamodel_code_generator.model import DataModelSet

_CONSTRUCTION_CAPABILITIES: dict[DataModelType, tuple[ModelType | None, bool]] = {
    DataModelType.PydanticV2BaseModel: (ModelType.PYDANTIC, False),
    DataModelType.PydanticV2Dataclass: (None, True),
    DataModelType.DataclassesDataclass: (None, True),
    DataModelType.TypingTypedDict: (None, False),
    DataModelType.MsgspecStruct: (ModelType.MSGSPEC, False),
}


class _CustomDataModel(DataModel):
    """Custom model without an output-specific construction contract."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "TypedDict.jinja2"


def _parser(model_types: DataModelSet, *, data_model_type: type[DataModel] | None = None) -> JsonSchemaParser:
    """Create a parser configured with the supplied output model set."""
    return JsonSchemaParser(
        "",
        data_model_type=data_model_type or model_types.data_model,
        data_model_root_type=model_types.root_model,
        data_model_field_type=model_types.field_model,
        data_type_manager_type=model_types.data_type_manager,
    )


@pytest.mark.allow_direct_assert
def test_construction_capability_matrix_covers_every_data_model_type() -> None:
    """Require each canonical output target to keep an intentional contract."""
    assert set(_CONSTRUCTION_CAPABILITIES) == set(DataModelType)


@pytest.mark.allow_direct_assert
def test_generic_model_keeps_reference_import_boundary() -> None:
    """Prevent field-name policy from adding a generic-to-reference import edge."""
    reference_imports = {
        alias.name
        for node in ast.walk(ast.parse(inspect.getsource(model_base_module)))
        if isinstance(node, ast.ImportFrom) and node.module == "datamodel_code_generator.reference"
        for alias in node.names
    }

    assert reference_imports == {"Reference", "_BaseModel"}
    assert "ModelType" not in vars(model_base_module)


@pytest.mark.parametrize(
    ("output_model_type", "expected"),
    [
        pytest.param(output_model_type, capabilities, id=output_model_type.name)
        for output_model_type, capabilities in _CONSTRUCTION_CAPABILITIES.items()
    ],
)
@pytest.mark.allow_direct_assert
def test_standard_model_construction_capabilities(
    output_model_type: DataModelType,
    expected: tuple[ModelType | None, bool],
) -> None:
    """Resolve field-name and dataclass construction behavior without backend inspection."""
    model_types = get_data_model_types(output_model_type, target_python_version=PythonVersion.PY_311)
    declared_model_type, uses_dataclass_arguments = expected
    parser = _parser(model_types)

    assert model_types.data_model.FIELD_NAME_MODEL_TYPE is declared_model_type
    assert model_types.data_model.USES_DATACLASS_ARGUMENTS is uses_dataclass_arguments
    assert parser.field_name_model_type is (declared_model_type or ModelType.CLASS)


@pytest.mark.parametrize(
    ("output_model_type", "expected"),
    [
        pytest.param(output_model_type, capabilities, id=output_model_type.name)
        for output_model_type, capabilities in _CONSTRUCTION_CAPABILITIES.items()
    ],
)
@pytest.mark.allow_direct_assert
def test_external_model_subclasses_inherit_construction_capabilities(
    output_model_type: DataModelType,
    expected: tuple[ModelType | None, bool],
) -> None:
    """Preserve MRO-based behavior for external subclasses of built-in outputs."""
    model_types = get_data_model_types(output_model_type, target_python_version=PythonVersion.PY_311)
    external_model_type = cast("type[DataModel]", type("ExternalModel", (model_types.data_model,), {}))
    declared_model_type, uses_dataclass_arguments = expected
    parser = _parser(model_types, data_model_type=external_model_type)
    parser.dataclass_arguments = {"slots": True}

    result = parser._create_data_model(
        reference=Reference(path="ExternalModel", name="ExternalModel"),
        fields=[],
        dataclass_arguments={"order": True},
    )

    assert external_model_type.FIELD_NAME_MODEL_TYPE is declared_model_type
    assert external_model_type.USES_DATACLASS_ARGUMENTS is uses_dataclass_arguments
    assert parser.field_name_model_type is (declared_model_type or ModelType.CLASS)
    assert type(result) is external_model_type
    assert result.dataclass_arguments == ({"order": True} if uses_dataclass_arguments else {})


@pytest.mark.allow_direct_assert
def test_custom_model_construction_capabilities_fail_closed() -> None:
    """Keep arbitrary custom models on ordinary class and constructor behavior."""
    model_types = get_data_model_types(DataModelType.TypingTypedDict, target_python_version=PythonVersion.PY_311)
    parser = _parser(model_types, data_model_type=_CustomDataModel)

    result = parser._create_data_model(
        reference=Reference(path="CustomModel", name="CustomModel"),
        fields=[],
        dataclass_arguments={"frozen": True},
    )

    assert _CustomDataModel.FIELD_NAME_MODEL_TYPE is None
    assert parser.field_name_model_type is ModelType.CLASS
    assert result.dataclass_arguments == {}
