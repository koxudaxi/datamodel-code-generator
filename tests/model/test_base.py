"""Tests for base model classes and utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from unittest.mock import Mock

import pytest

from datamodel_code_generator.imports import (
    IMPORT_ANNOTATED,
    IMPORT_ANY,
    IMPORT_DECIMAL,
    IMPORT_DICT,
    IMPORT_OPTIONAL,
    IMPORT_UNION,
    Import,
)
from datamodel_code_generator.model.base import (
    _MAX_MISSING_CUSTOM_TEMPLATE_SUBDIRS,
    UNDEFINED,
    DataModel,
    DataModelFieldBase,
    TemplateBase,
    _annotation_typing_import_names,
    _clear_custom_template_caches,
    _get_environment,
    _get_environment_with_absolute_path,
    _get_template_with_absolute_path,
    _get_template_with_custom_dir,
    _missing_custom_template_state,
    _refresh_custom_template_paths,
    _remember_missing_custom_template_subdir,
    _RenderedDataModelField,
    _TypingImportRequirements,
    comment_safe,
    escape_docstring,
    format_docstring,
    get_effective_fields,
    get_module_path,
    get_template,
    inline_comment_safe,
    sanitize_module_name,
)
from datamodel_code_generator.model.dataclass import DataClass as DataclassModel
from datamodel_code_generator.model.imports import (
    IMPORT_MSGSPEC_CONVERT,
    IMPORT_MSGSPEC_FIELD,
    IMPORT_MSGSPEC_META,
    IMPORT_MSGSPEC_UNSET,
    IMPORT_MSGSPEC_UNSETTYPE,
)
from datamodel_code_generator.model.msgspec import DataModelField as MsgspecDataModelField
from datamodel_code_generator.model.msgspec import Struct as MsgspecStruct
from datamodel_code_generator.model.msgspec import import_extender
from datamodel_code_generator.model.pydantic_base import DataModelField as PydanticBaseDataModelField
from datamodel_code_generator.model.pydantic_v2 import BaseModel
from datamodel_code_generator.model.pydantic_v2 import DataModelField as PydanticV2DataModelField
from datamodel_code_generator.model.pydantic_v2.base_model import (
    _strip_legacy_pydantic_extra_post_class_assignment,
)
from datamodel_code_generator.model.pydantic_v2.dataclass import DataClass as PydanticDataclassModel
from datamodel_code_generator.model.pydantic_v2.dataclass import DataModelField as PydanticDataclassField
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_FIELD, IMPORT_MISSING
from datamodel_code_generator.model.typed_dict import DataModelField as TypedDictDataModelField
from datamodel_code_generator.model.typed_dict import TypedDict as TypedDictModel
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import ANY, NONE, DataType, Types


class A(TemplateBase):
    """Test helper class for TemplateBase testing."""

    def __init__(self, path: Path) -> None:
        """Initialize with template file path."""
        self._path = path

    @property
    def template_file_path(self) -> Path:
        """Return the template file path."""
        return self._path

    def render(self) -> str:
        """Render the template."""
        return ""


class B(DataModel):
    """Test helper class for DataModel testing with template path."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
        super().__init__(*args, **kwargs)

    TEMPLATE_FILE_PATH = ""


class C(DataModel):
    """Test helper class for DataModel testing without template path."""


@dataclass
class ReferenceSource:
    """Test helper for reference source nullability."""

    nullable: bool
    is_alias: bool = False


def test_get_effective_fields_without_base_classes() -> None:
    """Return only named fields directly when inheritance resolution is unnecessary."""
    named_field = DataModelFieldBase(name="value", data_type=DataType(type="str"))
    model = DataclassModel(
        reference=Reference(path="Model", name="Model"),
        fields=[
            named_field,
            DataModelFieldBase(name=None, data_type=DataType(type="str")),
        ],
    )

    assert get_effective_fields(model) == (named_field,)

    inherited_model = DataclassModel(
        reference=Reference(path="InheritedModel", name="InheritedModel"),
        fields=[],
        base_classes=[model.reference],
    )

    assert get_effective_fields(inherited_model) == (named_field,)


@pytest.mark.parametrize(
    ("model_type", "supports_inherited_enum"),
    [
        pytest.param(DataModel, False, id="base"),
        pytest.param(BaseModel, True, id="pydantic"),
        pytest.param(DataclassModel, True, id="dataclass"),
        pytest.param(MsgspecStruct, True, id="msgspec"),
        pytest.param(PydanticDataclassModel, False, id="pydantic-dataclass"),
        pytest.param(TypedDictModel, False, id="typed-dict"),
    ],
)
def test_inherited_discriminator_enum_capability(
    model_type: type[DataModel],
    *,
    supports_inherited_enum: bool,
) -> None:
    """Output models explicitly declare inherited discriminator enum support."""
    assert model_type.SUPPORTS_INHERITED_DISCRIMINATOR_ENUM is supports_inherited_enum
    external_model_type = type(f"External{model_type.__name__}", (model_type,), {})
    assert external_model_type.SUPPORTS_INHERITED_DISCRIMINATOR_ENUM is supports_inherited_enum


@pytest.mark.parametrize(
    ("field_type", "supports_discriminator"),
    [
        pytest.param(DataModelFieldBase, False, id="base"),
        pytest.param(PydanticV2DataModelField, True, id="pydantic"),
        pytest.param(PydanticDataclassField, True, id="pydantic-dataclass"),
        pytest.param(MsgspecDataModelField, False, id="msgspec"),
        pytest.param(TypedDictDataModelField, False, id="typed-dict"),
    ],
)
def test_discriminator_field_capability(
    field_type: type[DataModelFieldBase],
    *,
    supports_discriminator: bool,
) -> None:
    """Only Pydantic fields opt in to Pydantic discriminator behavior."""
    assert field_type.SUPPORTS_DISCRIMINATOR is supports_discriminator
    external_field_type = type(f"External{field_type.__name__}", (field_type,), {})
    assert external_field_type.SUPPORTS_DISCRIMINATOR is supports_discriminator


def test_msgspec_apply_discriminator_tag() -> None:
    """The msgspec model owns its tagged-union mutation policy."""
    field = MsgspecDataModelField(name="kind", data_type=DataType(literals=["pet"]))
    model = MsgspecStruct(
        fields=[field],
        reference=Reference(path="Pet", original_name="Pet", name="Pet"),
    )

    model.apply_discriminator_tag(field, "kind", "pet")

    assert model.extra_template_data["base_class_kwargs"] == {
        "tag_field": "'kind'",
        "tag": "'pet'",
    }
    assert field.extras["is_classvar"] is True


def test_default_apply_discriminator_tag_is_noop() -> None:
    """Models without tagged unions leave fields and template data unchanged."""
    field = TypedDictDataModelField(name="kind", data_type=DataType(literals=["pet"]))
    model = TypedDictModel(
        fields=[field],
        reference=Reference(path="Pet", original_name="Pet", name="Pet"),
    )

    model.apply_discriminator_tag(field, "kind", "pet")

    assert model.extra_template_data == {}
    assert field.extras == {}


template: str = """{%- for decorator in decorators -%}
{{ decorator }}
{%- endfor %}
@dataclass
class {{ class_name }}:
{%- for field in fields -%}
    {%- if field.required %}
    {{ field.name }}: {{ field.type_hint }}
    {%- else %}
    {{ field.name }}: {{ field.type_hint }} = {{field.default}}
    {%- endif %}
{%- endfor -%}"""


def test_template_base() -> None:
    """Test TemplateBase rendering and file path handling."""
    with NamedTemporaryFile("w", delete=False, encoding="utf-8") as dummy_template:
        dummy_template.write("abc")
        dummy_template.seek(0)
        dummy_template.close()
        a: TemplateBase = A(Path(dummy_template.name))
    assert str(a.template_file_path) == dummy_template.name
    assert a._render() == "abc"
    assert not str(a)


def test_data_model() -> None:
    """Test DataModel rendering with fields and decorators."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), default="abc", required=True)

    with NamedTemporaryFile("w", delete=False, encoding="utf-8") as dummy_template:
        dummy_template.write(template)
        dummy_template.seek(0)
        dummy_template.close()
        B.TEMPLATE_FILE_PATH = dummy_template.name
        data_model = B(
            fields=[field],
            decorators=["@validate"],
            base_classes=[Reference(path="base", original_name="base", name="Base")],
            reference=Reference(path="test_model", name="test_model"),
        )

    assert data_model.name == "test_model"
    assert data_model.fields == [field]
    assert data_model.decorators == ["@validate"]
    assert data_model.base_class == "Base"
    assert data_model.render() == "@validate\n@dataclass\nclass test_model:\n    a: str"


def test_data_model_custom_base_class_list() -> None:
    """Preserve every explicitly configured custom base class."""
    model = BaseModel(
        fields=[],
        reference=Reference(path="Model", original_name="Model", name="Model"),
        custom_base_class=["package.First", "package.Second"],
    )

    assert model.base_class == "First, Second"
    assert [(base.type, base.import_) for base in model.base_classes] == [
        ("First", Import(from_="package", import_="First")),
        ("Second", Import(from_="package", import_="Second")),
    ]


def test_data_model_relative_custom_template_without_adapter() -> None:
    """Load a relative custom template unchanged when the model has no adapter."""

    class RelativeTemplateModel(B):
        """Data model using an existing relative custom template fixture."""

        TEMPLATE_FILE_PATH = "pydantic_v2/BaseModel.jinja2"

    model = RelativeTemplateModel(
        fields=[],
        reference=Reference(path="Model", original_name="Model", name="Model"),
        custom_template_dir=Path("tests/data/templates_pydantic_extra_pre_3593"),
    )

    assert Path(model.template.filename).parts[-2:] == ("pydantic_v2", "BaseModel.jinja2")


def test_pydantic_custom_template_legacy_root_keeps_precedence(tmp_path: Path) -> None:
    """The historical root layout still wins when both custom paths exist."""
    legacy_template = tmp_path / "BaseModel.jinja2"
    current_template = tmp_path / "pydantic_v2/BaseModel.jinja2"
    current_template.parent.mkdir()
    legacy_template.write_text("legacy", encoding="utf-8")
    current_template.write_text("current", encoding="utf-8")

    model = BaseModel(
        fields=[],
        reference=Reference(path="Model", original_name="Model", name="Model"),
        custom_template_dir=tmp_path,
    )

    assert model.template_file_path == legacy_template


def test_direct_data_models_reuse_bounded_custom_template_cache(tmp_path: Path) -> None:
    """Direct model consumers retain bounded process-level template reuse."""
    _clear_custom_template_caches()
    try:
        custom_template = tmp_path / "pydantic_v2/BaseModel.jinja2"
        custom_template.parent.mkdir()
        custom_template.write_text("class {{ class_name }}({{ base_class }}):\n    pass\n", encoding="utf-8")

        models = [
            BaseModel(
                fields=[],
                reference=Reference(path=name, original_name=name, name=name),
                custom_template_dir=tmp_path,
            )
            for name in ("First", "Second")
        ]

        assert models[0].template is models[1].template
        assert _get_template_with_absolute_path.cache_parameters()["maxsize"] == 128
        assert _get_template_with_custom_dir.cache_parameters()["maxsize"] == 128
        assert _get_environment.cache_parameters()["maxsize"] == 16
        assert _get_environment_with_absolute_path.cache_parameters()["maxsize"] == 16
        assert get_template.cache_parameters()["maxsize"] == 128

        for index in range(_MAX_MISSING_CUSTOM_TEMPLATE_SUBDIRS + 2):
            include_only_dir = tmp_path / f"include-only-{index}"
            model = BaseModel(
                fields=[],
                reference=Reference(path=f"Model{index}", original_name=f"Model{index}", name=f"Model{index}"),
                custom_template_dir=include_only_dir,
            )
            _ = model.template

        assert _get_template_with_custom_dir.cache_info().currsize <= 128
        assert _missing_custom_template_state.count == _MAX_MISSING_CUSTOM_TEMPLATE_SUBDIRS
        _refresh_custom_template_paths(tmp_path / "overflow-refresh")
        assert not _missing_custom_template_state.paths
        assert _get_template_with_custom_dir.cache_info().currsize == 0

        missing_subdir = tmp_path / "duplicate/pydantic_v2"
        _remember_missing_custom_template_subdir(missing_subdir.parent, missing_subdir)
        _remember_missing_custom_template_subdir(missing_subdir.parent, missing_subdir)
        assert _missing_custom_template_state.count == 1
    finally:
        _clear_custom_template_caches()


def test_data_model_create_typed_extra_field_unsupported() -> None:
    """Test the default typed extra field factory for unsupported models."""
    assert (
        DataModel.create_typed_extra_field(
            field_model=DataModelFieldBase,
            data_type=DataType(type="str"),
        )
        is None
    )


def test_pydantic_v2_base_model_create_typed_extra_field() -> None:
    """Test Pydantic v2 typed extra field creation."""
    data_type = DataType(type="str", is_dict=True)

    field = BaseModel.create_typed_extra_field(
        field_model=PydanticV2DataModelField,
        data_type=data_type,
    )

    assert field.name == "__pydantic_extra__"
    assert field.original_name == "__pydantic_extra__"
    assert field.data_type is data_type
    assert field.required is True


def test_data_model_dedup_key_uses_model_base_to_hashable_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test DataModel deduplication resolves to_hashable through model.base."""
    calls: list[object] = []

    def fake_to_hashable(value: object) -> tuple[str, int]:
        calls.append(value)
        return ("patched", len(calls))

    monkeypatch.setattr("datamodel_code_generator.model.base.to_hashable", fake_to_hashable)
    model = BaseModel(fields=[], reference=Reference(path="Model", original_name="Model", name="Model"))

    assert model.get_dedup_key() == (("patched", 1), ("patched", 2))
    assert isinstance(calls[0], str)
    assert calls[1] == model.imports


def test_data_model_imports_cache_clears_after_field_type_replacement() -> None:
    """Test model imports reflect field type replacements after an earlier read."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)
    model = BaseModel(fields=[field], reference=Reference(path="Model", original_name="Model", name="Model"))

    assert IMPORT_DECIMAL not in model.imports

    field.replace_data_type(DataType.from_import(IMPORT_DECIMAL))

    assert IMPORT_DECIMAL in model.imports


def test_data_model_render_identity_cache_clears_after_field_mutations() -> None:
    """Field mutations must not retain a render-derived deduplication key."""
    field = PydanticDataclassField(name="value", data_type=DataType(type="str"), required=True)
    model = PydanticDataclassModel(
        fields=[field],
        reference=Reference(path="Model", original_name="Model", name="Model"),
    )
    original_key = model.get_dedup_key()

    field.force_field_assignment()
    field.force_field_assignment()

    assert model.get_dedup_key() != original_key


@pytest.mark.parametrize("reference_name", ["Before", "package.Before"])
def test_data_model_render_identity_cache_clears_after_model_rename(reference_name: str) -> None:
    """Model identity must be recomputed after a generated class name changes."""
    model = BaseModel(
        fields=[],
        reference=Reference(path=reference_name, original_name=reference_name, name=reference_name),
    )
    original_key = model.get_dedup_key(None, use_default=False)

    model.class_name = "After"

    assert model.reference.name == ("package.After" if "." in reference_name else "After")
    assert model.get_dedup_key(None, use_default=False) != original_key


def test_data_model_parent_and_reference_path_changes_invalidate_field_semantics() -> None:
    """Direct model ownership and path changes must refresh self-reference state."""
    model_reference = Reference(path="Before", original_name="Before", name="Before")
    other_reference = Reference(path="After", original_name="After", name="After")
    field = PydanticV2DataModelField(name="value", data_type=DataType(reference=other_reference))
    model = BaseModel(fields=[field], reference=model_reference)

    assert not field.self_reference()

    model.set_reference_path("After")

    assert field.self_reference()

    replacement_model = BaseModel(
        fields=[field],
        reference=Reference(path="Replacement", original_name="Replacement", name="Replacement"),
    )

    assert field.parent is replacement_model
    assert not field.self_reference()


def test_field_deep_copy_drops_transient_semantic_caches() -> None:
    """Copied fields must recompute transient renderer and self-reference state."""
    field = PydanticV2DataModelField(name="value", data_type=DataType(type="str"))
    field.__dict__["_computed_default_factory"] = "list"
    field.__dict__["_self_reference_cache"] = True

    copied = field.copy_deep()

    assert "_computed_default_factory" not in copied.__dict__
    assert "_self_reference_cache" not in copied.__dict__


def test_field_semantic_cache_invalidation_supports_legacy_parent_hook() -> None:
    """External parent implementations with only the legacy import hook remain compatible."""

    class ImportsOnlyParent:
        def __init__(self) -> None:
            self.cache_cleared = False

        def clear_imports_cache(self) -> None:
            self.cache_cleared = True

    parent = ImportsOnlyParent()
    field = DataModelFieldBase(name="value", data_type=DataType(type="str"))
    field.parent = parent  # ty: ignore[invalid-assignment]

    field.invalidate_semantic_caches()

    assert parent.cache_cleared

    parent.cache_cleared = False
    field.force_field_assignment()

    assert parent.cache_cleared


def test_pydantic_v2_extra_type_hint_keeps_non_dict_hint() -> None:
    """Test typed-extra type hint conversion leaves non-dict hints unchanged."""
    field = PydanticV2DataModelField(
        name="__pydantic_extra__",
        data_type=DataType(type="str"),
        required=True,
    )

    assert field.pydantic_extra_type_hint == "str"


def test_pydantic_v2_extra_type_hint_uses_structured_root_dict() -> None:
    """Test typed-extra type hint renders only the root dict as typing.Dict."""
    item_type = DataType(type="str", is_list=True, use_standard_collections=True)
    data_type = DataType(data_types=[item_type], is_dict=True, use_standard_collections=True)
    field = PydanticV2DataModelField(
        name="__pydantic_extra__",
        data_type=data_type,
        required=True,
    )

    assert field.type_hint == "dict[str, list[str]]"
    assert field.pydantic_extra_type_hint == "Dict[str, list[str]]"
    assert data_type.use_standard_collections is True
    assert item_type.use_standard_collections is True
    assert IMPORT_DICT in field.imports


def test_pydantic_v2_extra_annotation_mode_defaults_to_annotations_dict() -> None:
    """Test typed extras use class-body __annotations__ by default."""
    field = PydanticV2DataModelField(
        name="__pydantic_extra__",
        data_type=DataType(type="str", is_dict=True, use_standard_collections=True),
        required=True,
    )

    assert field.is_pydantic_extra_field
    assert field.use_pydantic_extra_annotations_dict
    assert not field.use_pydantic_extra_plain_annotation
    assert IMPORT_DICT in field.imports


def test_pydantic_v2_extra_annotation_mode_uses_plain_annotation_for_native_deferred() -> None:
    """Test typed extras use plain annotations for native deferred annotation targets."""
    field = PydanticV2DataModelField(
        name="__pydantic_extra__",
        data_type=DataType(type="str", is_dict=True, use_standard_collections=True),
        required=True,
    )
    model = BaseModel(fields=[field], reference=Reference(path="Model", original_name="Model", name="Model"))

    model.extra_template_data["pydantic_extra_plain_annotation"] = True

    assert field.use_pydantic_extra_plain_annotation
    assert not field.use_pydantic_extra_annotations_dict
    assert IMPORT_DICT not in field.imports


def test_pydantic_v2_legacy_extra_template_supports_relative_custom_path() -> None:
    """Test legacy typed extras render through a relative custom template path."""
    field = PydanticV2DataModelField(
        name="__pydantic_extra__",
        data_type=DataType(type="str", is_dict=True),
        required=True,
    )
    model = BaseModel(
        fields=[field],
        reference=Reference(path="Model", original_name="Model", name="Model"),
        custom_template_dir=Path("tests/data/templates_pydantic_extra_pre_3593"),
    )

    with pytest.warns(UserWarning, match="was rewritten automatically for Pydantic typed-extra"):
        rendered = model.render()

    assert Path(model.template.filename).parts[-2:] == ("pydantic_v2", "BaseModel.jinja2")
    assert "'__pydantic_extra__': Dict[str, str]," in rendered
    assert "Model.__annotations__['__pydantic_extra__']" not in rendered
    assert "Model.model_rebuild(force=True)" not in rendered
    assert "locals()" not in rendered


@pytest.mark.parametrize("customization", ["missing-tail", "missing-class-body"])
def test_pydantic_v2_legacy_extra_template_warns_when_not_fully_rewritten(customization: str, tmp_path: Path) -> None:
    """Warn without failing when a customized legacy template cannot be fully rewritten."""
    source_template = Path("tests/data/templates_pydantic_extra_pre_3593/pydantic_v2/BaseModel.jinja2")
    custom_template = tmp_path / "pydantic_v2/BaseModel.jinja2"
    custom_template.parent.mkdir()
    template_source = source_template.read_text(encoding="utf-8")
    match customization:
        case "missing-tail":
            template_source = template_source.rsplit("{%- for field in fields %}", 1)[0]
        case _:
            template_source = template_source.replace(
                "{%- for line in class_body_lines %}\n    {{ line }}\n{%- endfor %}\n",
                "",
            )
    custom_template.write_text(template_source, encoding="utf-8")
    field = PydanticV2DataModelField(
        name="__pydantic_extra__",
        data_type=DataType(type="str", is_dict=True),
        required=True,
    )
    model = BaseModel(
        fields=[field],
        reference=Reference(path="Model", original_name="Model", name="Model"),
        custom_template_dir=tmp_path,
    )

    with pytest.warns(UserWarning, match="could not be fully rewritten automatically"):
        rendered = model.render()

    match customization:
        case "missing-tail":
            assert "'__pydantic_extra__': Dict[str, str]," in rendered
        case _:
            assert "Model.__annotations__['__pydantic_extra__'] = Dict[str, str]" in rendered


def test_strip_legacy_pydantic_extra_post_class_assignment_is_model_scoped() -> None:
    """Strip only the target model's old assignment while preserving rebuilds and helpers."""
    rendered = (
        "Helper.__annotations__['__pydantic_extra__'] = Dict[str, int]\n"
        "Helper.model_rebuild(force=True)\n"
        'Model . __annotations__ [ "__pydantic_extra__" ] = Dict[str, int]\r\n'
        "\r\n"
        "Model . model_rebuild ( force = True )  # legacy\r\n"
        "Model.model_rebuild()\n"
    )

    assert _strip_legacy_pydantic_extra_post_class_assignment(rendered, "Missing") is None
    assert _strip_legacy_pydantic_extra_post_class_assignment(rendered, "Model") == (
        "Helper.__annotations__['__pydantic_extra__'] = Dict[str, int]\n"
        "Helper.model_rebuild(force=True)\n"
        "Model.model_rebuild()\n"
    )
    unicode_stripped = _strip_legacy_pydantic_extra_post_class_assignment(
        "℘Model.__annotations__['__pydantic_extra__'] = Dict[str, int]\n℘Model.model_rebuild(force=True)\n",
        "℘Model",
    )
    assert unicode_stripped is not None
    assert not unicode_stripped


def test_pydantic_v2_missing_sentinel_default_keeps_explicit_default() -> None:
    """Test explicit defaults are not replaced by the MISSING sentinel."""
    field = PydanticV2DataModelField(
        name="value",
        data_type=DataType(type="str"),
        default="fallback",
        use_missing_sentinel=True,
    )

    assert not field.use_missing_sentinel_default
    assert field.represented_default == "'fallback'"
    assert IMPORT_MISSING not in field.imports


def test_pydantic_v2_missing_sentinel_type_hint_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test defensive MISSING type-hint branches."""
    field = PydanticV2DataModelField(
        name="value",
        data_type=DataType(type="str", use_union_operator=True),
        use_missing_sentinel=True,
    )

    assert field._type_hint_with_missing_sentinel("") == "MISSING"

    monkeypatch.setattr(PydanticV2DataModelField, "_use_union_operator", property(lambda _self: None))

    assert field._type_hint_with_missing_sentinel("str") == "str"


def test_rendered_pydantic_v2_field_uses_structured_values() -> None:
    """Test the built-in proxy exposes both views of the structured render plan."""
    field = PydanticV2DataModelField(
        name="name",
        data_type=DataType(type="str"),
        required=True,
        extras={"title": "Name"},
        use_annotated=True,
    )
    expected_field = field.field
    expected_annotated = field.annotated
    rendered_field = _RenderedDataModelField(field, "")

    assert rendered_field.annotated == expected_annotated
    assert rendered_field.field == expected_field


@pytest.mark.parametrize(
    ("field_kwargs", "expected"),
    [
        pytest.param({"extras": {"title": "Field("}}, "title='Field('", id="title"),
        pytest.param({"extras": {"description": "Field("}}, "description='Field('", id="description"),
        pytest.param({"extras": {"examples": ["Field("]}}, "examples=['Field(']", id="examples"),
        pytest.param(
            {"extras": {"json_schema_extra": {"marker": "Field("}}},
            "json_schema_extra={'marker': 'Field('}",
            id="json-schema-extra",
        ),
        pytest.param({"alias": "Field("}, "alias='Field('", id="alias"),
    ],
)
def test_pydantic_default_kwarg_preserves_field_syntax_in_user_metadata(
    field_kwargs: dict[str, object],
    expected: str,
) -> None:
    """Only the actual positional default is converted to a default keyword."""
    field = PydanticV2DataModelField(
        name="value",
        data_type=DataType(type="str"),
        default="value",
        required=False,
        has_default=True,
        use_default_kwarg=True,
        **field_kwargs,
    )

    assert str(field).startswith("Field('value', ")
    assert field.field == f"Field(default='value', {expected})"


@pytest.mark.parametrize(
    ("default", "has_default", "required", "extra_values", "expected"),
    [
        pytest.param(
            "value",
            True,
            False,
            {},
            "Field(default='value', title='Field(')",
            id="default",
        ),
        pytest.param(
            UNDEFINED,
            True,
            False,
            {"default_factory": "list"},
            "Field(default_factory=list, title='Field(')",
            id="factory",
        ),
        pytest.param(
            UNDEFINED,
            False,
            True,
            {},
            "Field(..., title='Field(')",
            id="required",
        ),
    ],
)
def test_pydantic_field_render_plan_preserves_assignment_semantics(
    default: object,
    has_default: bool,
    required: bool,
    extra_values: dict[str, object],
    expected: str,
) -> None:
    """Default, factory, and required assignments share one structured plan."""
    field = PydanticV2DataModelField(
        name="value",
        data_type=DataType(type="str"),
        default=default,
        required=required,
        has_default=has_default,
        extras={"title": "Field(", **extra_values},
        use_default_kwarg=True,
    )

    assert field.field == expected


def test_pydantic_v2_field_render_plan_preserves_explicit_null_default() -> None:
    """The v2-only Field(None) fallback keeps its distinct assignment form."""
    field = PydanticV2DataModelField(
        name="value",
        data_type=DataType(type="None"),
        default=None,
        required=False,
        has_default=True,
        use_annotated=True,
        use_default_kwarg=True,
    )

    assert str(field) == "Field(None)"
    assert field.field == "Field(default=None)"
    assert field.annotated == "Annotated[None, Field(None)]"


def test_pydantic_field_render_plan_preserves_required_nullable_marker() -> None:
    """A required nullable field uses the shared single-argument Field() plan."""
    field = PydanticV2DataModelField(
        name="value",
        data_type=DataType(type="str"),
        required=True,
        nullable=True,
    )

    assert str(field) == "Field(...)"
    assert field.field == "Field(...)"


def test_pydantic_field_render_plan_preserves_string_discriminator() -> None:
    """A string discriminator remains structured Field() metadata."""
    field = PydanticBaseDataModelField(
        name="value",
        data_type=DataType(type="str"),
        required=True,
        extras={"discriminator": "kind"},
    )

    assert str(field) == "Field(..., discriminator='kind')"


def test_pydantic_class_var_factory_state_is_access_order_independent() -> None:
    """ClassVar field rendering stays stateless across compatibility accessors."""
    field = PydanticV2DataModelField(
        name="value",
        data_type=DataType(type="str"),
        required=False,
        extras={"x-is-classvar": True, "default_factory": "list"},
        use_annotated=True,
    )

    assert field.has_default_factory_in_field is False
    assert field._get_field_data_and_default_factory() == ({}, None)
    assert field._rendered_field_values() == (None, None)
    assert field.field is None
    assert field.has_default_factory_in_field is False


def test_pydantic_base_field_string_uses_structured_render_plan() -> None:
    """The shared Pydantic field class renders through the structured path."""
    field = PydanticBaseDataModelField(
        name="value",
        data_type=DataType(type="str"),
        default="value",
        required=False,
        has_default=True,
        extras={"description": "Field("},
    )

    assert str(field) == "Field('value', description='Field(')"


@pytest.mark.parametrize(
    ("field_kwargs", "expected_field"),
    [
        pytest.param({"default": "lambda: convert"}, "'lambda: convert'", id="default"),
        pytest.param(
            {"default": "value", "alias": "lambda: convert"},
            "field(name='lambda: convert', default='value')",
            id="alias",
        ),
    ],
)
def test_msgspec_convert_import_ignores_user_string_false_positives(
    field_kwargs: dict[str, object],
    expected_field: str,
) -> None:
    """User values containing converter syntax do not create a converter import."""
    field = MsgspecDataModelField(
        name="value",
        data_type=DataType(type="str"),
        required=True,
        has_default=True,
        use_default_with_required=True,
        **field_kwargs,
    )

    assert str(field) == expected_field
    assert IMPORT_MSGSPEC_CONVERT not in field.imports


def test_msgspec_struct_default_render_plan_requires_convert_import() -> None:
    """A generated Struct conversion factory retains both syntax-owned imports."""
    nested_reference = Reference(path="#/Nested", name="Nested")
    MsgspecStruct(reference=nested_reference, fields=[])
    field = MsgspecDataModelField(
        name="nested",
        data_type=DataType(reference=nested_reference),
        default={"value": "Field("},
        required=False,
        has_default=True,
    )

    assert str(field) == "field(default_factory=lambda: convert({'value': 'Field('},  type=Nested))"
    assert field._get_field_data() == {"default_factory": "lambda: convert({'value': 'Field('},  type=Nested)"}
    assert IMPORT_MSGSPEC_FIELD in field.imports
    assert IMPORT_MSGSPEC_CONVERT in field.imports


def test_msgspec_empty_struct_default_uses_conversion_factory() -> None:
    """An empty object for a Struct still creates the declared model."""
    nested_reference = Reference(path="#/Nested", name="Nested")
    MsgspecStruct(reference=nested_reference, fields=[])
    field = MsgspecDataModelField(
        name="nested",
        data_type=DataType(reference=nested_reference),
        default={},
        required=False,
        has_default=True,
    )
    MsgspecStruct(reference=Reference(path="#/Owner", name="Owner"), fields=[field])

    assert str(field) == "field(default_factory=lambda: convert({},  type=Nested))"
    assert IMPORT_MSGSPEC_FIELD in field.imports
    assert IMPORT_MSGSPEC_CONVERT in field.imports
    assert IMPORT_MSGSPEC_UNSET not in field.imports


@pytest.mark.parametrize(
    ("container_type", "default", "expected"),
    [
        pytest.param(
            DataType(is_list=True),
            [],
            "field(default_factory=list)",
            id="list",
        ),
        pytest.param(
            DataType(is_dict=True),
            {},
            "field(default_factory=dict)",
            id="dict",
        ),
        pytest.param(
            DataType(is_set=True),
            set(),
            "field(default_factory=set)",
            id="set",
        ),
    ],
)
def test_msgspec_empty_struct_container_defaults_use_builtin_factory(
    container_type: DataType,
    default: dict[object, object] | list[object] | set[object],
    expected: str,
) -> None:
    """Empty Struct containers keep the allocation-only builtin factory."""
    nested_reference = Reference(path="#/Nested", name="Nested")
    MsgspecStruct(reference=nested_reference, fields=[])
    container_type.data_types = [DataType(reference=nested_reference)]
    field = MsgspecDataModelField(
        name="nested",
        data_type=DataType(data_types=[container_type]),
        default=default,
        required=False,
        has_default=True,
    )
    MsgspecStruct(reference=Reference(path="#/Owner", name="Owner"), fields=[field])

    assert str(field) == expected
    assert IMPORT_MSGSPEC_FIELD in field.imports
    assert IMPORT_MSGSPEC_CONVERT not in field.imports
    assert IMPORT_MSGSPEC_UNSET not in field.imports


def test_msgspec_optional_nested_factory_does_not_import_unused_unset() -> None:
    """A rendered nested factory owns field syntax without an UNSET value."""
    nested_reference = Reference(path="#/Nested", name="Nested")
    MsgspecStruct(reference=nested_reference, fields=[])
    field = MsgspecDataModelField(
        name="nested",
        data_type=DataType(reference=nested_reference),
        default=None,
        required=False,
        use_default_factory_for_optional_nested_models=True,
    )
    MsgspecStruct(reference=Reference(path="#/Owner", name="Owner"), fields=[field])

    assert str(field) == "field(default_factory=Nested)"
    assert IMPORT_MSGSPEC_FIELD in field.imports
    assert IMPORT_MSGSPEC_UNSET not in field.imports


def test_msgspec_import_extender_preserves_generic_field_imports() -> None:
    """The reusable import decorator leaves non-msgspec field imports unchanged."""

    @import_extender
    class GenericField(DataModelFieldBase):
        pass

    field = GenericField(
        name="value",
        data_type=DataType.from_import(IMPORT_DECIMAL),
        required=True,
    )

    assert field.imports == (IMPORT_DECIMAL,)


def test_msgspec_class_var_imports_ignore_instance_field_syntax() -> None:
    """Class variables do not inherit imports from instance-field rendering."""
    field = MsgspecDataModelField(
        name="value",
        data_type=DataType.from_import(IMPORT_DECIMAL),
        default=None,
        required=False,
        extras={"is_classvar": True, "default_factory": "list"},
    )

    assert field.imports == ()


def test_rendered_pydantic_v2_class_var_field_values_are_none() -> None:
    """Test class variable fields do not render Field or Annotated values."""
    field = PydanticV2DataModelField(
        name="name",
        data_type=DataType(type="str"),
        required=True,
        extras={"x-is-classvar": True},
        use_annotated=True,
    )
    rendered_field = _RenderedDataModelField(field, "")

    assert field.field is None
    assert rendered_field.field is None
    assert rendered_field.annotated is None


def test_field_semantic_policy_api() -> None:
    """Expose parser-facing field semantics without backend extras knowledge."""
    base_field = DataModelFieldBase(name="value", data_type=DataType(type="str"))
    msgspec_field = MsgspecDataModelField(
        name="constant",
        data_type=DataType(type="str"),
        extras={"is_classvar": True},
    )
    pydantic_field = PydanticV2DataModelField(
        name="constant",
        data_type=DataType(type="str"),
        required=True,
        extras={"x-is-classvar": True},
    )

    assert base_field.constructor_keyword_only is None
    base_field.mark_as_keyword_only()
    assert base_field.constructor_keyword_only is True
    assert base_field.is_class_var is False
    assert msgspec_field.is_class_var is True
    assert pydantic_field.is_class_var is True
    assert pydantic_field.type_hint == "ClassVar[str]"
    assert base_field.enable_structured_default_validation() is False
    assert pydantic_field.enable_structured_default_validation() is True
    assert pydantic_field.enable_structured_default_validation() is False
    assert pydantic_field.extras["validate_default"] is True


def test_rendered_data_model_field_caches_delegated_attributes() -> None:
    """Test delegated field attributes are stored directly on the rendered proxy."""

    @dataclass
    class DelegatedField:
        """Test field with counted attribute access."""

        calls: int = 0

        @property
        def value(self) -> str:
            """Return a counted delegated value."""
            self.calls += 1
            return "cached value"

    field = DelegatedField()
    rendered_field = _RenderedDataModelField(field, "docstring")

    assert rendered_field.docstring == "docstring"
    assert rendered_field.value == "cached value"
    assert rendered_field.value == "cached value"
    assert field.calls == 1
    assert rendered_field.__dict__["value"] == "cached value"


def test_rendered_data_model_field_preserves_missing_attribute_errors() -> None:
    """Test missing delegated field attributes still raise AttributeError."""
    rendered_field = _RenderedDataModelField(object(), "")

    with pytest.raises(AttributeError):
        _ = rendered_field.missing


def test_rendered_data_model_field_batches_field_and_annotated_values() -> None:
    """Test field and annotated template values share one lazy render call."""

    @dataclass
    class RenderValuesField:
        """Test field that batches rendered field values."""

        calls: int = 0

        def _rendered_field_values(self) -> tuple[str, str]:
            """Return counted rendered values."""
            self.calls += 1
            return "field value", "annotated value"

    field = RenderValuesField()
    rendered_field = _RenderedDataModelField(field, "")

    assert rendered_field.annotated == "annotated value"
    assert rendered_field.field == "field value"
    assert field.calls == 1
    assert rendered_field.__dict__["field"] == "field value"
    assert rendered_field.__dict__["annotated"] == "annotated value"


def test_jinja_environment_auto_reload_only_for_custom_templates(tmp_path: Path) -> None:
    """Test built-in templates disable Jinja auto-reload while custom templates keep it."""
    _get_environment.cache_clear()
    _get_environment_with_absolute_path.cache_clear()

    builtin_environment = _get_environment(Path(), None)
    custom_environment = _get_environment(Path(), tmp_path)
    missing_custom_subdir_environment = _get_environment(Path("pydantic_v2"), tmp_path)
    absolute_path_environment = _get_environment_with_absolute_path(tmp_path, Path())

    assert builtin_environment.auto_reload is False
    assert custom_environment.auto_reload is True
    assert missing_custom_subdir_environment.auto_reload is False
    assert absolute_path_environment.auto_reload is True


def test_pydantic_base_class_var_imports_do_not_require_field() -> None:
    """Test common Pydantic ClassVar fields skip Field() without render state."""
    field = PydanticBaseDataModelField(
        name="name",
        data_type=DataType(type="str"),
        required=True,
        extras={"x-is-classvar": True},
    )
    assert IMPORT_FIELD not in field.imports
    assert field.field is None


def test_pydantic_forced_required_assignment_imports_field() -> None:
    """A required override rendered as Field(...) must contribute its only import."""
    field = PydanticDataclassField(
        name="name",
        data_type=DataType(type="str"),
        required=True,
    )

    field.force_field_assignment()

    assert str(field) == "Field(...)"
    assert IMPORT_FIELD in field.imports


@pytest.mark.parametrize(
    ("use_default_with_required", "expected"),
    [
        pytest.param(False, "", id="required"),
        pytest.param(True, "Field(default_factory=list)", id="required-with-default"),
    ],
)
def test_pydantic_required_default_factory_respects_default_policy(
    *,
    use_default_with_required: bool,
    expected: str,
) -> None:
    """A required schema factory is used only when required defaults are enabled."""
    field = PydanticV2DataModelField(
        name="items",
        data_type=DataType(type="str", is_list=True),
        required=True,
        has_default=True,
        extras={"default_factory": "list"},
        use_default_with_required=use_default_with_required,
    )

    assert str(field) == expected


@pytest.mark.parametrize(
    ("default", "extras", "use_default_kwarg", "expected"),
    [
        pytest.param("value", {"kw_only": True}, False, "Field('value', kw_only=True)", id="scalar"),
        pytest.param(
            "value",
            {"kw_only": True},
            True,
            "Field(default='value', kw_only=True)",
            id="scalar-default-keyword",
        ),
        pytest.param(
            UNDEFINED,
            {"default_factory": "list"},
            False,
            "Field(default_factory=list)",
            id="factory",
        ),
    ],
)
def test_pydantic_annotated_dataclass_field_preserves_constructor_default(
    default: object,
    extras: dict[str, object],
    use_default_kwarg: bool,
    expected: str,
) -> None:
    """Annotated metadata must keep scalar and factory defaults on the dataclass RHS."""
    field = PydanticDataclassField(
        name="items",
        data_type=DataType(type="str"),
        default=default,
        required=False,
        has_default=True,
        extras=extras,
        use_annotated=True,
        use_default_kwarg=use_default_kwarg,
    )

    assert field.dataclass_field == expected


@pytest.mark.parametrize("use_default_kwarg", [False, True])
def test_pydantic_annotated_dataclass_field_omits_undefined_default(*, use_default_kwarg: bool) -> None:
    """Dataclass-only metadata must not turn the unresolved sentinel into Python source."""
    field = PydanticDataclassField(
        name="item",
        data_type=DataType(type="str"),
        default=UNDEFINED,
        required=False,
        has_default=False,
        extras={"kw_only": True},
        use_annotated=True,
        use_default_kwarg=use_default_kwarg,
    )

    assert field.dataclass_field == "Field(kw_only=True)"
    assert field.field == "Field(kw_only=True)"


def test_pydantic_dataclass_optional_nested_model_uses_default_factory() -> None:
    """The optional-nested-model flag recognizes Pydantic dataclass references."""
    nested_reference = Reference(path="#/Nested", name="Nested")
    PydanticDataclassModel(reference=nested_reference, fields=[])
    field = PydanticDataclassField(
        name="nested",
        data_type=DataType(reference=nested_reference),
        default=None,
        required=False,
        has_default=False,
        use_annotated=True,
        use_default_factory_for_optional_nested_models=True,
    )

    assert field.dataclass_field == "Field(default_factory=Nested)"
    assert field.field == "Field(default_factory=Nested)"
    assert field.has_default_factory_in_field is True
    assert field._get_constructor_default_info() == (True, False)
    assert field.dataclass_field == "Field(default_factory=Nested)"


def test_pydantic_dataclass_render_computes_plan_once() -> None:
    """Built-in dataclass rendering shares one local plan across policy and output."""
    plan_calls = 0

    class CountingField(PydanticDataclassField):
        def _get_field_render_plan(self) -> Any:
            nonlocal plan_calls
            plan_calls += 1
            return super()._get_field_render_plan()

    field = CountingField(
        name="value",
        data_type=DataType(type="str"),
        required=True,
        extras={"repr": False},
        use_annotated=True,
    )

    assert field._rendered_field_values() == ("Field(repr=False)", None)
    assert plan_calls == 1


def test_pydantic_missing_sentinel_checks_optional_factory_once() -> None:
    """The missing-sentinel policy reuses the effective factory decision."""
    factory_calls = 0

    class CountingField(PydanticV2DataModelField):
        def _get_default_factory_for_optional_nested_model(self) -> str | None:
            nonlocal factory_calls
            factory_calls += 1
            return super()._get_default_factory_for_optional_nested_model()

    field = CountingField(
        name="value",
        data_type=DataType(type="str"),
        required=False,
        use_missing_sentinel=True,
        use_default_factory_for_optional_nested_models=True,
    )

    assert field.use_missing_sentinel_default is True
    assert factory_calls == 1


@pytest.mark.parametrize("use_annotated", [False, True])
def test_pydantic_dataclass_field_rebuilds_from_structured_arguments(*, use_annotated: bool) -> None:
    """Dataclass defaults are inserted without parsing Field-like user metadata."""
    field = PydanticDataclassField(
        name="value",
        data_type=DataType(type="str"),
        default="value",
        required=False,
        has_default=True,
        extras={"title": "Field(", "examples": ["Field("], "kw_only": True},
        use_annotated=use_annotated,
        use_default_kwarg=True,
    )

    expected = "Field(default='value', examples=['Field('], kw_only=True, title='Field(')"
    assert field.dataclass_field == expected
    assert field.field == expected
    assert field.annotated is None


def test_pydantic_annotated_dataclass_field_skips_empty_assignment() -> None:
    """A plain required Annotated field does not synthesize an empty RHS."""
    field = PydanticDataclassField(
        name="item",
        data_type=DataType(type="str"),
        required=True,
        use_annotated=True,
    )

    assert field.dataclass_field is None


def test_pydantic_dataclass_annotated_assignment_uses_existing_template_contract() -> None:
    """Dataclass-only metadata should use the legacy field/annotated template branches."""
    assigned_field = PydanticDataclassField(
        name="assigned",
        data_type=DataType(type="str"),
        required=True,
        extras={"repr": False},
        use_annotated=True,
    )
    annotated_field = PydanticDataclassField(
        name="annotated",
        data_type=DataType(type="str"),
        required=True,
        extras={"title": "Annotated"},
        use_annotated=True,
    )

    assert assigned_field.annotated is None
    assert assigned_field.requires_dataclass_field_assignment is True
    assert assigned_field.field == "Field(repr=False)"
    assert assigned_field._rendered_field_values() == ("Field(repr=False)", None)
    assert IMPORT_ANNOTATED not in assigned_field.imports
    assert annotated_field.annotated == "Annotated[str, Field(title='Annotated')]"
    assert annotated_field._rendered_field_values() == (
        "Field(title='Annotated')",
        "Annotated[str, Field(title='Annotated')]",
    )
    assert IMPORT_ANNOTATED in annotated_field.imports


def test_pydantic_v2_leaf_field_imports_skip_discriminator_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test leaf fields do not walk all nested data types for impossible discriminators."""
    field = PydanticV2DataModelField(
        name="name",
        data_type=DataType(type="str"),
        required=True,
    )

    def fail_all_data_types(_self: DataType) -> tuple[DataType, ...]:
        message = "unexpected discriminator scan"
        raise AssertionError(message)

    monkeypatch.setattr(DataType, "all_data_types", property(fail_all_data_types))

    assert IMPORT_FIELD not in field.imports
    with pytest.raises(AssertionError, match="unexpected discriminator scan"):
        tuple(DataType(type="str").all_data_types)


def test_pydantic_v2_nested_discriminator_still_imports_field() -> None:
    """Test discriminator imports still work for nested data types."""
    field = PydanticV2DataModelField(
        name="item",
        data_type=DataType(data_types=[DataType(type="Pet", discriminator="pet_type")]),
        required=True,
    )

    assert IMPORT_FIELD in field.imports


def _msgspec_field(data_type: DataType, **kwargs: Any) -> MsgspecDataModelField:
    field = MsgspecDataModelField(name="value", data_type=data_type, required=False, **kwargs)
    MsgspecStruct(fields=[field], reference=Reference(path="Model", original_name="Model", name="Model"))
    return field


def test_msgspec_unset_type_hint_uses_structured_ordered_union() -> None:
    """Test msgspec UnsetType is added through an ordered DataType union."""
    data_type = DataType(data_types=[DataType(type="str"), DataType(type=NONE)])
    field = _msgspec_field(data_type)

    assert field.type_hint == "Union[str, None, UnsetType]"
    assert data_type.preserve_union_member_order is False
    assert field.imports == (IMPORT_MSGSPEC_UNSETTYPE, IMPORT_UNION, IMPORT_MSGSPEC_UNSET)


def test_msgspec_unset_type_hint_handles_empty_and_simple_types() -> None:
    """Test msgspec UnsetType structural unions cover empty and simple field types."""
    assert _msgspec_field(DataType()).type_hint == "UnsetType"
    assert _msgspec_field(DataType(type="str")).type_hint == "Union[str, UnsetType]"
    assert _msgspec_field(DataType(type="str", is_optional=True)).type_hint == "Union[str, None, UnsetType]"
    assert _msgspec_field(DataType(data_types=[DataType(type="str"), DataType(type="int")])).type_hint == (
        "Union[str, int, UnsetType]"
    )
    none_field = _msgspec_field(DataType(is_optional=True))
    assert none_field.type_hint == "Union[None, UnsetType]"
    assert none_field.imports == (IMPORT_MSGSPEC_UNSETTYPE, IMPORT_UNION, IMPORT_MSGSPEC_UNSET)


def test_msgspec_unset_import_is_limited_to_struct_fields() -> None:
    """Test msgspec UNSET value imports match Struct-only field emission."""
    field = MsgspecDataModelField(name="value", data_type=DataType(type="str"), required=False)
    annotated_field = MsgspecDataModelField(
        name="value",
        data_type=DataType(type="str"),
        required=False,
        extras={"max_length": 5},
        use_annotated=True,
    )

    assert IMPORT_MSGSPEC_UNSET not in field.imports
    assert IMPORT_MSGSPEC_UNSET not in annotated_field.imports


def test_msgspec_data_type_copy_preserves_structural_children() -> None:
    """Test msgspec annotation copies preserve dict keys and kwargs without parent links."""
    field = _msgspec_field(DataType(type="str"))
    data_type = DataType(
        type="Value",
        is_dict=True,
        dict_key=DataType(type="Key"),
        kwargs={"strict": True},
    )

    copied = field._copy_data_type(data_type)

    assert copied is not data_type
    assert copied.parent is None
    assert copied.children == []
    assert copied.dict_key is not data_type.dict_key
    assert copied.dict_key.type == "Key"
    assert copied.kwargs == {"strict": True}


def test_msgspec_annotated_unset_keeps_none_outside_annotated() -> None:
    """Test msgspec Annotated fields keep None outside the Annotated branch."""
    field = _msgspec_field(
        DataType(type="str", is_optional=True),
        extras={"max_length": 5},
        use_annotated=True,
    )

    assert field.annotated == "Union[Annotated[str, Meta(max_length=5)], None, UnsetType]"
    assert field.needs_annotated_import is True
    assert field.imports == (
        IMPORT_MSGSPEC_UNSETTYPE,
        IMPORT_UNION,
        IMPORT_ANNOTATED,
        IMPORT_MSGSPEC_META,
        IMPORT_MSGSPEC_UNSET,
    )


def test_msgspec_required_annotated_nullable_keeps_none_outside_annotated() -> None:
    """Test required msgspec Annotated nullable fields keep None outside Annotated."""
    field = MsgspecDataModelField(
        name="value",
        data_type=DataType(type="str", is_optional=True),
        required=True,
        extras={"max_length": 5},
        use_annotated=True,
    )
    MsgspecStruct(fields=[field], reference=Reference(path="Model", original_name="Model", name="Model"))

    assert field.annotated == "Union[Annotated[str, Meta(max_length=5)], None]"
    assert field.imports == (
        IMPORT_UNION,
        IMPORT_ANNOTATED,
        IMPORT_MSGSPEC_META,
    )


def test_typed_dict_empty_original_name_uses_functional_syntax_and_key() -> None:
    """Preserve an empty source key instead of falling back to the generated field name."""
    field = TypedDictDataModelField(
        name="field_",
        original_name="",
        data_type=DataType(type="str"),
        required=True,
    )
    model = TypedDictModel(
        fields=[field],
        reference=Reference(path="EmptyField", original_name="EmptyField", name="EmptyField"),
    )

    rendered = model.render()
    assert model.is_functional_syntax
    assert not field.key
    assert "EmptyField = TypedDict('EmptyField', {" in rendered
    assert "    '': str," in rendered


@pytest.mark.parametrize("source_name", ["", "value"], ids=["empty", "regular"])
def test_typed_dict_functional_syntax_replaces_inherited_source_key(source_name: str) -> None:
    """Render only the child override when an inherited source key is repeated."""
    base_reference = Reference(path="Base", original_name="Base", name="Base")
    TypedDictModel(
        fields=[
            TypedDictDataModelField(
                name="base_value",
                original_name=source_name,
                data_type=DataType(type="str"),
                required=False,
            )
        ],
        reference=base_reference,
    )
    child = TypedDictModel(
        fields=[
            TypedDictDataModelField(
                name="child_value",
                original_name=source_name,
                data_type=DataType(type="int"),
                required=True,
            ),
            TypedDictDataModelField(
                name="trigger_key",
                original_name="trigger-key",
                data_type=DataType(type="bool"),
                required=True,
            ),
        ],
        base_classes=[base_reference],
        reference=Reference(path="Child", original_name="Child", name="Child"),
    )

    matching_fields = [field for field in child.all_fields if field.original_name == source_name]
    rendered = child.render()
    assert len(matching_fields) == 1
    assert matching_fields[0].name == "child_value"
    assert matching_fields[0].type_hint == "int"
    assert rendered.count(f"'{source_name}':") == 1
    assert f"'{source_name}': int," in rendered


def test_ordered_union_type_hint_handles_empty_and_discriminator() -> None:
    """Test ordered union rendering keeps explicit order without Optional normalization."""
    empty_union = DataType(data_types=[DataType(), DataType()], preserve_union_member_order=True)
    deduplicated_union = DataType(
        data_types=[DataType(type="str"), DataType(type="str")],
        preserve_union_member_order=True,
    )
    discriminated_union = DataType(
        data_types=[DataType(type="str"), DataType(type="int")],
        discriminator="kind",
        preserve_union_member_order=True,
    )

    assert empty_union.type_hint == ANY
    assert deduplicated_union.type_hint == "str"
    assert discriminated_union.type_hint == "Annotated[Union[str, int], Field(discriminator='kind')]"


def test_data_model_exception() -> None:
    """Test DataModel raises exception when TEMPLATE_FILE_PATH is undefined."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), default="abc", required=True)
    with pytest.raises(Exception, match="TEMPLATE_FILE_PATH is undefined"):
        C(
            fields=[field],
            reference=Reference(path="abc", original_name="abc", name="abc"),
        )


def test_replace_children_in_models_updates_matching_owner_references() -> None:
    """Test replacing reference children for only the selected owner models."""
    old_reference = Reference(path="Old", original_name="Old", name="Old")
    new_reference = Reference(path="Selected", original_name="Selected", name="Selected")
    target_model = BaseModel(fields=[], reference=old_reference)
    selected_type = DataType(data_types=[DataType(reference=old_reference)])
    selected_reference_type = selected_type.data_types[0]
    selected_reference_type.parent = selected_type
    selected_field = DataModelFieldBase(data_type=selected_type)
    selected_model = BaseModel(
        fields=[selected_field],
        reference=Reference(path="Selected", original_name="Selected", name="Selected"),
    )
    other_type = DataType(reference=old_reference)
    BaseModel(
        fields=[DataModelFieldBase(data_type=other_type)],
        reference=Reference(path="Other", original_name="Other", name="Other"),
    )

    assert not selected_field.self_reference()

    target_model.replace_children_in_models([selected_model], new_reference)

    assert selected_field.self_reference()
    assert selected_reference_type.reference is new_reference
    assert other_type.reference is old_reference
    assert [child is selected_reference_type for child in old_reference.children] == [False]
    assert [child is selected_reference_type for child in new_reference.children] == [True]


def test_replace_children_in_models_invalidates_direct_model_owner() -> None:
    """A redirected base-class reference refreshes its owning model's render identity."""
    old_reference = Reference(path="Old", original_name="Old", name="Old")
    new_reference = Reference(path="New", original_name="New", name="New")
    target_model = BaseModel(fields=[], reference=old_reference)
    selected_model = BaseModel(
        fields=[],
        base_classes=[old_reference],
        reference=Reference(path="Selected", original_name="Selected", name="Selected"),
    )
    base_class = selected_model.base_classes[0]
    shared_owner_model = BaseModel(
        fields=[],
        reference=Reference(path="SharedOwner", original_name="SharedOwner", name="SharedOwner"),
    )
    shared_owner_model.base_classes = [base_class]
    ignored_owner_model = BaseModel(
        fields=[],
        base_classes=[old_reference],
        reference=Reference(path="IgnoredOwner", original_name="IgnoredOwner", name="IgnoredOwner"),
    )
    ignored_base_class = ignored_owner_model.base_classes[0]
    original_key = selected_model.get_dedup_key()
    shared_owner_key = shared_owner_model.get_dedup_key()
    ignored_owner_key = ignored_owner_model.get_dedup_key()

    target_model.replace_children_in_models([selected_model, shared_owner_model], new_reference)

    assert base_class.reference is new_reference
    assert ignored_base_class.reference is old_reference
    assert selected_model.get_dedup_key() != original_key
    assert shared_owner_model.get_dedup_key() != shared_owner_key
    assert ignored_owner_model.get_dedup_key() == ignored_owner_key


def test_data_field() -> None:
    """Test DataModelFieldBase type hint generation for various configurations."""
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(is_list=True),
        required=True,
        is_list=True,
        is_union=True,
    )
    assert field.type_hint == "List"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(is_list=True),
        required=True,
        is_list=True,
        is_union=False,
    )
    assert field.type_hint == "List"
    field = DataModelFieldBase(name="a", data_type=DataType(), required=False)
    assert field.type_hint == "None"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(is_list=True),
        required=False,
        is_list=True,
        is_union=True,
    )
    assert field.type_hint == "Optional[List]"
    field = DataModelFieldBase(name="a", data_type=DataType(), required=False, is_list=False, is_union=True)
    assert field.type_hint == "None"
    field = DataModelFieldBase(name="a", data_type=DataType(), required=False, is_list=False, is_union=False)
    assert field.type_hint == "None"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(is_list=True),
        required=False,
        is_list=True,
        is_union=False,
    )
    assert field.type_hint == "Optional[List]"
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)
    assert field.type_hint == "str"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(type="str", is_list=True),
        required=True,
    )
    assert field.type_hint == "List[str]"
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)
    assert field.type_hint == "str"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(type="str"),
        required=True,
    )
    assert field.type_hint == "str"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(type="str", is_list=True),
        required=True,
    )
    assert field.type_hint == "List[str]"
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=False)
    assert field.type_hint == "Optional[str]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(
            type="str",
            is_list=True,
        ),
        required=False,
    )
    assert field.type_hint == "Optional[List[str]]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(type="str"),
        required=False,
    )
    assert field.type_hint == "Optional[str]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(type="str"),
        required=False,
    )
    assert field.type_hint == "Optional[str]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(
            type="str",
            is_list=True,
        ),
        required=False,
    )
    assert field.type_hint == "Optional[List[str]]"

    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int")]),
        required=True,
    )
    assert field.type_hint == "Union[str, int]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(
            data_types=[DataType(type="str"), DataType(type="int")],
            is_list=True,
        ),
        required=True,
    )
    assert field.type_hint == "List[Union[str, int]]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int")]),
        required=True,
    )
    assert field.type_hint == "Union[str, int]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int")]),
        required=True,
    )
    assert field.type_hint == "Union[str, int]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int")], is_list=True),
        required=True,
    )
    assert field.type_hint == "List[Union[str, int]]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int")]),
        required=False,
    )
    assert field.type_hint == "Optional[Union[str, int]]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(
            data_types=[DataType(type="str"), DataType(type="int")],
            is_list=True,
        ),
        required=False,
    )
    assert field.type_hint == "Optional[List[Union[str, int]]]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int")]),
        required=False,
    )
    assert field.type_hint == "Optional[Union[str, int]]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int")]),
        required=False,
    )
    assert field.type_hint == "Optional[Union[str, int]]"
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int")], is_list=True),
        required=False,
    )
    assert field.type_hint == "Optional[List[Union[str, int]]]"

    field = DataModelFieldBase(name="a", data_type=DataType(is_list=True), required=False)
    assert field.type_hint == "Optional[List]"


@pytest.mark.parametrize(
    "data_type",
    [
        DataType(data_types=[DataType(type="str")]),
        DataType(is_dict=True, dict_key=DataType(type="str")),
        DataType(literals=["value"]),
        DataType(enum_member_literals=[("EnumModel", "VALUE")]),
        DataType(type=ANY, is_optional=True),
    ],
)
def test_field_import_fast_path_skips_complex_data_types(data_type: DataType) -> None:
    """Test that complex DataTypes keep the side-effect-preserving import path."""
    field = DataModelFieldBase(name="a", data_type=data_type, required=True)

    assert field._can_collect_imports_without_type_hint(needs_annotated=False) is False


def test_field_import_fast_path_skips_annotated_fields() -> None:
    """Test that annotated fields keep the rendered type-hint import path."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)

    assert field._can_collect_imports_without_type_hint(needs_annotated=True) is False


def test_field_import_fast_path_skips_forward_reference_parent() -> None:
    """Test fields in forward-reference models keep rendered type-hint import detection."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=False)
    model = BaseModel(
        fields=[field],
        reference=Reference(path="Model", original_name="Model", name="Model"),
    )
    model.has_forward_reference = True

    assert field._can_collect_imports_without_type_hint(needs_annotated=False) is False


@pytest.mark.parametrize("type_name", ["Optional[str]", "Union[str, int]"])
def test_field_import_fast_path_skips_explicit_typing_names(type_name: str) -> None:
    """Test explicit typing names keep legacy import detection."""
    field = DataModelFieldBase(name="a", data_type=DataType(type=type_name), required=True)

    assert field._can_collect_imports_without_type_hint(needs_annotated=False) is False


@pytest.mark.parametrize(
    ("field", "expected_imports"),
    [
        (DataModelFieldBase(name="a", data_type=DataType(type="str"), required=False), (IMPORT_OPTIONAL,)),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                required=True,
                nullable=True,
            ),
            (IMPORT_OPTIONAL,),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                required=False,
                nullable=False,
            ),
            (),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str"),
                required=True,
                type_has_null=True,
            ),
            (IMPORT_OPTIONAL,),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str", is_optional=True),
                required=False,
            ),
            (IMPORT_OPTIONAL,),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="str", use_union_operator=True),
                required=False,
            ),
            (),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(type="Decimal", import_=IMPORT_DECIMAL),
                required=False,
            ),
            (IMPORT_DECIMAL, IMPORT_OPTIONAL),
        ),
        (DataModelFieldBase(name="a", data_type=DataType(), required=False), ()),
    ],
)
def test_field_import_fast_path_collects_simple_data_type_imports(
    field: DataModelFieldBase,
    expected_imports: tuple[Import, ...],
) -> None:
    """Test simple DataTypes collect imports without rendering type hints."""
    assert field.imports == expected_imports


def test_field_import_fast_path_collects_nullable_reference_import() -> None:
    """Test reference source nullability contributes Optional without rendering type hints."""
    reference = Reference(path="#/definitions/User", name="User")
    reference.source = ReferenceSource(nullable=True)
    field = DataModelFieldBase(name="user", data_type=DataType(reference=reference), required=True)

    assert field.imports == (IMPORT_OPTIONAL,)
    assert field.data_type.is_optional is False


def test_field_import_fast_path_ignores_nullable_alias_reference() -> None:
    """Test nullable aliases do not make the referencing field import Optional."""
    reference = Reference(path="#/definitions/UserAlias", name="UserAlias")
    reference.source = ReferenceSource(nullable=True, is_alias=True)
    field = DataModelFieldBase(name="user", data_type=DataType(reference=reference), required=True)

    assert field.imports == ()


def test_field_import_fallback_collects_annotated_import() -> None:
    """Test the fallback path includes Annotated when requested."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)

    assert field._collect_field_imports(needs_annotated=True) == (IMPORT_ANNOTATED,)


@pytest.mark.parametrize(
    ("type_name", "expected_imports"),
    [
        ("Optional[str]", (IMPORT_OPTIONAL,)),
        ("Union[str, int]", (IMPORT_UNION,)),
        ("Annotated[str, Field()]", (IMPORT_ANNOTATED,)),
    ],
)
def test_field_import_fallback_collects_explicit_typing_names(
    type_name: str,
    expected_imports: tuple[Import, ...],
) -> None:
    """Test explicit typing names still collect Optional and Union imports."""
    field = DataModelFieldBase(name="a", data_type=DataType(type=type_name), required=True)

    assert field.imports == expected_imports


def test_field_import_fallback_uses_structured_union_requirements(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test complex unions collect imports without scanning rendered type-hint text."""
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str"), DataType(type="int"), DataType(type=NONE)]),
        required=True,
    )

    def fail_type_hint(_self: DataModelFieldBase) -> str:  # pragma: no cover
        msg = "unexpected type_hint render"
        raise AssertionError(msg)

    monkeypatch.setattr(DataModelFieldBase, "type_hint", property(fail_type_hint))

    assert field.imports == (IMPORT_OPTIONAL, IMPORT_UNION)


@pytest.mark.parametrize(
    ("data_type", "expected_imports"),
    [
        (DataType(data_types=[DataType(type="str"), DataType(type=NONE)]), (IMPORT_OPTIONAL,)),
        (DataType(data_types=[DataType(type="str"), DataType(type="str")]), (IMPORT_OPTIONAL,)),
        (DataType(data_types=[DataType(type=NONE)]), ()),
        (DataType(data_types=[DataType(type=NONE), DataType(type=NONE)]), (IMPORT_ANY, IMPORT_OPTIONAL)),
        (DataType(data_types=[DataType(type="str")]), (IMPORT_OPTIONAL,)),
        (DataType(data_types=[DataType(type="str", discriminator="kind")]), (IMPORT_ANNOTATED, IMPORT_OPTIONAL)),
        (DataType(data_types=[DataType(type="str")], is_optional=True), (IMPORT_OPTIONAL,)),
    ],
)
def test_field_import_fallback_handles_structured_optional_edges(
    data_type: DataType,
    expected_imports: tuple[Import, ...],
) -> None:
    """Test structured import detection preserves Optional edge cases."""
    field = DataModelFieldBase(name="a", data_type=data_type, required=False)

    assert field.imports == expected_imports


def test_field_import_fallback_collects_explicit_typing_names_with_ast() -> None:
    """Test explicit type strings are parsed structurally for typing imports."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="list[Union[str, int]]"), required=True)

    assert field.imports == (IMPORT_UNION,)


def test_field_import_fallback_collects_dict_key_typing_names() -> None:
    """Test dict key annotations contribute structured typing imports."""
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(is_dict=True, dict_key=DataType(type="Optional[str]")),
        required=True,
    )

    assert field.imports == (IMPORT_DICT, IMPORT_OPTIONAL)


def test_field_import_fallback_collects_nullable_reference_in_union() -> None:
    """Test nullable references inside complex types contribute Optional structurally."""
    reference = Reference(path="#/definitions/User", name="User")
    reference.source = ReferenceSource(nullable=True)
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(reference=reference), DataType(type="int")]),
        required=True,
    )

    assert field.imports == (IMPORT_OPTIONAL, IMPORT_UNION)


def test_field_import_cache_normalizes_union_on_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test cached import lookup still applies union Optional side effects."""
    DataModelFieldBase._field_imports_cache.clear()
    try:
        primed_field = DataModelFieldBase(
            name="a",
            data_type=DataType(data_types=[DataType(type="str"), DataType(type=NONE)]),
            required=True,
        )

        assert primed_field.imports == (IMPORT_OPTIONAL,)
        assert primed_field.data_type.is_optional is True

        uncached = Mock(side_effect=AssertionError("unexpected uncached import collection"))
        monkeypatch.setattr(DataModelFieldBase, "_collect_field_imports_uncached", uncached)
        cached_field = DataModelFieldBase(
            name="a",
            data_type=DataType(data_types=[DataType(type="str"), DataType(type=NONE)]),
            required=True,
        )

        assert cached_field.data_type.is_optional is False
        assert cached_field.imports == (IMPORT_OPTIONAL,)
        assert cached_field.data_type.is_optional is True
        uncached.assert_not_called()
    finally:
        DataModelFieldBase._field_imports_cache.clear()


def test_field_import_cache_normalizes_nullable_reference_on_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test cached import lookup still applies reference nullable side effects."""
    DataModelFieldBase._field_imports_cache.clear()
    try:
        primed_reference = Reference(path="#/definitions/User", name="User")
        primed_reference.source = ReferenceSource(nullable=True)
        primed_field = DataModelFieldBase(
            name="user",
            data_type=DataType(data_types=[DataType(reference=primed_reference), DataType(type="int")]),
            required=True,
        )

        assert primed_field.imports == (IMPORT_OPTIONAL, IMPORT_UNION)
        assert primed_field.data_type.data_types[0].is_optional is True

        uncached = Mock(side_effect=AssertionError("unexpected uncached import collection"))
        monkeypatch.setattr(DataModelFieldBase, "_collect_field_imports_uncached", uncached)
        cached_reference = Reference(path="#/definitions/User", name="User")
        cached_reference.source = ReferenceSource(nullable=True)
        cached_field = DataModelFieldBase(
            name="user",
            data_type=DataType(data_types=[DataType(reference=cached_reference), DataType(type="int")]),
            required=True,
        )

        assert cached_field.data_type.data_types[0].is_optional is False
        assert cached_field.imports == (IMPORT_OPTIONAL, IMPORT_UNION)
        assert cached_field.data_type.data_types[0].is_optional is True
        uncached.assert_not_called()
    finally:
        DataModelFieldBase._field_imports_cache.clear()


def test_field_import_cache_evicts_oldest_entry() -> None:
    """Test the bounded field imports cache evicts the oldest entry."""
    DataModelFieldBase._field_imports_cache.clear()
    original_max_size = DataModelFieldBase._FIELD_IMPORTS_CACHE_MAX_SIZE
    try:
        DataModelFieldBase._FIELD_IMPORTS_CACHE_MAX_SIZE = 1
        field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)
        first_key: tuple[Any, ...] = ("first",)
        second_key: tuple[Any, ...] = ("second",)

        field._set_cached_field_imports(first_key, ())
        field._set_cached_field_imports(second_key, (IMPORT_OPTIONAL,))

        assert first_key not in DataModelFieldBase._field_imports_cache
        assert DataModelFieldBase._field_imports_cache[second_key] == (IMPORT_OPTIONAL,)
    finally:
        DataModelFieldBase._FIELD_IMPORTS_CACHE_MAX_SIZE = original_max_size
        DataModelFieldBase._field_imports_cache.clear()


@pytest.mark.parametrize(
    ("field", "expected_imports"),
    [
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(data_types=[DataType(type="str")]),
                required=True,
                nullable=True,
            ),
            (IMPORT_OPTIONAL,),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(data_types=[DataType(type="str")]),
                required=True,
                nullable=False,
            ),
            (),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(data_types=[DataType(type="str")]),
                required=True,
                type_has_null=True,
            ),
            (IMPORT_OPTIONAL,),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(data_types=[DataType(type="str")], use_union_operator=True),
                required=False,
            ),
            (),
        ),
        (
            DataModelFieldBase(
                name="a",
                data_type=DataType(data_types=[DataType(type="str")]),
                required=False,
                extras={"default_factory": "list"},
            ),
            (),
        ),
    ],
)
def test_field_import_fallback_handles_field_optional_structure(
    field: DataModelFieldBase,
    expected_imports: tuple[Import, ...],
) -> None:
    """Test field-level optional import decisions use field structure."""
    assert field.imports == expected_imports


def test_field_import_fallback_handles_unexpected_nullable_value() -> None:
    """Test defensive nullable matching keeps non-bool values from adding imports."""
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str")]),
        required=False,
    )
    field.nullable = object()  # type: ignore[assignment]

    assert field.imports == ()


def test_field_import_fallback_respects_union_operator_for_none_branch() -> None:
    """Test union operator mode does not add typing imports for None branches."""
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(
            data_types=[DataType(type="str"), DataType(type=NONE)],
            use_union_operator=True,
        ),
        required=True,
    )

    assert field.imports == ()


def test_field_import_fallback_keeps_union_operator_optional_in_forward_ref_model() -> None:
    """Test DataType-level union operator option still controls existing optional hints."""
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(data_types=[DataType(type="str")], is_optional=True, use_union_operator=True),
        required=False,
    )
    model = BaseModel(
        fields=[field],
        reference=Reference(path="Model", original_name="Model", name="Model"),
    )
    model.has_forward_reference = True

    assert field.imports == ()


def test_typing_import_requirements_ignore_unknown_import_name() -> None:
    """Test unknown annotation names leave structured import requirements unchanged."""
    requirements = _TypingImportRequirements(optional=True)

    assert requirements.with_import_name("Literal") is requirements


def test_annotation_typing_import_names_ignores_invalid_annotation() -> None:
    """Test invalid explicit type strings do not fall back to ad hoc string matching."""
    assert _annotation_typing_import_names("List[") == frozenset()


@pytest.mark.parametrize(
    ("annotation", "expected_names"),
    [
        ("str", frozenset()),
        ("Optional", frozenset({IMPORT_OPTIONAL.import_})),
    ],
)
def test_annotation_typing_import_names_handles_identifier_fast_path(
    annotation: str,
    expected_names: frozenset[str],
) -> None:
    """Test identifier annotations skip AST parsing unless they are typing imports."""
    assert _annotation_typing_import_names(annotation) == expected_names


@pytest.mark.parametrize(
    ("name", "expected_true", "expected_false"),
    [
        ("array-commons.schema", "array_commons.schema", "array_commons_schema"),
        ("123filename", "_123filename", "_123filename"),
        ("normal_filename", "normal_filename", "normal_filename"),
        ("file!name", "file_name", "file_name"),
        ("", "", ""),
    ],
)
@pytest.mark.parametrize("treat_dot_as_module", [True, False])
def test_sanitize_module_name(name: str, expected_true: str, expected_false: str, treat_dot_as_module: bool) -> None:
    """Test module name sanitization with different characters and options."""
    expected = expected_true if treat_dot_as_module else expected_false
    assert sanitize_module_name(name, treat_dot_as_module=treat_dot_as_module) == expected


@pytest.mark.parametrize(
    ("treat_dot_as_module", "expected"),
    [
        (True, ["inputs", "array_commons.schema", "array-commons"]),
        (False, ["inputs", "array_commons_schema"]),
    ],
)
def test_get_module_path_with_file_path(treat_dot_as_module: bool, expected: list[str]) -> None:
    """Test module path generation with a file path."""
    file_path = Path("inputs/array-commons.schema.json")
    result = get_module_path("array-commons.schema", file_path, treat_dot_as_module=treat_dot_as_module)
    assert result == expected


def test_get_module_path_without_file_path_treat_dot_true() -> None:
    """Test module path generation without a file path with treat_dot_as_module=True."""
    result = get_module_path("my_module.submodule", None, treat_dot_as_module=True)
    expected = ["my_module"]
    assert result == expected


def test_get_module_path_without_file_path_treat_dot_false() -> None:
    """Test module path generation without a file path with treat_dot_as_module=False."""
    result = get_module_path("my_module.submodule", None, treat_dot_as_module=False)
    expected: list[str] = []
    assert result == expected


@pytest.mark.parametrize(
    ("treat_dot_as_module", "name", "expected"),
    [
        (True, "a.b.c", ["a", "b"]),
        (True, "simple", []),
        (True, "with.dot", ["with"]),
        (False, "a.b.c", []),
        (False, "simple", []),
        (False, "with.dot", []),
    ],
)
def test_get_module_path_without_file_path_parametrized(
    treat_dot_as_module: bool, name: str, expected: list[str]
) -> None:
    """Test module path generation without file path for various module names."""
    result = get_module_path(name, None, treat_dot_as_module=treat_dot_as_module)
    assert result == expected


def test_copy_deep_with_dict_key() -> None:
    """Test that copy_deep properly copies dict key and value types."""
    dict_key_type = DataType(type="str")
    dict_value_type = DataType(type="str")
    data_type = DataType(data_types=[dict_value_type], is_dict=True, dict_key=dict_key_type)
    field = DataModelFieldBase(name="a", data_type=data_type, required=True)

    copied = field.copy_deep()

    assert copied.data_type.dict_key is not None
    assert copied.data_type.dict_key is not field.data_type.dict_key
    assert copied.data_type.dict_key.type == "str"
    assert copied.data_type.data_types[0] is not dict_value_type
    copied.data_type.data_types[0].type = "int"
    assert dict_value_type.type == "str"


def test_copy_deep_with_extras() -> None:
    """Test that copy_deep properly deep copies extras."""
    field = DataModelFieldBase(
        name="a",
        data_type=DataType(type="str"),
        required=True,
        extras={"key": "value", "nested": {"inner": 1}},
    )

    copied = field.copy_deep()

    assert copied.extras is not field.extras
    assert copied.extras == {"key": "value", "nested": {"inner": 1}}
    copied.extras["key"] = "modified"
    assert field.extras["key"] == "value"


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (None, None),
        ("", ""),
        ("no special chars", "no special chars"),
        # Backslash escaping
        (r"backslash \ here", r"backslash \\ here"),
        (r"path C:\Users\name", r"path C:\\Users\\name"),
        (r"escape \n sequence", r"escape \\n sequence"),
        # Triple quote escaping
        ('"""', r"\"\"\""),
        ('contains """quotes"""', r"contains \"\"\"quotes\"\"\""),
        # Both backslash and triple quotes
        (r'both \ and """', r"both \\ and \"\"\""),
        (r'path C:\"""file"""', r"path C:\\\"\"\"file\"\"\""),
    ],
)
def test_escape_docstring(input_value: str | None, expected: str | None) -> None:
    """Test escape_docstring properly escapes special characters.

    This tests issue #1808 where backslashes and triple quotes in docstrings
    were not escaped, causing Python syntax errors and type checker warnings.
    """
    assert escape_docstring(input_value) == expected


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (None, None),
        ("", ""),
        ("plain text", "plain text"),
        # LF is already handled by the union templates.
        ("line one\nline two", "line one\nline two"),
        ("a\nb\nc", "a\nb\nc"),
        # CR and CRLF must be normalized before template rendering.
        ("line one\rline two", "line one\nline two"),
        ("line one\r\nline two", "line one\nline two"),
        ("a\r\nb\nc\rd", "a\nb\nc\nd"),
        (
            "Color union\rprint('PWNED')",
            "Color union\nprint('PWNED')",
        ),
    ],
)
def test_comment_safe(input_value: str | None, expected: str | None) -> None:
    """Test comment_safe line ending normalization."""
    assert comment_safe(input_value) == expected


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (None, None),
        ("", ""),
        ("plain text", "plain text"),
        ("line one\nline two", "line one\n# line two"),
        ("line one\rline two", "line one\n# line two"),
        ("line one\r\nline two", "line one\n# line two"),
        ("line one\vline two", "line one\n# line two"),
        ("line one\fline two", "line one\n# line two"),
        ("a\r\nb\nc\rd\ve\ff", "a\n# b\n# c\n# d\n# e\n# f"),
    ],
)
def test_inline_comment_safe(input_value: str | None, expected: str | None) -> None:
    """Test inline comment escaping."""
    assert inline_comment_safe(input_value) == expected


def test_format_docstring_uses_multiline_format_by_default() -> None:
    """Test format_docstring preserves historical multi-line formatting by default."""
    assert format_docstring("Description", 4) == '"""\n    Description\n    """'


@pytest.mark.parametrize("empty_value", [None, "", "   "])
def test_format_docstring_returns_empty_string_for_empty_values(empty_value: str | None) -> None:
    """Test format_docstring returns an empty string for empty values."""
    assert not format_docstring(empty_value, 4)


def test_format_docstring_uses_single_line_when_enabled() -> None:
    """Test format_docstring emits one-line docstrings when enabled."""
    assert format_docstring("Description", 4, use_single_line_docstring=True) == '"""Description"""'


def test_format_docstring_escapes_trailing_quote_without_changing_docstring() -> None:
    """Test one-line docstrings ending with a quote preserve their value."""
    assert format_docstring('Description"', 4, use_single_line_docstring=True) == r'"""Description\""""'


def test_format_docstring_escapes_single_quote_docstring() -> None:
    """Test a docstring consisting only of a quote is escaped."""
    assert format_docstring('"', 4, use_single_line_docstring=True) == r'"""\""""'


def test_format_docstring_keeps_escaped_triple_quotes_without_extra_escape() -> None:
    """Test escaped triple quotes at the end are not double-escaped."""
    assert format_docstring('Description """', 4, use_single_line_docstring=True) == r'"""Description \"\"\""""'


def test_inline_field_docstring_escapes_special_chars() -> None:
    """Test inline_field_docstring property escapes special characters."""
    field = DataModelFieldBase(
        name="test_field",
        data_type=DataType(type="str"),
        required=True,
        extras={"description": r"Path like C:\Users\name"},
        use_inline_field_description=True,
    )
    assert field.inline_field_docstring == r'"""Path like C:\\Users\\name"""'


def test_inline_field_docstring_escapes_triple_quotes() -> None:
    """Test inline_field_docstring property escapes triple quotes."""
    field = DataModelFieldBase(
        name="test_field",
        data_type=DataType(type="str"),
        required=True,
        extras={"description": 'Contains """quotes"""'},
        use_inline_field_description=True,
    )
    assert field.inline_field_docstring == r'"""Contains \"\"\"quotes\"\"\""""'


def test_data_type_manager_unknown_type_raises_error() -> None:
    """Test DataTypeManager raises NotImplementedError for unknown types."""
    from datamodel_code_generator.model.types import DataTypeManager

    manager = DataTypeManager()
    del manager.type_map[Types.path]

    with pytest.raises(NotImplementedError, match="Type mapping for 'path' not implemented"):
        manager.get_data_type(Types.path)


def test_data_type_manager_has_all_types() -> None:
    """Test DataTypeManager has mappings for all Types enum members."""
    from datamodel_code_generator.model.types import DataTypeManager

    manager = DataTypeManager()
    missing_types = [t for t in Types if t not in manager.type_map]
    assert not missing_types, f"Missing type mappings: {[t.name for t in missing_types]}"


def test_data_type_manager_returns_copied_type_map_entries() -> None:
    """Type map entries are reusable prototypes, not caller-owned objects."""
    from datamodel_code_generator.model.types import DataTypeManager

    manager = DataTypeManager()

    integer_type = manager.get_data_type(Types.integer)
    int64_type = manager.get_data_type(Types.int64)
    integer_type.alias = "CustomInt"

    assert integer_type is not int64_type
    assert int64_type.alias is None


def test_data_type_manager_returns_copied_nested_type_map_entries() -> None:
    """Nested data types from map prototypes should not be shared between callers."""
    from datamodel_code_generator.model.types import DataTypeManager

    manager = DataTypeManager()

    array_type = manager.get_data_type(Types.array)
    another_array_type = manager.get_data_type(Types.array)
    array_type.data_types[0].alias = "CustomItem"

    assert array_type is not another_array_type
    assert array_type.data_types[0] is not another_array_type.data_types[0]
    assert another_array_type.data_types[0].alias is None
