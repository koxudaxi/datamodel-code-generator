"""Tests for output model capability resolution."""

from __future__ import annotations

import subprocess
import sys

import pytest

from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.config import JSONSchemaParserConfig
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.model.type_alias import TypeAliasTypeBackport
from datamodel_code_generator.parser._output_context import OutputModelContext
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

_OUTPUT_CAPABILITIES: dict[DataModelType, tuple[bool, bool, bool, bool]] = {
    DataModelType.PydanticV2BaseModel: (True, True, False, False),
    DataModelType.PydanticV2Dataclass: (True, True, False, False),
    DataModelType.DataclassesDataclass: (False, True, False, False),
    DataModelType.TypingTypedDict: (False, True, False, True),
    DataModelType.MsgspecStruct: (True, False, True, False),
}


@pytest.mark.allow_direct_assert
def test_output_capability_matrix_covers_every_data_model_type() -> None:
    """Require every output target to declare an intentional capability contract."""
    assert set(_OUTPUT_CAPABILITIES) == set(DataModelType)


@pytest.mark.parametrize(
    ("target_python_version"),
    [
        pytest.param(PythonVersion.PY_311, id="py311"),
        pytest.param(PythonVersion.PY_312, id="py312"),
    ],
)
@pytest.mark.parametrize(
    ("output_model_type", "expected_capabilities"),
    [
        pytest.param(output_model_type, capabilities, id=output_model_type.name)
        for output_model_type, capabilities in _OUTPUT_CAPABILITIES.items()
    ],
)
@pytest.mark.allow_direct_assert
def test_output_capabilities_for_standard_generation_types(
    output_model_type: DataModelType,
    expected_capabilities: tuple[bool, bool, bool, bool],
    target_python_version: PythonVersion,
) -> None:
    """Resolve stable capabilities for every canonical output target."""
    model_types = get_data_model_types(output_model_type, target_python_version=target_python_version)
    context = OutputModelContext.from_generation_types(
        data_model_type=model_types.data_model,
        data_model_root_type=model_types.root_model,
        data_model_field_type=model_types.field_model,
        data_type_manager_type=model_types.data_type_manager,
        configured_types_are_builtin=True,
        use_annotated=True,
    )
    (
        supports_annotated_constraints,
        supports_boolean_literals,
        requires_tagged_union_discriminator,
        requires_additional_properties_reference_classes,
    ) = expected_capabilities

    assert context.supports_annotated_constraints is supports_annotated_constraints
    assert context.supports_boolean_literals is supports_boolean_literals
    assert context.requires_tagged_union_discriminator is requires_tagged_union_discriminator
    assert context.requires_additional_properties_reference_classes is requires_additional_properties_reference_classes
    if not supports_annotated_constraints:
        return

    expected_nested_model_type = (
        TypeAliasTypeBackport if output_model_type is DataModelType.PydanticV2BaseModel else model_types.root_model
    )
    assert context.resolve_nested_constrained_model_type() is expected_nested_model_type


@pytest.mark.parametrize(
    ("use_type_alias", "use_root_model_type_alias"),
    [
        pytest.param(True, False, id="type-alias"),
        pytest.param(False, True, id="root-model-type-alias"),
    ],
)
@pytest.mark.parametrize(
    "target_python_version",
    [
        pytest.param(PythonVersion.PY_311, id="py311"),
        pytest.param(PythonVersion.PY_312, id="py312"),
    ],
)
@pytest.mark.allow_direct_assert
def test_pydantic_root_model_variants_preserve_annotated_constraint_capability(
    target_python_version: PythonVersion,
    use_type_alias: bool,
    use_root_model_type_alias: bool,
) -> None:
    """Accept every canonical Pydantic root representation without changing nested aliases."""
    model_types = get_data_model_types(
        DataModelType.PydanticV2BaseModel,
        target_python_version=target_python_version,
        use_type_alias=use_type_alias,
        use_root_model_type_alias=use_root_model_type_alias,
    )

    context = OutputModelContext.from_generation_types(
        data_model_type=model_types.data_model,
        data_model_root_type=model_types.root_model,
        data_model_field_type=model_types.field_model,
        data_type_manager_type=model_types.data_type_manager,
        configured_types_are_builtin=True,
        use_annotated=True,
    )

    assert context.supports_annotated_constraints is True
    assert context.resolve_nested_constrained_model_type() is TypeAliasTypeBackport


@pytest.mark.parametrize(
    ("use_annotated", "configured_types_are_builtin"),
    [
        pytest.param(False, True, id="annotated-disabled"),
        pytest.param(True, False, id="custom-generation-types"),
        pytest.param(False, False, id="both-disabled"),
    ],
)
@pytest.mark.allow_direct_assert
def test_annotated_constraint_capability_requires_both_gates(
    use_annotated: bool,
    configured_types_are_builtin: bool,
) -> None:
    """Keep optional and custom generator configurations on the legacy path."""
    model_types = get_data_model_types(
        DataModelType.PydanticV2BaseModel,
        target_python_version=PythonVersion.PY_311,
    )

    context = OutputModelContext.from_generation_types(
        data_model_type=model_types.data_model,
        data_model_root_type=model_types.root_model,
        data_model_field_type=model_types.field_model,
        data_type_manager_type=model_types.data_type_manager,
        configured_types_are_builtin=configured_types_are_builtin,
        use_annotated=use_annotated,
    )

    assert context.supports_annotated_constraints is False
    assert context.supports_boolean_literals is True
    assert context.requires_tagged_union_discriminator is False
    assert context.requires_additional_properties_reference_classes is False


@pytest.mark.parametrize(
    ("data_model_target", "root_target", "field_target", "manager_target"),
    [
        pytest.param(
            DataModelType.PydanticV2BaseModel,
            DataModelType.PydanticV2BaseModel,
            DataModelType.MsgspecStruct,
            DataModelType.PydanticV2BaseModel,
            id="msgspec-field-with-pydantic",
        ),
        pytest.param(
            DataModelType.PydanticV2BaseModel,
            DataModelType.PydanticV2BaseModel,
            DataModelType.PydanticV2BaseModel,
            DataModelType.MsgspecStruct,
            id="msgspec-manager-with-pydantic",
        ),
        pytest.param(
            DataModelType.MsgspecStruct,
            DataModelType.PydanticV2BaseModel,
            DataModelType.MsgspecStruct,
            DataModelType.MsgspecStruct,
            id="pydantic-root-with-msgspec",
        ),
        pytest.param(
            DataModelType.PydanticV2Dataclass,
            DataModelType.PydanticV2Dataclass,
            DataModelType.DataclassesDataclass,
            DataModelType.PydanticV2Dataclass,
            id="stdlib-field-with-pydantic-dataclass",
        ),
    ],
)
@pytest.mark.allow_direct_assert
def test_mixed_builtin_generation_contexts_fail_closed_for_annotated_constraints(
    data_model_target: DataModelType,
    root_target: DataModelType,
    field_target: DataModelType,
    manager_target: DataModelType,
) -> None:
    """Reject incompatible built-in component contexts without changing model semantics."""
    data_model_types = get_data_model_types(data_model_target, target_python_version=PythonVersion.PY_311)
    root_types = get_data_model_types(root_target, target_python_version=PythonVersion.PY_311)
    field_types = get_data_model_types(field_target, target_python_version=PythonVersion.PY_311)
    manager_types = get_data_model_types(manager_target, target_python_version=PythonVersion.PY_311)

    context = OutputModelContext.from_generation_types(
        data_model_type=data_model_types.data_model,
        data_model_root_type=root_types.root_model,
        data_model_field_type=field_types.field_model,
        data_type_manager_type=manager_types.data_type_manager,
        configured_types_are_builtin=True,
        use_annotated=True,
    )
    expected_capabilities = _OUTPUT_CAPABILITIES[data_model_target]

    assert context.supports_annotated_constraints is False
    assert context.supports_boolean_literals is expected_capabilities[1]
    assert context.requires_tagged_union_discriminator is expected_capabilities[2]
    assert context.requires_additional_properties_reference_classes is expected_capabilities[3]


@pytest.mark.parametrize(
    "custom_component",
    [
        pytest.param("data-model", id="data-model"),
        pytest.param("root-model", id="root-model"),
        pytest.param("field-model", id="field-model"),
        pytest.param("type-manager", id="type-manager"),
    ],
)
@pytest.mark.allow_direct_assert
def test_custom_generation_type_subclasses_fail_closed_for_annotated_constraints(custom_component: str) -> None:
    """Keep inherited custom generator classes on the parser's legacy path."""
    model_types = get_data_model_types(
        DataModelType.PydanticV2BaseModel,
        target_python_version=PythonVersion.PY_311,
    )
    data_model_type = model_types.data_model
    data_model_root_type = model_types.root_model
    data_model_field_type = model_types.field_model
    data_type_manager_type = model_types.data_type_manager

    match custom_component:
        case "data-model":
            data_model_type = type("CustomDataModel", (data_model_type,), {})
        case "root-model":
            data_model_root_type = type("CustomRootModel", (data_model_root_type,), {})
        case "field-model":
            data_model_field_type = type("CustomFieldModel", (data_model_field_type,), {})
        case "type-manager":
            data_type_manager_type = type("CustomTypeManager", (data_type_manager_type,), {})

    parser = JsonSchemaParser(
        "{}",
        config=JSONSchemaParserConfig(
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_model_field_type=data_model_field_type,
            data_type_manager_type=data_type_manager_type,
            field_constraints=True,
            use_annotated=True,
        ),
    )

    assert parser._configured_generation_types_are_builtin is False
    assert parser._output_model_context.supports_annotated_constraints is False
    assert parser._output_model_context.supports_boolean_literals is True
    assert parser._output_model_context.requires_tagged_union_discriminator is False
    assert parser._output_model_context.requires_additional_properties_reference_classes is False


@pytest.mark.allow_direct_assert
def test_output_context_import_does_not_load_output_backends() -> None:
    """Keep importing the context independent from concrete output backends."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import datamodel_code_generator.parser._output_context; "
                "print('datamodel_code_generator.model.pydantic_v2' in sys.modules); "
                "print('datamodel_code_generator.model.msgspec' in sys.modules)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == ["False", "False"]


@pytest.mark.allow_direct_assert
def test_pydantic_nested_constraint_alias_import_is_lazy() -> None:
    """Load the Pydantic compatibility alias only when resolution needs it."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "from datamodel_code_generator.model.pydantic_v2.base_model "
                "import BaseModel, DataModelField; "
                "from datamodel_code_generator.model.pydantic_v2.root_model import RootModel; "
                "from datamodel_code_generator.model.pydantic_v2.types import DataTypeManager; "
                "from datamodel_code_generator.parser._output_context import OutputModelContext; "
                "module_name = 'datamodel_code_generator.model.type_alias'; "
                "print(module_name in sys.modules); "
                "context = OutputModelContext.from_generation_types("
                "data_model_type=BaseModel, data_model_root_type=RootModel, "
                "data_model_field_type=DataModelField, data_type_manager_type=DataTypeManager, "
                "configured_types_are_builtin=True, use_annotated=True); "
                "print(module_name in sys.modules); "
                "print(context.resolve_nested_constrained_model_type().__name__); "
                "print(module_name in sys.modules)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == ["False", "False", "TypeAliasTypeBackport", "True"]
