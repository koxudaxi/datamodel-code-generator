"""Tests for Pydantic v2 config generation helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pytest

from datamodel_code_generator.model import DataModelFieldBase, pydantic_v2
from datamodel_code_generator.model.msgspec import Constraints as MsgspecConstraints
from datamodel_code_generator.model.pydantic_base import PatternConstraints
from datamodel_code_generator.model.pydantic_v2.base_model import BaseModel
from datamodel_code_generator.model.pydantic_v2.base_model import Constraints as PydanticV2Constraints
from datamodel_code_generator.model.pydantic_v2.dataclass import DataClass
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def _extra_template_data() -> defaultdict[str, dict[str, Any]]:
    return defaultdict(
        dict,
        {
            "Model": {
                "additionalProperties": False,
                "allow_population_by_field_name": True,
                "use_attribute_docstrings": True,
            }
        },
    )


def _field() -> DataModelFieldBase:
    return DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)


def _reference() -> Reference:
    return Reference(name="Model", path="Model")


@pytest.mark.allow_direct_assert
def test_config_dict_reexport_preserves_public_surface() -> None:
    """ConfigDict remains importable from the package for compatibility."""
    assert pydantic_v2.ConfigDict.__module__ == "datamodel_code_generator.model.pydantic_v2"
    assert "ConfigDict" not in pydantic_v2.__all__


@pytest.mark.allow_direct_assert
def test_base_model_config_key_order_with_multiple_shared_parameters() -> None:
    """BaseModel config generation keeps deterministic key ordering."""
    model = BaseModel(
        fields=[_field()],
        reference=_reference(),
        extra_template_data=_extra_template_data(),
    )

    config = model.extra_template_data["config"]
    assert isinstance(config, pydantic_v2.ConfigDict)
    assert list(config.dict(exclude_unset=True)) == ["extra", "populate_by_name", "use_attribute_docstrings"]
    assert (
        "model_config = ConfigDict(\n"
        "        extra='forbid',\n"
        "        populate_by_name=True,\n"
        "        use_attribute_docstrings=True,\n"
        "    )"
    ) in model.render()


@pytest.mark.allow_direct_assert
def test_dataclass_config_key_order_with_multiple_shared_parameters() -> None:
    """Dataclass config generation keeps deterministic key ordering."""
    model = DataClass(
        fields=[_field()],
        reference=_reference(),
        extra_template_data=_extra_template_data(),
    )

    config = model.extra_template_data["config"]
    assert isinstance(config, dict)
    assert list(config) == ["extra", "populate_by_name", "use_attribute_docstrings"]
    assert (
        "@dataclass(config=ConfigDict(extra='forbid', populate_by_name=True, use_attribute_docstrings=True))"
        in model.render()
    )


@pytest.mark.allow_direct_assert
def test_pattern_constraints_keep_leaf_specific_behavior() -> None:
    """Renamed pydantic constraints remain leaf-model specific."""
    assert list(PatternConstraints.model_fields)[-2:] == ["regex", "pattern"]
    assert list(PydanticV2Constraints.model_fields)[-2:] == ["regex", "pattern"]
    assert list(MsgspecConstraints.model_fields)[-2:] == ["regex", "pattern"]

    assert PydanticV2Constraints.model_validate({"minItems": 1}).model_dump(exclude_unset=True) == {"min_length": 1}
    assert MsgspecConstraints.model_validate({"minItems": 1}).model_dump(exclude_unset=True) == {"min_items": 1}
