"""Tests for dataclass model field generation."""

from __future__ import annotations

from collections import UserDict, UserList

import pytest

from datamodel_code_generator.model.base import DataModel, TemplateBase
from datamodel_code_generator.model.dataclass import DataClass, DataModelField
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def _dataclass_model(**kwargs: object) -> DataClass:
    return DataClass(
        reference=Reference(path="Model", name="Model"),
        fields=[DataModelField(name="value", data_type=DataType(type="str"), required=True)],
        **kwargs,
    )


@pytest.mark.parametrize(
    "dataclass_arguments",
    [
        pytest.param({"slots": "x" * 100}, id="long-string"),
        pytest.param({"slots": list(range(50))}, id="long-list"),
        pytest.param({"slots": {"values": list(range(50))}}, id="long-dict"),
    ],
)
def test_dataclass_builtin_renderer_keeps_public_argument_format(dataclass_arguments: dict[str, object]) -> None:
    """Match Jinja pprint output for direct public construction values."""
    model = _dataclass_model(dataclass_arguments=dataclass_arguments)

    assert model.render() == DataModel.render(model)


@pytest.mark.parametrize(
    "model",
    [
        pytest.param(
            DataClass(reference=Reference(path="Empty", name="Empty"), fields=[]),
            id="empty",
        ),
        pytest.param(
            DataClass(reference=Reference(path="Described", name="Described"), fields=[], description="model doc"),
            id="model-description",
        ),
        pytest.param(
            DataClass(
                reference=Reference(path="Assigned", name="Assigned"),
                fields=[
                    DataModelField(
                        name="assigned",
                        data_type=DataType(type="str"),
                        extras={"repr": False},
                    ),
                ],
            ),
            id="field-assignment",
        ),
        pytest.param(
            DataClass(
                reference=Reference(path="FieldDoc", name="FieldDoc"),
                fields=[
                    DataModelField(
                        name="documented",
                        data_type=DataType(type="str"),
                        required=True,
                        use_inline_field_description=True,
                        extras={"description": "line one\nline two"},
                    ),
                    DataModelField(name="tail", data_type=DataType(type="str"), required=True),
                ],
            ),
            id="multiline-field-docstring",
        ),
        pytest.param(
            DataClass(
                reference=Reference(path="InlineDoc", name="InlineDoc"),
                fields=[
                    DataModelField(
                        name="documented",
                        data_type=DataType(type="str"),
                        required=True,
                        use_inline_field_description=True,
                        extras={"description": "inline field doc"},
                    ),
                    DataModelField(name="tail", data_type=DataType(type="str"), required=True),
                ],
            ),
            id="inline-field-docstring",
        ),
        pytest.param(
            DataClass(
                reference=Reference(path="LastInlineDoc", name="LastInlineDoc"),
                fields=[
                    DataModelField(
                        name="documented",
                        data_type=DataType(type="str"),
                        required=True,
                        use_inline_field_description=True,
                        extras={"description": "last inline field doc"},
                    ),
                ],
            ),
            id="last-inline-field-docstring",
        ),
    ],
)
def test_dataclass_builtin_renderer_keeps_docstring_layout(model: DataClass) -> None:
    """Match the built-in template's empty and docstring layouts."""
    assert model.render() == DataModel.render(model)


@pytest.mark.parametrize("collision", sorted({"base_class", "class_name", "fields", "path"}))
def test_dataclass_builtin_renderer_falls_back_for_render_key_collision(collision: str) -> None:
    """Preserve Jinja's duplicate render-argument error behavior."""
    model = _dataclass_model()
    model.extra_template_data[collision] = "duplicate"

    with pytest.raises(TypeError) as expected:
        DataModel.render(model)
    with pytest.raises(TypeError) as actual:
        model.render()

    assert str(actual.value) == str(expected.value)


def test_dataclass_builtin_renderer_falls_back_for_non_string_template_key() -> None:
    """Preserve Jinja's non-string keyword error."""
    model = _dataclass_model()
    model.extra_template_data[1] = "invalid"

    with pytest.raises(TypeError) as expected:
        DataModel.render(model)
    with pytest.raises(TypeError) as actual:
        model.render()

    assert str(actual.value) == str(expected.value)


def test_dataclass_builtin_renderer_falls_back_for_non_string_decorator() -> None:
    """Preserve Jinja's public decorator stringification."""
    model = _dataclass_model()
    model.decorators = [1]  # type: ignore[list-item]

    assert model.render() == DataModel.render(model)


@pytest.mark.parametrize("attribute", ["decorators", "extra_template_data", "fields"])
def test_dataclass_builtin_renderer_falls_back_for_custom_containers(attribute: str) -> None:
    """Avoid consuming stateful public container subclasses on the native path."""

    class CustomList(UserList[object]):
        pass

    class CustomDict(UserDict[object, object]):
        pass

    model = _dataclass_model()
    match attribute:
        case "decorators":
            model.decorators = CustomList(model.decorators)  # type: ignore[assignment]
        case "extra_template_data":
            model.extra_template_data = CustomDict(model.extra_template_data)  # type: ignore[assignment]
        case _:
            model.fields = CustomList(model.fields)  # type: ignore[assignment]

    assert model.render() == DataModel.render(model)


def test_dataclass_builtin_renderer_falls_back_for_model_and_field_subclasses() -> None:
    """Keep public subclass hooks on the Jinja renderer."""

    class CustomDataClass(DataClass):
        pass

    class CustomDataModelField(DataModelField):
        pass

    model = CustomDataClass(reference=Reference(path="Custom", name="Custom"), fields=[])
    field_model = DataClass(
        reference=Reference(path="FieldCustom", name="FieldCustom"),
        fields=[CustomDataModelField(name="value", data_type=DataType(type="str"), required=True)],
    )

    assert model.render() == DataModel.render(model)
    assert field_model.render() == DataModel.render(field_model)


def test_dataclass_builtin_renderer_falls_back_for_instance_render_overrides() -> None:
    """Respect public instance-level template and renderer overrides."""
    model = _dataclass_model()
    model.__dict__["_render"] = lambda *args, **kwargs: "overridden"  # noqa: ARG005

    assert model.render() == "overridden"


def test_dataclass_builtin_renderer_keeps_fast_path_after_template_access() -> None:
    """Keep standard cached template access independent from render dispatch."""
    model = _dataclass_model()
    cached_template = model.template

    assert model.__dict__["template"] is cached_template
    assert model._render_builtin(None) == DataModel.render(model)


def test_dataclass_builtin_renderer_falls_back_for_instance_template_override() -> None:
    """Respect a caller-owned instance template override."""

    class CustomTemplate:
        @staticmethod
        def render(*_args: object, **_kwargs: object) -> str:
            return "instance-template-overridden"

    model = _dataclass_model()
    model.__dict__["template"] = CustomTemplate()

    assert model.render() == "instance-template-overridden"


def test_dataclass_builtin_renderer_falls_back_for_class_render_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Respect class-level renderer replacement."""
    model = _dataclass_model()
    monkeypatch.setattr(DataClass, "_render", lambda *_args, **_kwargs: "class-overridden")

    assert model.render() == "class-overridden"


def test_dataclass_builtin_renderer_falls_back_for_class_template_path_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Respect class-level template path replacement."""
    model = _dataclass_model()
    monkeypatch.setattr(DataClass, "TEMPLATE_FILE_PATH", "missing-dataclass.jinja2")

    with pytest.raises(Exception) as expected:  # noqa: PT011
        DataModel.render(model)
    with pytest.raises(Exception) as actual:  # noqa: PT011
        model.render()

    assert type(actual.value) is type(expected.value)
    assert str(actual.value) == str(expected.value)


def test_dataclass_builtin_renderer_falls_back_for_class_template_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Respect class-level template descriptor replacement."""

    class CustomTemplate:
        @staticmethod
        def render(*_args: object, **_kwargs: object) -> str:
            return "template-overridden"

    model = _dataclass_model()
    monkeypatch.setattr(DataClass, "template", property(lambda _self: CustomTemplate()))

    assert model.render() == DataModel.render(model) == "template-overridden"


@pytest.mark.parametrize("owner", [DataModel, DataClass])
def test_dataclass_builtin_renderer_falls_back_for_parent_template_override(
    owner: type[DataModel],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Respect inherited template-dispatch descriptor replacement."""

    class CustomTemplate:
        @staticmethod
        def render(*_args: object, **_kwargs: object) -> str:
            return "parent-template-overridden"

    model = _dataclass_model()
    monkeypatch.setattr(owner, "template", property(lambda _self: CustomTemplate()))

    assert model.render() == "parent-template-overridden"


def test_dataclass_builtin_renderer_falls_back_for_parent_render_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Respect inherited public model-render replacement."""
    model = _dataclass_model()
    monkeypatch.setattr(DataModel, "render", lambda *_args, **_kwargs: "parent-render-overridden")

    assert model.render() == "parent-render-overridden"


def test_dataclass_builtin_renderer_falls_back_for_parent_internal_render_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Respect inherited low-level renderer replacement."""
    model = _dataclass_model()
    monkeypatch.setattr(TemplateBase, "_render", lambda *_args, **_kwargs: "parent-internal-overridden")

    assert model.render() == "parent-internal-overridden"


def test_dataclass_builtin_renderer_falls_back_for_description_policy_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Respect class-level description rendering policy replacement."""
    model = DataClass(reference=Reference(path="Model", name="Model"), fields=[], description="plain description")
    monkeypatch.setattr(DataClass, "FORMAT_DESCRIPTION_AS_DOCSTRING", False)

    assert model.render() == DataModel.render(model)
    assert '"""' not in model.render()


def test_dataclass_builtin_renderer_falls_back_for_rendered_fields_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Respect class-level rendered-fields descriptor replacement."""
    model = _dataclass_model()
    monkeypatch.setattr(DataClass, "rendered_fields", property(lambda _self: []))

    assert model.render() == DataModel.render(model)
    assert "value: str" not in model.render()


def test_dataclass_builtin_renderer_falls_back_for_field_property_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Respect class-level field rendering replacement."""
    model = _dataclass_model()
    monkeypatch.setattr(DataModelField, "field", property(lambda _self: "custom_field()"))

    assert model.render() == DataModel.render(model)
    assert "custom_field()" in model.render()


def test_dataclass_builtin_renderer_falls_back_for_field_docstring_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Respect class-level field docstring replacement."""
    model = _dataclass_model()
    monkeypatch.setattr(DataModelField, "docstring", property(lambda _self: "custom docstring"))

    assert model.render() == DataModel.render(model)
    assert "custom docstring" in model.render()


def test_data_model_field_process_const() -> None:
    """Test process_const method functionality."""
    field = DataModelField(name="test_field", data_type=DataType(type="str"), required=True, extras={"const": "v1"})

    field.process_const()

    assert field.const is True
    assert field.nullable is False
    assert field.data_type.literals == ["v1"]
    assert field.default == "v1"


def test_data_model_field_process_const_no_const() -> None:
    """Test process_const when no const is in extras."""
    field = DataModelField(name="test_field", data_type=DataType(type="str"), required=True, extras={})

    original_nullable = field.nullable
    original_default = field.default
    original_const = field.const

    field.process_const()

    assert field.const == original_const
    assert field.nullable == original_nullable
    assert field.default == original_default


@pytest.mark.parametrize(
    ("extras", "strip_default_none", "expected"),
    [
        pytest.param({"repr": False}, False, "field(repr=False, default=None)", id="metadata"),
        pytest.param({"kw_only": True}, False, "field(kw_only=True, default=None)", id="keyword-only"),
        pytest.param({"repr": False}, True, "field(repr=False)", id="stripped-metadata"),
        pytest.param({"init": False}, False, "field(init=False, default=None)", id="init-disabled"),
        pytest.param({"init": False}, True, "field(init=False, default=None)", id="stripped-init-disabled"),
    ],
)
def test_data_model_field_optional_none_preserves_field_semantics(
    extras: dict[str, bool],
    strip_default_none: bool,
    expected: str,
) -> None:
    """Preserve optional defaults whenever field metadata bypasses the template default."""
    field = DataModelField(
        name="value",
        data_type=DataType(type="str"),
        default=None,
        required=False,
        strip_default_none=strip_default_none,
        extras=extras,
    )

    assert str(field) == expected


def test_data_model_field_init_false_preserves_default_factory() -> None:
    """Do not add a competing None default when init-disabled fields use a factory."""
    field = DataModelField(
        name="value",
        data_type=DataType(type="list"),
        default=None,
        required=False,
        extras={"default_factory": "list", "init": False},
    )

    assert str(field) == "field(default_factory=list, init=False)"


def test_data_model_field_init_false_prefers_computed_nested_default_factory() -> None:
    """A computed nested factory must replace the otherwise necessary None default."""
    nested_reference = Reference(path="Nested", original_name="Nested", name="Nested")
    DataClass(reference=nested_reference, fields=[])
    field = DataModelField(
        name="value",
        data_type=DataType(reference=nested_reference),
        default=None,
        required=False,
        extras={"init": False},
        use_default_factory_for_optional_nested_models=True,
    )

    assert str(field) == "field(init=False, default_factory=Nested)"


def test_data_model_field_renders_nested_mapping_default_as_constructor() -> None:
    """Build typed nested defaults while preserving renamed constructor fields."""
    nested_reference = Reference(path="Nested", original_name="Nested", name="Nested")
    DataClass(
        reference=nested_reference,
        fields=[
            DataModelField(
                name="renamed",
                original_name="external-name",
                data_type=DataType(type="str"),
            ),
        ],
    )
    field = DataModelField(
        name="nested",
        data_type=DataType(reference=nested_reference),
        default={"external-name": "preset"},
    )

    assert str(field) == "field(default_factory=lambda: Nested(renamed='preset'))"

    field.default = {"unknown": "preset"}

    assert str(field) == "field(default_factory=lambda: {'unknown': 'preset'})"

    mapping_union_field = DataModelField(
        name="mapping",
        data_type=DataType(data_types=[DataType(is_dict=True), DataType(reference=nested_reference)]),
        default={"external-name": "preset"},
    )

    assert str(mapping_union_field) == "field(default_factory=lambda: {'external-name': 'preset'})"


def test_data_model_field_nested_constructor_requires_all_signature_arguments() -> None:
    """Only build nested dataclasses whose constructor arguments are satisfied."""
    leaf_reference = Reference(path="Leaf", original_name="Leaf", name="Leaf")
    DataClass(reference=leaf_reference, fields=[])
    nested_reference = Reference(path="Nested", original_name="Nested", name="Nested")
    DataClass(
        reference=nested_reference,
        fields=[
            DataModelField(
                name="required_value",
                data_type=DataType(type="str"),
                required=True,
            ),
            DataModelField(
                name="defaulted_value",
                data_type=DataType(type="str"),
                default="fallback",
                required=True,
                has_default=True,
                use_default_with_required=True,
            ),
            DataModelField(
                name="not_initialized",
                data_type=DataType(type="str"),
                required=True,
                extras={"init": False},
            ),
            DataModelField(
                name="stripped_none",
                data_type=DataType(type="str"),
                default=None,
                strip_default_none=True,
            ),
            DataModelField(
                name="factory_value",
                data_type=DataType(type="list"),
                extras={"default_factory": "list"},
            ),
            DataModelField(
                name="child",
                data_type=DataType(reference=leaf_reference),
                default={},
            ),
        ],
    )
    field = DataModelField(
        name="nested",
        data_type=DataType(reference=nested_reference),
        default={"required_value": "preset", "stripped_none": None},
    )

    assert str(field) == "field(default_factory=lambda: Nested(required_value='preset', stripped_none=None))"

    field.default = {}
    assert str(field) == "field(default_factory=dict)"

    field.default = {
        "required_value": "preset",
        "stripped_none": None,
        "not_initialized": "invalid",
    }
    assert str(field) == (
        "field(default_factory=lambda: "
        "{'required_value': 'preset', 'stripped_none': None, 'not_initialized': 'invalid'})"
    )


def test_data_model_field_nested_constructor_uses_effective_inherited_fields() -> None:
    """Inherited required fields and child overrides share the C3 field policy."""
    base_reference = Reference(path="Base", original_name="Base", name="Base")
    DataClass(
        reference=base_reference,
        fields=[
            DataModelField(
                name="inherited",
                data_type=DataType(type="str"),
                required=True,
            ),
        ],
    )
    child_reference = Reference(path="Child", original_name="Child", name="Child")
    DataClass(reference=child_reference, fields=[], base_classes=[base_reference])
    field = DataModelField(
        name="nested",
        data_type=DataType(reference=child_reference),
        default={},
    )

    assert str(field) == "field(default_factory=dict)"

    overridden_reference = Reference(path="Overridden", original_name="Overridden", name="Overridden")
    DataClass(
        reference=overridden_reference,
        fields=[
            DataModelField(
                name="inherited",
                data_type=DataType(type="str"),
                default="fallback",
            ),
        ],
        base_classes=[base_reference],
    )
    field.data_type = DataType(reference=overridden_reference)

    assert str(field) == "field(default_factory=lambda: Overridden())"


def test_data_model_field_nested_constructor_handles_name_collisions_and_ambiguity() -> None:
    """Original names win collisions, while multiple matching models keep raw mappings."""
    first_reference = Reference(path="First", original_name="First", name="First")
    DataClass(
        reference=first_reference,
        fields=[
            DataModelField(
                name="generated",
                original_name="wire",
                data_type=DataType(type="str"),
                required=True,
            ),
            DataModelField(
                name="wire",
                original_name="other",
                data_type=DataType(type="str"),
                default="fallback",
            ),
        ],
    )
    field = DataModelField(
        name="nested",
        data_type=DataType(reference=first_reference),
        default={"wire": "preset"},
    )

    assert str(field) == "field(default_factory=lambda: First(generated='preset'))"

    field.default = {"generated": "current", "wire": "original"}

    assert str(field) == "field(default_factory=lambda: {'generated': 'current', 'wire': 'original'})"

    second_reference = Reference(path="Second", original_name="Second", name="Second")
    DataClass(
        reference=second_reference,
        fields=[
            DataModelField(
                name="wire",
                data_type=DataType(type="str"),
                required=True,
            ),
        ],
    )
    field.data_type = DataType(
        data_types=[
            DataType(reference=first_reference),
            DataType(reference=second_reference),
        ],
    )
    field.default = {"wire": "preset"}

    assert str(field) == "field(default_factory=lambda: {'wire': 'preset'})"


def test_data_model_field_nested_constructor_rejects_recursive_mapping_factories() -> None:
    """Self- and mutually recursive defaults must not generate recursive factories."""
    node_reference = Reference(path="Node", original_name="Node", name="Node")
    DataClass(
        reference=node_reference,
        fields=[
            DataModelField(
                name="metadata",
                data_type=DataType(is_dict=True),
                default={},
            ),
            DataModelField(
                name="child",
                data_type=DataType(reference=node_reference),
                default={},
            ),
        ],
    )
    field = DataModelField(
        name="node",
        data_type=DataType(reference=node_reference),
        default={},
    )

    assert str(field) == "field(default_factory=dict)"

    left_reference = Reference(path="Left", original_name="Left", name="Left")
    right_reference = Reference(path="Right", original_name="Right", name="Right")
    DataClass(
        reference=left_reference,
        fields=[
            DataModelField(
                name="right",
                data_type=DataType(reference=right_reference),
                default={},
            ),
        ],
    )
    DataClass(
        reference=right_reference,
        fields=[
            DataModelField(
                name="left",
                data_type=DataType(reference=left_reference),
                default={},
            ),
        ],
    )
    field.data_type = DataType(reference=left_reference)

    assert str(field) == "field(default_factory=dict)"


@pytest.mark.parametrize(
    ("data_type", "default", "expected"),
    [
        pytest.param(
            DataType(is_dict=True),
            {"value": "preset"},
            "field(default_factory=lambda: {'value': 'preset'})",
            id="mapping",
        ),
        pytest.param(
            DataType(data_types=[DataType(is_mapping=True), DataType(type="str")]),
            {"value": "preset"},
            "field(default_factory=lambda: {'value': 'preset'})",
            id="mapping-union",
        ),
        pytest.param(
            DataType(type="str"),
            {"unknown": "preset"},
            "field(default_factory=lambda: {'unknown': 'preset'})",
            id="non-model",
        ),
    ],
)
def test_data_model_field_preserves_plain_mapping_default(
    data_type: DataType,
    default: dict[str, str],
    expected: str,
) -> None:
    """Keep mapping factories when no nested dataclass constructor applies."""
    field = DataModelField(name="value", data_type=data_type, default=default)

    assert str(field) == expected


@pytest.mark.parametrize(
    ("const", "default", "type_"),
    [
        (True, False, "bool"),
        (3, 0, "int"),
        ("fast", "", "str"),
    ],
)
def test_data_model_field_process_const_preserves_explicit_falsy_default(
    const: bool | int | str,
    default: bool | int | str,
    type_: str,
) -> None:
    """Do not treat explicit falsy schema defaults as missing defaults."""
    field = DataModelField(
        name="test_field",
        data_type=DataType(type=type_),
        default=default,
        has_default=True,
        extras={"const": const},
    )

    field.process_const()

    assert field.const is True
    assert field.nullable is False
    assert field.data_type.literals == [const]
    assert field.default == default
