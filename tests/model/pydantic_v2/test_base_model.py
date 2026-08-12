"""Tests for Pydantic v2 BaseModel generation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from datamodel_code_generator import DataModelType
from datamodel_code_generator.config import JSONSchemaParserConfig
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.model.pydantic_v2 import base_model as pydantic_v2_base_model
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


def _base_model(*, fields: list[DataModelField] | None = None, **kwargs: object) -> BaseModel:
    return BaseModel(
        fields=fields or [],
        reference=Reference(name="Model", path="#/Model"),
        **kwargs,
    )


@pytest.mark.allow_direct_assert
def test_builtin_base_model_native_renderer_matches_jinja() -> None:
    """Match the built-in template across standard class and field branches."""
    models = [
        _base_model(),
        _base_model(description="Model description", decorators=["@first", "@second()"]),
        _base_model(
            fields=[
                DataModelField(name="required", required=True, data_type=DataType(type="str")),
                DataModelField(name="aliased", alias="wire-name", data_type=DataType(type="str")),
                DataModelField(
                    name="annotated",
                    default="value",
                    data_type=DataType(type="str"),
                    constraints=Constraints(minLength=1),
                    use_annotated=True,
                ),
                DataModelField(
                    name="stripped",
                    default=None,
                    data_type=DataType(type="str"),
                    strip_default_none=True,
                ),
                DataModelField(
                    name="optional",
                    default=None,
                    data_type=DataType(type="str", is_optional=True),
                    strip_default_none=True,
                ),
                DataModelField(
                    name="documented",
                    required=True,
                    data_type=DataType(type="int"),
                    extras={"description": "Multi-line field\ndescription"},
                    use_inline_field_description=True,
                ),
                DataModelField(
                    name="inline",
                    required=True,
                    data_type=DataType(type="float"),
                    extras={"description": "Inline field description"},
                    use_inline_field_description=True,
                ),
                DataModelField(
                    name="last",
                    required=True,
                    data_type=DataType(type="bool"),
                    extras={"description": "Multi-line\ndescription"},
                    use_field_description=True,
                ),
            ],
        ),
    ]

    for model in models:
        rendered = model.render(class_name="Renamed")
        expected = super(BaseModel, model).render(class_name="Renamed")
        assert rendered == expected


@pytest.mark.allow_direct_assert
def test_builtin_base_model_native_renderer_falls_back_for_template_features() -> None:
    """Leave template-only features and duplicate render arguments to Jinja."""
    for key, value in (
        ("class_body_lines", ["marker = True"]),
        ("config", True),
        ("prepared_validators", [{"fields_str": "'value'"}]),
        ("schema_runtime_validation", _schema_runtime_validation()),
        ("schema_runtime_validation_use_base", True),
    ):
        model = _base_model()
        model.extra_template_data[key] = value
        assert model._render_builtin(None) is None

    model = _base_model()
    model.methods.append("def method(self) -> None: ...")
    assert model._render_builtin(None) is None

    model = _base_model()
    model.extra_template_data["comment"] = None
    assert model._render_builtin(None) is None

    model = _base_model()
    model.extra_template_data["class_name"] = "Duplicate"
    assert model._render_builtin(None) is None
    with pytest.raises(TypeError, match="class_name"):
        model.render()


@pytest.mark.allow_direct_assert
def test_builtin_base_model_native_renderer_falls_back_for_nonstandard_models(tmp_path: Path) -> None:
    """Keep subclasses, custom fields, typed extras, and custom templates on Jinja."""

    class CustomBaseModel(BaseModel):
        pass

    class CustomDataModelField(DataModelField):
        pass

    subclass = CustomBaseModel(fields=[], reference=Reference(name="Subclass", path="#/Subclass"))
    assert subclass._render_builtin(None) is None

    cached_template = _base_model()
    _ = cached_template.template
    assert cached_template._render_builtin(None) is None

    overridden_render = _base_model()
    overridden_render._render = lambda *_args, **_kwargs: "overridden"  # type: ignore[method-assign]
    assert overridden_render._render_builtin(None) is None
    assert overridden_render.render() == "overridden"

    custom_field = _base_model(
        fields=[CustomDataModelField(name="value", required=True, data_type=DataType(type="str"))]
    )
    assert custom_field._render_builtin(None) is None

    typed_extra = _base_model(
        fields=[DataModelField(name="__pydantic_extra__", required=True, data_type=DataType(type="str"))]
    )
    assert typed_extra._render_builtin(None) is None

    changed_path = _base_model()
    changed_path.__dict__["template_file_path"] = Path("different/BaseModel.jinja2")
    assert changed_path._render_builtin(None) is None

    custom_template = tmp_path / "BaseModel.jinja2"
    custom_template.write_text("custom {{ class_name }}", encoding="utf-8")
    custom = BaseModel(
        fields=[],
        reference=Reference(name="Custom", path="#/Custom"),
        custom_template_dir=tmp_path,
    )
    assert custom._render_builtin(None) is None
    assert custom.render() == "custom Custom"


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
    """Preserve dumps and rendering when the parser supplies normalized values."""
    values = {
        "name": "item_name",
        "default": "'item'",
        "required": True,
        "alias": "item-name",
        "data_type": DataType(type="str"),
        "extras": {},
        "use_annotated": True,
        "use_missing_sentinel": True,
    }
    validated = DataModelField(**values)
    constructed = _construct_parser_simple_field(**{**values, "data_type": DataType(type="str")})

    assert constructed.model_dump() == validated.model_dump()
    assert constructed.model_dump(exclude_unset=True) == validated.model_dump(exclude_unset=True)
    assert constructed.__pydantic_fields_set__ == validated.__pydantic_fields_set__
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
def test_parser_simple_field_unknown_layout_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use validation when a future Pydantic release changes instance layout."""
    monkeypatch.setattr(pydantic_v2_base_model, "_PARSER_SIMPLE_FIELD_LAYOUT_SUPPORTED", False)

    field = _construct_parser_simple_field(name="value", data_type=DataType(type="str"))

    assert field == DataModelField(name="value", data_type=DataType(type="str"))


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
