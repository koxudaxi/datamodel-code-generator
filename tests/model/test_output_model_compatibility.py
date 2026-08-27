"""Tests for output-model compatibility capabilities."""

from __future__ import annotations

import pytest

from datamodel_code_generator import DataModelType
from datamodel_code_generator.enums import _get_output_model_family, _OutputModelFamily

_OUTPUT_MODEL_FAMILIES: dict[DataModelType, _OutputModelFamily] = {
    DataModelType.PydanticV2BaseModel: _OutputModelFamily.PYDANTIC,
    DataModelType.PydanticV2Dataclass: _OutputModelFamily.PYDANTIC,
    DataModelType.DataclassesDataclass: _OutputModelFamily.DATACLASS,
    DataModelType.TypingTypedDict: _OutputModelFamily.TYPEDDICT,
    DataModelType.MsgspecStruct: _OutputModelFamily.MSGSPEC,
}


@pytest.mark.allow_direct_assert
def test_output_model_compatibility_matrix_covers_every_data_model_type() -> None:
    """Require each output target to declare input-model reuse compatibility."""
    assert set(_OUTPUT_MODEL_FAMILIES) == set(DataModelType)


@pytest.mark.parametrize(
    ("data_model_type", "expected_family"),
    [
        pytest.param(data_model_type, family, id=data_model_type.name)
        for data_model_type, family in _OUTPUT_MODEL_FAMILIES.items()
    ],
)
@pytest.mark.allow_direct_assert
def test_output_model_compatibility_matches_the_declared_contract(
    data_model_type: DataModelType,
    expected_family: _OutputModelFamily,
) -> None:
    """Resolve compatibility through model selection without input-model policy."""
    assert _get_output_model_family(data_model_type) is expected_family


@pytest.mark.allow_direct_assert
def test_default_output_model_compatibility_is_pydantic() -> None:
    """Keep omitted output selection compatible with the default Pydantic output."""
    assert _get_output_model_family(None) is _OutputModelFamily.PYDANTIC
