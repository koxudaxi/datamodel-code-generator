"""Tests for base model classes and utilities."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pytest

from datamodel_code_generator.model.base import (
    DataModel,
    DataModelFieldBase,
    TemplateBase,
    comment_safe,
    escape_docstring,
    format_docstring,
    get_module_path,
    inline_comment_safe,
    sanitize_module_name,
)
from datamodel_code_generator.model.pydantic_v2 import BaseModel
from datamodel_code_generator.model.pydantic_v2 import DataModelField as PydanticV2DataModelField
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, Types


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


def test_pydantic_v2_extra_type_hint_keeps_non_dict_hint() -> None:
    """Test typed-extra type hint conversion leaves non-dict hints unchanged."""
    field = PydanticV2DataModelField(
        name="__pydantic_extra__",
        data_type=DataType(type="str"),
        required=True,
    )

    assert field.pydantic_extra_type_hint == "str"


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
    new_reference = Reference(path="New", original_name="New", name="New")
    target_model = BaseModel(fields=[], reference=old_reference)
    selected_type = DataType(reference=old_reference)
    selected_model = BaseModel(
        fields=[DataModelFieldBase(data_type=selected_type)],
        reference=Reference(path="Selected", original_name="Selected", name="Selected"),
    )
    other_type = DataType(reference=old_reference)
    BaseModel(
        fields=[DataModelFieldBase(data_type=other_type)],
        reference=Reference(path="Other", original_name="Other", name="Other"),
    )

    target_model.replace_children_in_models([selected_model], new_reference)

    assert selected_type.reference is new_reference
    assert other_type.reference is old_reference
    assert [child is selected_type for child in old_reference.children] == [False]
    assert [child is selected_type for child in new_reference.children] == [True]


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
    """Test that copy_deep properly copies dict_key."""
    dict_key_type = DataType(type="str")
    data_type = DataType(is_dict=True, dict_key=dict_key_type)
    field = DataModelFieldBase(name="a", data_type=data_type, required=True)

    copied = field.copy_deep()

    assert copied.data_type.dict_key is not None
    assert copied.data_type.dict_key is not field.data_type.dict_key
    assert copied.data_type.dict_key.type == "str"


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
