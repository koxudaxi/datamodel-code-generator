"""Tests for output-owned dataclass field-ordering policies."""

from __future__ import annotations

import pytest

from datamodel_code_generator.model.base import UNDEFINED, DataModel
from datamodel_code_generator.model.dataclass import DataClass as StandardDataClass
from datamodel_code_generator.model.dataclass import DataModelField as DataclassDataModelField
from datamodel_code_generator.model.dataclass import has_field_assignment as has_dataclass_field_assignment
from datamodel_code_generator.model.msgspec import DataModelField as MsgspecDataModelField
from datamodel_code_generator.model.msgspec import Struct as MsgspecStruct
from datamodel_code_generator.model.msgspec import has_field_assignment as has_msgspec_field_assignment
from datamodel_code_generator.model.pydantic_v2.base_model import BaseModel as PydanticBaseModel
from datamodel_code_generator.model.pydantic_v2.base_model import DataModelField as PydanticBaseModelField
from datamodel_code_generator.model.pydantic_v2.dataclass import DataClass as PydanticDataClass
from datamodel_code_generator.model.pydantic_v2.dataclass import DataModelField as PydanticDataclassField
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


@pytest.mark.allow_direct_assert
def test_dataclass_ordering_capabilities_are_owned_by_output_models() -> None:
    """Output models should declare how inherited assignment conflicts are fixed."""

    class ExternalStruct(MsgspecStruct):
        """External msgspec backend inheriting the built-in ordering policy."""

    assert DataModel.REQUIRES_MODEL_LEVEL_KW_ONLY is False
    assert StandardDataClass.REQUIRES_MODEL_LEVEL_KW_ONLY is False
    assert PydanticDataClass.REQUIRES_MODEL_LEVEL_KW_ONLY is False
    assert MsgspecStruct.REQUIRES_MODEL_LEVEL_KW_ONLY is True
    assert ExternalStruct.REQUIRES_MODEL_LEVEL_KW_ONLY is True
    field = DataclassDataModelField(
        name="excluded",
        data_type=DataType(type="str"),
        required=True,
        extras={"init": False},
    )
    assert DataModel.FIELD_PARTICIPATES_IN_CONSTRUCTOR(field) is True
    assert StandardDataClass.FIELD_PARTICIPATES_IN_CONSTRUCTOR(field) is False
    assert PydanticDataClass.FIELD_PARTICIPATES_IN_CONSTRUCTOR(field) is True
    assert MsgspecStruct.FIELD_PARTICIPATES_IN_CONSTRUCTOR(field) is True
    assert ExternalStruct.FIELD_PARTICIPATES_IN_CONSTRUCTOR(field) is True
    assert DataModel.SUPPORTS_REQUIRED_INHERITED_FIELD_ASSIGNMENT is False
    assert StandardDataClass.SUPPORTS_REQUIRED_INHERITED_FIELD_ASSIGNMENT is True
    assert PydanticDataClass.SUPPORTS_REQUIRED_INHERITED_FIELD_ASSIGNMENT is True
    assert MsgspecStruct.SUPPORTS_REQUIRED_INHERITED_FIELD_ASSIGNMENT is False
    assert ExternalStruct.SUPPORTS_REQUIRED_INHERITED_FIELD_ASSIGNMENT is False
    assert MsgspecStruct.has_keyword_only_definition is not DataModel.has_keyword_only_definition
    assert MsgspecStruct.enable_model_keyword_only is not DataModel.enable_model_keyword_only
    assert ExternalStruct.has_keyword_only_definition is MsgspecStruct.has_keyword_only_definition
    assert ExternalStruct.enable_model_keyword_only is MsgspecStruct.enable_model_keyword_only
    assert PydanticBaseModel.FIELD_DEFAULT_CLASSIFIER is DataModel.FIELD_DEFAULT_CLASSIFIER
    assert StandardDataClass.FIELD_DEFAULT_CLASSIFIER is not DataModel.FIELD_DEFAULT_CLASSIFIER
    assert PydanticDataClass.FIELD_DEFAULT_CLASSIFIER is not DataModel.FIELD_DEFAULT_CLASSIFIER
    assert MsgspecStruct.FIELD_DEFAULT_CLASSIFIER is not DataModel.FIELD_DEFAULT_CLASSIFIER
    assert ExternalStruct.FIELD_DEFAULT_CLASSIFIER is MsgspecStruct.FIELD_DEFAULT_CLASSIFIER
    assert not hasattr(PydanticBaseModelField, "requires_dataclass_field_assignment")
    assert not hasattr(PydanticBaseModelField, "dataclass_field")
    assert hasattr(PydanticDataclassField, "requires_dataclass_field_assignment")
    assert hasattr(PydanticDataclassField, "dataclass_field")


@pytest.mark.allow_direct_assert
def test_dataclass_field_assignment_policy_keeps_legacy_helpers() -> None:
    """Model hooks should preserve both backend helper contracts."""
    required = DataclassDataModelField(name="required", data_type=DataType(type="str"), required=True)
    defaulted = DataclassDataModelField(
        name="defaulted",
        data_type=DataType(type="str"),
        default="value",
        required=False,
    )
    annotated_override = PydanticDataclassField(
        name="annotated_override",
        data_type=DataType(type="str"),
        required=True,
        use_annotated=True,
    )
    annotated_override.force_field_assignment()

    assert StandardDataClass.FIELD_ASSIGNMENT_CHECKER(required) is has_dataclass_field_assignment(required) is False
    assert StandardDataClass.FIELD_ASSIGNMENT_CHECKER(defaulted) is has_dataclass_field_assignment(defaulted) is True
    assert PydanticDataClass.FIELD_ASSIGNMENT_CHECKER(annotated_override) is True
    assert MsgspecStruct.FIELD_ASSIGNMENT_CHECKER(required) is has_msgspec_field_assignment(required) is False
    assert MsgspecStruct.FIELD_ASSIGNMENT_CHECKER(defaulted) is has_msgspec_field_assignment(defaulted) is True


@pytest.mark.allow_direct_assert
def test_constructor_default_classifiers_are_output_owned() -> None:
    """Classifiers should expose semantics without leaking rendered syntax to the parser."""
    required = DataclassDataModelField(name="required", data_type=DataType(type="str"), required=True)
    factory = DataclassDataModelField(
        name="factory",
        data_type=DataType(type="str"),
        required=False,
        extras={"default_factory": "list"},
    )
    undefined = DataclassDataModelField(
        name="undefined",
        data_type=DataType(type="str"),
        required=False,
        default=UNDEFINED,
    )
    defaulted = DataclassDataModelField(
        name="defaulted",
        data_type=DataType(type="str"),
        required=False,
        default="value",
    )
    metadata_only = MsgspecDataModelField(
        name="metadata",
        alias="source",
        data_type=DataType(type="str"),
        required=False,
        default=UNDEFINED,
    )

    assert DataModel.FIELD_DEFAULT_CLASSIFIER(required) == (False, False)
    assert DataModel.FIELD_DEFAULT_CLASSIFIER(factory) == (True, False)
    assert DataModel.FIELD_DEFAULT_CLASSIFIER(undefined) == (False, False)
    assert DataModel.FIELD_DEFAULT_CLASSIFIER(defaulted) == (True, True)
    assert MsgspecStruct.FIELD_DEFAULT_CLASSIFIER(metadata_only) == (False, False)


@pytest.mark.allow_direct_assert
def test_dataclass_keyword_only_definition_uses_model_owned_metadata() -> None:
    """Each backend should interpret only its own keyword-only metadata."""
    data_class = StandardDataClass(
        fields=[],
        reference=Reference(path="Model", original_name="Model", name="Model"),
        dataclass_arguments={"kw_only": True},
    )
    pydantic_model = PydanticBaseModel(
        fields=[],
        reference=Reference(path="PydanticModel", original_name="PydanticModel", name="PydanticModel"),
    )
    pydantic_data_class = PydanticDataClass(
        fields=[],
        reference=Reference(
            path="PydanticDataClass",
            original_name="PydanticDataClass",
            name="PydanticDataClass",
        ),
        dataclass_arguments={"kw_only": True},
    )
    struct = MsgspecStruct(
        fields=[],
        reference=Reference(path="Struct", original_name="Struct", name="Struct"),
    )

    assert data_class.has_keyword_only_definition() is True
    assert pydantic_model.has_keyword_only_definition() is False
    assert pydantic_data_class.has_keyword_only_definition() is True
    assert struct.has_keyword_only_definition() is False

    struct.add_base_class_kwarg("tag", "'kind'")
    struct.enable_model_keyword_only()
    struct.enable_model_keyword_only()

    assert struct.has_keyword_only_definition() is True
    assert struct.extra_template_data["base_class_kwargs"] == {"tag": "'kind'", "kw_only": "True"}

    struct.extra_template_data["base_class_kwargs"]["kw_only"] = True

    assert struct.has_keyword_only_definition() is True
