"""Tests for base parser classes and utilities."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any
from unittest.mock import MagicMock

import pytest

from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.pydantic import BaseModel, DataModelField
from datamodel_code_generator.model.type_alias import TypeAlias, TypeAliasTypeBackport, TypeStatement
from datamodel_code_generator.parser.base import (
    Parser,
    add_model_path_to_list,
    escape_characters,
    exact_import,
    get_module_directory,
    relative,
    sort_data_models,
    to_hashable,
)
from datamodel_code_generator.reference import Reference, snake_to_upper_camel
from datamodel_code_generator.types import DataType


class A(DataModel):
    """Test data model class A."""


class B(DataModel):
    """Test data model class B."""


class C(Parser):
    """Test parser class C."""

    def parse_raw(self, name: str, raw: dict[str, Any]) -> None:
        """Parse raw data into models."""

    def parse(self) -> str:
        """Parse and return results."""
        return "parsed"


def test_parser() -> None:
    """Test parser initialization."""
    c = C(
        data_model_type=D,
        data_model_root_type=B,
        data_model_field_type=DataModelFieldBase,
        base_class="Base",
        source="",
    )
    assert c.data_model_type == D
    assert c.data_model_root_type == B
    assert c.data_model_field_type == DataModelFieldBase
    assert c.base_class == "Base"


def test_add_model_path_to_list() -> None:
    """Test method which adds model paths to "update" list."""
    reference_1 = Reference(path="Base1", original_name="A", name="A")
    reference_2 = Reference(path="Alias2", original_name="B", name="B")
    reference_3 = Reference(path="Alias3", original_name="B", name="B")
    reference_4 = Reference(path="Alias4", original_name="B", name="B")
    reference_5 = Reference(path="Alias5", original_name="B", name="B")
    model1 = BaseModel(fields=[], reference=reference_1)
    model2 = TypeAlias(fields=[], reference=reference_2)
    model3 = TypeAlias(fields=[], reference=reference_3)
    model4 = TypeAliasTypeBackport(fields=[], reference=reference_4)
    model5 = TypeStatement(fields=[], reference=reference_5)

    paths = add_model_path_to_list(None, model1)
    assert "Base1" in paths
    assert len(paths) == 1

    paths = list[str]()
    add_model_path_to_list(paths, model1)
    assert "Base1" in paths
    assert len(paths) == 1

    add_model_path_to_list(paths, model1)
    assert len(paths) != 2
    assert len(paths) == 1

    add_model_path_to_list(paths, model2)
    assert "Alias2" not in paths

    add_model_path_to_list(paths, model3)
    assert "Alias3" not in paths

    add_model_path_to_list(paths, model4)
    assert "Alias4" not in paths

    add_model_path_to_list(paths, model5)
    assert "Alias5" not in paths


def test_sort_data_models() -> None:
    """Test sorting data models by dependencies."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    reference_c = Reference(path="C", original_name="C", name="C")
    data_type_a = DataType(reference=reference_a)
    data_type_b = DataType(reference=reference_b)
    data_type_c = DataType(reference=reference_c)
    reference = [
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelFieldBase(data_type=data_type_c),
            ],
            reference=reference_a,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)],
            reference=reference_b,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)],
            reference=reference_c,
        ),
    ]

    unresolved, resolved, require_update_action_models = sort_data_models(reference)
    expected = OrderedDict()
    expected["B"] = reference[1]
    expected["C"] = reference[2]
    expected["A"] = reference[0]

    assert resolved == expected
    assert unresolved == []
    assert require_update_action_models == ["B", "A"]


def test_sort_data_models_unresolved() -> None:
    """Test sorting data models with unresolved references."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    reference_c = Reference(path="C", original_name="C", name="C")
    reference_d = Reference(path="D", original_name="D", name="D")
    reference_v = Reference(path="V", original_name="V", name="V")
    reference_z = Reference(path="Z", original_name="Z", name="Z")
    data_type_a = DataType(reference=reference_a)
    data_type_b = DataType(reference=reference_b)
    data_type_c = DataType(reference=reference_c)
    data_type_v = DataType(reference=reference_v)
    data_type_z = DataType(reference=reference_z)
    reference = [
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelFieldBase(data_type=data_type_c),
            ],
            reference=reference_a,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)],
            reference=reference_b,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)],
            reference=reference_c,
        ),
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelField(data_type=data_type_c),
                DataModelField(data_type=data_type_z),
            ],
            reference=reference_d,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_v)],
            reference=reference_z,
        ),
    ]

    with pytest.raises(Exception):  # noqa: B017, PT011
        sort_data_models(reference)


def test_sort_data_models_unresolved_raise_recursion_error() -> None:
    """Test sorting data models raises error on recursion limit."""
    reference_a = Reference(path="A", original_name="A", name="A")
    reference_b = Reference(path="B", original_name="B", name="B")
    reference_c = Reference(path="C", original_name="C", name="C")
    reference_d = Reference(path="D", original_name="D", name="D")
    reference_v = Reference(path="V", original_name="V", name="V")
    reference_z = Reference(path="Z", original_name="Z", name="Z")
    data_type_a = DataType(reference=reference_a)
    data_type_b = DataType(reference=reference_b)
    data_type_c = DataType(reference=reference_c)
    data_type_v = DataType(reference=reference_v)
    data_type_z = DataType(reference=reference_z)
    reference = [
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelFieldBase(data_type=data_type_c),
            ],
            reference=reference_a,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)],
            reference=reference_b,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)],
            reference=reference_c,
        ),
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelField(data_type=data_type_c),
                DataModelField(data_type=data_type_z),
            ],
            reference=reference_d,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_v)],
            reference=reference_z,
        ),
    ]

    with pytest.raises(Exception):  # noqa: B017, PT011
        sort_data_models(reference, recursion_count=100000)


@pytest.mark.parametrize(
    ("current_module", "reference", "val"),
    [
        ("", "Foo", ("", "")),
        ("a", "a.Foo", ("", "")),
        ("a", "a.b.Foo", (".", "b")),
        ("a.b", "a.Foo", (".", "Foo")),
        ("a.b.c", "a.Foo", ("..", "Foo")),
        ("a.b.c", "Foo", ("...", "Foo")),
    ],
)
def test_relative(current_module: str, reference: str, val: tuple[str, str]) -> None:
    """Test relative import calculation."""
    assert relative(current_module, reference) == val


@pytest.mark.parametrize(
    ("from_", "import_", "name", "val"),
    [
        (".", "mod", "Foo", (".mod", "Foo")),
        ("..", "mod", "Foo", ("..mod", "Foo")),
        (".a", "mod", "Foo", (".a.mod", "Foo")),
        ("..a", "mod", "Foo", ("..a.mod", "Foo")),
        ("..a.b", "mod", "Foo", ("..a.b.mod", "Foo")),
    ],
)
def test_exact_import(from_: str, import_: str, name: str, val: tuple[str, str]) -> None:
    """Test exact import formatting."""
    assert exact_import(from_, import_, name) == val


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        (
            "_hello",
            "_Hello",
        ),  # In case a name starts with a underline, we should keep it.
        ("hello_again", "HelloAgain"),  # regular snake case
        ("hello__again", "HelloAgain"),  # handles double underscores
        (
            "hello___again_again",
            "HelloAgainAgain",
        ),  # handles double and single underscores
        ("hello_again_", "HelloAgain"),  # handles trailing underscores
        ("hello", "Hello"),  # no underscores
        ("____", "_"),  # degenerate case, but this is the current expected behavior
    ],
)
def test_snake_to_upper_camel(word: str, expected: str) -> None:
    """Tests the snake to upper camel function."""
    actual = snake_to_upper_camel(word)
    assert actual == expected


class D(DataModel):
    """Test data model class D with custom render."""

    def __init__(self, filename: str, data: str, fields: list[DataModelFieldBase]) -> None:  # noqa: ARG002
        """Initialize data model with custom data."""
        super().__init__(fields=fields, reference=Reference(""))
        self._data = data

    def render(self) -> str:
        """Render the data model."""
        return self._data


@pytest.fixture
def parser_fixture() -> C:
    """Create a test parser instance for unit tests."""
    return C(
        data_model_type=D,
        data_model_root_type=B,
        data_model_field_type=DataModelFieldBase,
        base_class="Base",
        source="",
    )


def test_additional_imports() -> None:
    """Test that additional imports are inside imports container."""
    new_parser = C(
        source="",
        additional_imports=["collections.deque"],
    )
    assert len(new_parser.imports) == 1
    assert new_parser.imports["collections"] == {"deque"}


def test_no_additional_imports() -> None:
    """Test that not additional imports are not affecting imports container."""
    new_parser = C(
        source="",
    )
    assert len(new_parser.imports) == 0


@pytest.mark.parametrize(
    ("input_data", "expected"),
    [
        (
            {
                ("folder1", "module1.py"): "content1",
                ("folder1", "module2.py"): "content2",
                ("folder1", "__init__.py"): "init_content",
            },
            {
                ("folder1", "module1.py"): "content1",
                ("folder1", "module2.py"): "content2",
                ("folder1", "__init__.py"): "init_content",
            },
        ),
        (
            {
                ("folder1.module", "file.py"): "content1",
                ("folder1.module", "__init__.py"): "init_content",
            },
            {
                ("folder1", "module", "file.py"): "content1",
                ("folder1", "__init__.py"): "init_content",
                ("folder1", "module", "__init__.py"): "init_content",
            },
        ),
    ],
)
def test_postprocess_result_modules(input_data: Any, expected: Any) -> None:
    """Test postprocessing of result modules."""
    result = Parser._Parser__postprocess_result_modules(input_data)
    assert result == expected


def test_find_member_with_integer_enum() -> None:
    """Test find_member method with integer enum values."""
    from datamodel_code_generator.model.enum import Enum
    from datamodel_code_generator.model.pydantic.base_model import DataModelField
    from datamodel_code_generator.reference import Reference
    from datamodel_code_generator.types import DataType

    # Create test Enum with integer values
    enum = Enum(
        reference=Reference(path="test_path", original_name="TestEnum", name="TestEnum"),
        fields=[
            DataModelField(
                name="VALUE_1000",
                default="1000",
                data_type=DataType(type="int"),
                required=True,
            ),
            DataModelField(
                name="VALUE_100",
                default="100",
                data_type=DataType(type="int"),
                required=True,
            ),
            DataModelField(
                name="VALUE_0",
                default="0",
                data_type=DataType(type="int"),
                required=True,
            ),
        ],
    )

    # Test finding members with integer values
    assert enum.find_member(1000).field.name == "VALUE_1000"
    assert enum.find_member(100).field.name == "VALUE_100"
    assert enum.find_member(0).field.name == "VALUE_0"

    # Test with string representations
    assert enum.find_member("1000").field.name == "VALUE_1000"
    assert enum.find_member("100").field.name == "VALUE_100"
    assert enum.find_member("0").field.name == "VALUE_0"

    # Test with non-existent values
    assert enum.find_member(999) is None
    assert enum.find_member("999") is None


def test_find_member_with_string_enum() -> None:
    """Test find_member method with string enum values."""
    from datamodel_code_generator.model.enum import Enum
    from datamodel_code_generator.model.pydantic.base_model import DataModelField
    from datamodel_code_generator.reference import Reference
    from datamodel_code_generator.types import DataType

    enum = Enum(
        reference=Reference(path="test_path", original_name="TestEnum", name="TestEnum"),
        fields=[
            DataModelField(
                name="VALUE_A",
                default="'value_a'",
                data_type=DataType(type="str"),
                required=True,
            ),
            DataModelField(
                name="VALUE_B",
                default="'value_b'",
                data_type=DataType(type="str"),
                required=True,
            ),
        ],
    )

    member = enum.find_member("value_a")
    assert member is not None
    assert member.field.name == "VALUE_A"

    member = enum.find_member("value_b")
    assert member is not None
    assert member.field.name == "VALUE_B"

    member = enum.find_member("'value_a'")
    assert member is not None
    assert member.field.name == "VALUE_A"


def test_find_member_with_mixed_enum() -> None:
    """Test find_member method with mixed type enum values."""
    from datamodel_code_generator.model.enum import Enum
    from datamodel_code_generator.model.pydantic.base_model import DataModelField
    from datamodel_code_generator.reference import Reference
    from datamodel_code_generator.types import DataType

    enum = Enum(
        reference=Reference(path="test_path", original_name="TestEnum", name="TestEnum"),
        fields=[
            DataModelField(
                name="INT_VALUE",
                default="100",
                data_type=DataType(type="int"),
                required=True,
            ),
            DataModelField(
                name="STR_VALUE",
                default="'value_a'",
                data_type=DataType(type="str"),
                required=True,
            ),
        ],
    )

    member = enum.find_member(100)
    assert member is not None
    assert member.field.name == "INT_VALUE"

    member = enum.find_member("100")
    assert member is not None
    assert member.field.name == "INT_VALUE"

    member = enum.find_member("value_a")
    assert member is not None
    assert member.field.name == "STR_VALUE"

    member = enum.find_member("'value_a'")
    assert member is not None
    assert member.field.name == "STR_VALUE"


@pytest.fixture
def escape_map() -> dict[str, str]:
    """Provide escape character mapping for tests."""
    return {
        "\u0000": r"\x00",  # Null byte
        "'": r"\'",
        "\b": r"\b",
        "\f": r"\f",
        "\n": r"\n",
        "\r": r"\r",
        "\t": r"\t",
        "\\": r"\\",
    }


@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ("\u0000", r"\x00"),  # Test null byte
        ("'", r"\'"),  # Test single quote
        ("\b", r"\b"),  # Test backspace
        ("\f", r"\f"),  # Test form feed
        ("\n", r"\n"),  # Test newline
        ("\r", r"\r"),  # Test carriage return
        ("\t", r"\t"),  # Test tab
        ("\\", r"\\"),  # Test backslash
    ],
)
def test_character_escaping(input_str: str, expected: str) -> None:
    """Test character escaping in strings."""
    assert input_str.translate(escape_characters) == expected


@pytest.mark.parametrize("flag", [True, False])
def test_use_non_positive_negative_number_constrained_types(flag: bool) -> None:
    """Test configuration of non-positive negative number constrained types."""
    instance = C(source="", use_non_positive_negative_number_constrained_types=flag)

    assert instance.data_type_manager.use_non_positive_negative_number_constrained_types == flag


def test_to_hashable_simple_values() -> None:
    """Test to_hashable with simple values."""
    assert to_hashable("string") == "string"
    assert to_hashable(123) == 123
    assert to_hashable(None) == ""  # noqa: PLC1901


def test_to_hashable_list_and_tuple() -> None:
    """Test to_hashable with list and tuple."""
    result = to_hashable([3, 1, 2])
    assert isinstance(result, tuple)
    assert result == (1, 2, 3)  # sorted

    result = to_hashable((3, 1, 2))
    assert isinstance(result, tuple)
    assert result == (1, 2, 3)  # sorted


def test_to_hashable_dict() -> None:
    """Test to_hashable with dict."""
    result = to_hashable({"b": 2, "a": 1})
    assert isinstance(result, tuple)
    # sorted by key
    assert result == (("a", 1), ("b", 2))


def test_to_hashable_mixed_types_fallback() -> None:
    """Test to_hashable with mixed types that cannot be compared."""
    mixed_list = [complex(1, 2), complex(3, 4)]
    result = to_hashable(mixed_list)
    assert isinstance(result, tuple)
    # Should preserve order since sorting fails
    assert result == (complex(1, 2), complex(3, 4))


def test_to_hashable_nested_structures() -> None:
    """Test to_hashable with nested structures."""
    nested = {"outer": [{"inner": 1}]}
    result = to_hashable(nested)
    assert isinstance(result, tuple)


def test_postprocess_result_modules_single_element_tuple() -> None:
    """Test postprocessing with single element tuple (len < 2)."""
    input_data = {
        ("__init__.py",): "init_content",
    }
    result = Parser._Parser__postprocess_result_modules(input_data)
    # Single element tuple should remain unchanged
    assert ("__init__.py",) in result


def test_postprocess_result_modules_single_file_no_dot() -> None:
    """Test postprocessing with single file without dot in name."""
    input_data = {
        ("module.py",): "content",
        ("__init__.py",): "init_content",
    }
    result = Parser._Parser__postprocess_result_modules(input_data)
    assert ("module.py",) in result


def test_postprocess_result_modules_single_element_no_dot() -> None:
    """Test postprocessing with single element without dot (len(r) < 2 branch)."""
    input_data = {
        ("__init__.py",): "init_content",
        ("file",): "content",  # Single element without dot, so len(r) = 1
    }
    result = Parser._Parser__postprocess_result_modules(input_data)
    assert ("file",) in result


@pytest.mark.parametrize(
    ("module", "expected"),
    [
        ((), ()),  # empty
        (("pkg",), ("pkg",)),  # single
        (("pkg", "issuing"), ("pkg",)),  # submodule
        (("foo", "bar", "baz"), ("foo", "bar")),  # deeply nested
    ],
    ids=["empty", "single", "submodule", "deeply_nested"],
)
def test_get_module_directory(module: tuple[str, ...], expected: tuple[str, ...]) -> None:
    """Test get_module_directory with various inputs."""
    assert get_module_directory(module) == expected


@pytest.mark.parametrize(
    ("scc_modules", "existing_modules", "expected"),
    [
        # name conflict: _internal already exists
        ({(), ("sub",)}, {("_internal",)}, ("_internal_1",)),
        # multiple conflicts: _internal and _internal_1 exist
        ({(), ("sub",)}, {("_internal",), ("_internal_1",)}, ("_internal_2",)),
        # different prefix break: LCP computation hits break
        ({("common", "a"), ("common", "b"), ("other", "x")}, set(), ("_internal",)),
    ],
    ids=["name_conflict", "multiple_conflicts", "different_prefix_break"],
)
def test_compute_internal_module_path(
    parser_fixture: C,
    scc_modules: set[tuple[str, ...]],
    existing_modules: set[tuple[str, ...]],
    expected: tuple[str, ...],
) -> None:
    """Test __compute_internal_module_path with various conflict scenarios."""
    result = parser_fixture._Parser__compute_internal_module_path(scc_modules, existing_modules)
    assert result == expected


def test_build_module_dependency_graph_with_missing_ref(parser_fixture: C) -> None:
    """Test __build_module_dependency_graph when reference path is not in path_to_module."""
    ref_source = MagicMock()
    ref_source.source = True
    ref_source.path = "nonexistent.Model"

    data_type = MagicMock()
    data_type.reference = ref_source

    model1 = MagicMock()
    model1.path = "pkg.Model1"
    model1.all_data_types = [data_type]
    model1.base_classes = []

    module_models_list = [
        (("pkg",), [model1]),
    ]

    graph = parser_fixture._Parser__build_module_dependency_graph(module_models_list)

    assert graph == {("pkg",): set()}
