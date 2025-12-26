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
    escape_docstring,
    get_module_path,
    sanitize_module_name,
)
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

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:  # noqa: D102
        pass

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
        super().__init__(*args, **kwargs)

    TEMPLATE_FILE_PATH = ""


class C(DataModel):
    """Test helper class for DataModel testing without template path."""

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:  # noqa: D102
        pass


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


def test_data_model_exception() -> None:
    """Test DataModel raises exception when TEMPLATE_FILE_PATH is undefined."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), default="abc", required=True)
    with pytest.raises(Exception, match="TEMPLATE_FILE_PATH is undefined"):
        C(
            fields=[field],
            reference=Reference(path="abc", original_name="abc", name="abc"),
        )


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
