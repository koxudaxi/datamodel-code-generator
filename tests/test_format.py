"""Tests for code formatting functionality."""

from __future__ import annotations

import ast
import sys
import warnings
from pathlib import Path
from unittest import mock

import black
import isort
import pytest

from datamodel_code_generator.format import (
    CodeFormatter,
    Formatter,
    PythonVersion,
    PythonVersionMin,
    _format_import_node,
    _warn_default_formatters_deprecation,
    apply_builtin_formatter,
    resolve_use_type_checking_imports,
)

EXAMPLE_LICENSE_FILE = str(Path(__file__).parent / "data/python/custom_formatters/license_example.txt")

UN_EXIST_FORMATTER = "tests.data.python.custom_formatters.un_exist"
WRONG_FORMATTER = "tests.data.python.custom_formatters.wrong"
NOT_SUBCLASS_FORMATTER = "tests.data.python.custom_formatters.not_subclass"
ADD_COMMENT_FORMATTER = "tests.data.python.custom_formatters.add_comment"
ADD_LICENSE_FORMATTER = "tests.data.python.custom_formatters.add_license"
FAKE_RUFF_PATH = "/opt/fake-ruff/bin/ruff"
BLACK_VERSION_DEPENDENT_NORMALIZED_EXPECTED_FILES = {
    "main/openapi/custom_file_header_with_docstring_and_import.py",
}


def test_python_version() -> None:
    """Ensure that the python version used for the tests is properly listed."""
    _ = PythonVersion("{}.{}".format(*sys.version_info[:2]))


def test_python_version_has_native_deferred_annotations() -> None:
    """Test that has_native_deferred_annotations returns correct values for each Python version."""
    assert not PythonVersion.PY_310.has_native_deferred_annotations
    assert not PythonVersion.PY_311.has_native_deferred_annotations
    assert not PythonVersion.PY_312.has_native_deferred_annotations
    assert not PythonVersion.PY_313.has_native_deferred_annotations
    assert PythonVersion.PY_314.has_native_deferred_annotations


@pytest.mark.parametrize(
    ("skip_string_normalization", "expected_output"),
    [
        (True, "a = 'b'"),
        (False, 'a = "b"'),
    ],
)
def test_format_code_with_skip_string_normalization(
    skip_string_normalization: bool,
    expected_output: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test code formatting with skip string normalization option."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        skip_string_normalization=skip_string_normalization,
        formatters=[Formatter.BLACK, Formatter.ISORT],
    )

    formatted_code = formatter.format_code("a = 'b'")

    assert formatted_code == expected_output + "\n"


def test_format_code_builtin_formatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test dependency-free built-in formatting."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
    )

    formatted_code = formatter.format_code(
        "from pydantic import Field, BaseModel\n"
        "import sys\n"
        "from __future__ import annotations\n"
        "from .models import Pet\n"
        "\n"
        "class Model(BaseModel):\n"
        "    pet: Pet\n"
        "    name: str = Field(...)\n"
    )

    assert (
        formatted_code == "from __future__ import annotations\n"
        "\n"
        "import sys\n"
        "\n"
        "from pydantic import BaseModel, Field\n"
        "\n"
        "from .models import Pet\n"
        "\n"
        "\n"
        "class Model(BaseModel):\n"
        "    pet: Pet\n"
        "    name: str = Field(...)\n"
    )


def test_format_code_builtin_formatter_uses_explicit_line_length(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test built-in formatter uses explicit line length configuration."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 88\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
        builtin_format_line_length=140,
    )

    formatted_code = formatter.format_code(
        "from module import Zed, ExtremelyLongGeneratedTypeName, AnotherLongGeneratedTypeName, "
        "GeneratedTypeNameThatFitsWithinConfiguredLineLength\n"
    )

    assert (
        formatted_code == "from module import AnotherLongGeneratedTypeName, ExtremelyLongGeneratedTypeName, "
        "GeneratedTypeNameThatFitsWithinConfiguredLineLength, Zed\n"
    )


def test_format_code_builtin_formatter_uses_datamodel_codegen_line_length(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test built-in formatter uses datamodel-codegen line length configuration."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.datamodel-codegen]\nbuiltin-format-line-length = 140\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
    )

    formatted_code = formatter.format_code(
        "from module import Zed, ExtremelyLongGeneratedTypeName, AnotherLongGeneratedTypeName, "
        "GeneratedTypeNameThatFitsWithinConfiguredLineLength\n"
    )

    assert (
        formatted_code == "from module import AnotherLongGeneratedTypeName, ExtremelyLongGeneratedTypeName, "
        "GeneratedTypeNameThatFitsWithinConfiguredLineLength, Zed\n"
    )


def test_format_code_builtin_formatter_falls_back_to_ruff_line_length(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test built-in formatter falls back to Ruff line length configuration."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 140\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
    )

    formatted_code = formatter.format_code(
        "from module import Zed, ExtremelyLongGeneratedTypeName, AnotherLongGeneratedTypeName, "
        "GeneratedTypeNameThatFitsWithinConfiguredLineLength\n"
    )

    assert (
        formatted_code == "from module import AnotherLongGeneratedTypeName, ExtremelyLongGeneratedTypeName, "
        "GeneratedTypeNameThatFitsWithinConfiguredLineLength, Zed\n"
    )


def test_format_code_builtin_formatter_ignores_non_integer_line_lengths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test built-in formatter ignores non-integer line length configuration."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.datamodel-codegen]\n"
        'builtin-format-line-length = "140"\n'
        "[tool.ruff]\n"
        'line-length = "140"\n'
        "[tool.black]\n"
        'line-length = "140"\n'
        "[tool.isort]\n"
        'line_length = "140"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
    )

    formatted_code = formatter.format_code(
        "from module import Zed, ExtremelyLongGeneratedTypeName, AnotherLongGeneratedTypeName, "
        "GeneratedTypeNameThatPushesTheImportPastTheDefaultLineLength\n"
    )

    assert (
        formatted_code == "from module import (\n"
        "    AnotherLongGeneratedTypeName,\n"
        "    ExtremelyLongGeneratedTypeName,\n"
        "    GeneratedTypeNameThatPushesTheImportPastTheDefaultLineLength,\n"
        "    Zed,\n"
        ")\n"
    )


def test_format_code_builtin_formatter_wraps_long_imports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test built-in formatter wraps import lines that exceed the default line length."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
    )

    formatted_code = formatter.format_code(
        "from module import Zed, ExtremelyLongGeneratedTypeName, AnotherLongGeneratedTypeName, "
        "GeneratedTypeNameThatPushesTheImportPastTheDefaultLineLength\n"
    )

    assert (
        formatted_code == "from module import (\n"
        "    AnotherLongGeneratedTypeName,\n"
        "    ExtremelyLongGeneratedTypeName,\n"
        "    GeneratedTypeNameThatPushesTheImportPastTheDefaultLineLength,\n"
        "    Zed,\n"
        ")\n"
    )


def test_format_code_builtin_formatter_preserves_commented_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test built-in formatter keeps import comments attached to their import line."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
    )

    formatted_code = formatter.format_code(
        "from pydantic import Field, BaseModel  # noqa: F401\n"
        "import sys\n"
        "from __future__ import annotations\n"
        "\n"
        "class Model(BaseModel):\n"
        "    name: str\n"
    )

    assert (
        formatted_code == "from __future__ import annotations\n"
        "\n"
        "import sys\n"
        "\n"
        "from pydantic import Field, BaseModel  # noqa: F401\n"
        "\n"
        "\n"
        "class Model(BaseModel):\n"
        "    name: str\n"
    )


def test_format_code_builtin_formatter_sorts_type_checking_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test built-in formatter sorts imports inside a generated TYPE_CHECKING block."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
    )

    formatted_code = formatter.format_code(
        "from typing import TYPE_CHECKING\n"
        "from pydantic import BaseModel\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from .models import Zebra, Antelope\n"
        "    import os\n"
        "\n"
        "class Model(BaseModel):\n"
        "    pet: Antelope\n"
    )

    assert (
        formatted_code == "from typing import TYPE_CHECKING\n"
        "\n"
        "from pydantic import BaseModel\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    import os\n"
        "\n"
        "    from .models import Antelope, Zebra\n"
        "\n"
        "class Model(BaseModel):\n"
        "    pet: Antelope\n"
    )


def test_apply_builtin_formatter_sorts_aliased_imports_like_isort() -> None:
    """Test built-in formatter keeps isort-compatible groups for aliased imports."""
    code = (
        "from pydantic import Field\n"
        "from pydantic import BaseModel as Model\n"
        "from pydantic import ConfigDict\n"
        "\n"
        "class Pet(Model):\n"
        "    name: str = Field(...)\n"
    )

    assert apply_builtin_formatter(code) == (
        "from pydantic import BaseModel as Model\n"
        "from pydantic import ConfigDict\n"
        "from pydantic import Field\n"
        "\n"
        "\n"
        "class Pet(Model):\n"
        "    name: str = Field(...)\n"
    )


def test_format_import_node_formats_from_import_aliases() -> None:
    """Test direct import node formatting for aliased from-imports."""
    node = ast.parse("from pydantic import Field as PydanticField, BaseModel as Model\n").body[0]

    assert isinstance(node, ast.ImportFrom)
    assert _format_import_node(node, line_length=88) == (
        2,
        "from pydantic import BaseModel as Model\nfrom pydantic import Field as PydanticField",
    )


def test_apply_builtin_formatter_adds_blank_after_module_docstring() -> None:
    """Test built-in formatter keeps a blank line between module docstrings and imports."""
    code = '"""Generated models."""\nimport sys\n\nclass Pet:\n    pass\n'

    assert apply_builtin_formatter(code) == '"""Generated models."""\n\nimport sys\n\n\nclass Pet:\n    pass\n'


def test_apply_builtin_formatter_collapses_top_level_decorator_blank_lines() -> None:
    """Test built-in formatter keeps black-compatible spacing before top-level decorators."""
    code = (
        "from dataclasses import dataclass\n"
        "\n"
        "Alias = str\n"
        '"""Alias docs."""\n'
        "\n"
        "\n"
        "\n"
        "@dataclass\n"
        "class Pet:\n"
        "    name: str\n"
    )

    assert apply_builtin_formatter(code) == (
        "from dataclasses import dataclass\n"
        "\n"
        "Alias = str\n"
        '"""Alias docs."""\n'
        "\n"
        "\n"
        "@dataclass\n"
        "class Pet:\n"
        "    name: str\n"
    )


def test_apply_builtin_formatter_removes_blank_between_stacked_decorators() -> None:
    """Test built-in formatter keeps black-compatible stacked decorator spacing."""
    code = (
        "from dataclasses import dataclass\n"
        "from typing_extensions import deprecated\n"
        "\n"
        "\n"
        "@deprecated('LegacyUser is deprecated.')\n"
        "\n"
        "@dataclass\n"
        "class LegacyUser:\n"
        "    name: str\n"
    )

    assert apply_builtin_formatter(code) == (
        "from dataclasses import dataclass\n"
        "\n"
        "from typing_extensions import deprecated\n"
        "\n"
        "\n"
        "@deprecated('LegacyUser is deprecated.')\n"
        "@dataclass\n"
        "class LegacyUser:\n"
        "    name: str\n"
    )


def test_apply_builtin_formatter_removes_blank_between_decorator_and_class() -> None:
    """Test built-in formatter keeps decorators attached to decorated classes."""
    code = "from my_module import my_decorator\n\n\n@my_decorator\n\nclass User:\n    name: str\n"

    assert apply_builtin_formatter(code) == (
        "from my_module import my_decorator\n\n\n@my_decorator\nclass User:\n    name: str\n"
    )


def test_apply_builtin_formatter_adds_blank_between_assignment_and_class() -> None:
    """Test built-in formatter keeps black-compatible spacing before classes."""
    code = '__all__ = [\n    "Model",\n]\n\nclass Model:\n    id: str\n'

    assert apply_builtin_formatter(code) == '__all__ = [\n    "Model",\n]\n\n\nclass Model:\n    id: str\n'


def test_apply_builtin_formatter_normalizes_simple_string_quotes() -> None:
    """Test built-in formatter can match black string normalization for generated strings."""
    code = (
        "from typing import Literal\n"
        "from pydantic import BaseModel, Field\n"
        "\n"
        "\n"
        "class Model(BaseModel):\n"
        "    mode: Literal['MODE_2D'] = Field(..., alias='mapViewMode')\n"
    )

    assert apply_builtin_formatter(code, string_normalization=True) == (
        "from typing import Literal\n"
        "\n"
        "from pydantic import BaseModel, Field\n"
        "\n"
        "\n"
        "class Model(BaseModel):\n"
        '    mode: Literal["MODE_2D"] = Field(..., alias="mapViewMode")\n'
    )


def test_apply_builtin_formatter_normalizes_blank_after_class_docstring() -> None:
    """Test built-in formatter keeps black-compatible class docstring spacing."""
    code = (
        "from enum import Enum\n"
        "\n"
        "\n"
        "class Shift(Enum):\n"
        '    """\n'
        "    Employee shift status\n"
        '    """\n'
        "    ON_SHIFT = 'ON_SHIFT'\n"
    )

    assert apply_builtin_formatter(code) == (
        "from enum import Enum\n"
        "\n"
        "\n"
        "class Shift(Enum):\n"
        '    """\n'
        "    Employee shift status\n"
        '    """\n'
        "\n"
        "    ON_SHIFT = 'ON_SHIFT'\n"
    )


def test_apply_builtin_formatter_wraps_type_alias_type_union() -> None:
    """Test built-in formatter wraps generated TypeAliasType unions like black."""
    code = (
        "from typing import TypeAliasType, Union\n"
        "\n"
        "\n"
        'Resource = TypeAliasType("Resource", Union[\n'
        "    'Car',\n"
        "    'Employee',\n"
        "])\n"
    )

    assert apply_builtin_formatter(code) == (
        "from typing import TypeAliasType, Union\n"
        "\n"
        "Resource = TypeAliasType(\n"
        '    "Resource",\n'
        "    Union[\n"
        "        'Car',\n"
        "        'Employee',\n"
        "    ],\n"
        ")\n"
    )


def test_apply_builtin_formatter_wraps_inline_type_alias_type_union() -> None:
    """Test built-in formatter matches black for inline Union TypeAliasType calls."""
    code = (
        "from typing import TypeAliasType, Union\n"
        "\n"
        "\n"
        'JsonType = TypeAliasType("JsonType", Union[ElementaryType, list["JsonType"], dict[str, "JsonType"]])\n'
    )

    assert apply_builtin_formatter(code) == (
        "from typing import TypeAliasType, Union\n"
        "\n"
        "JsonType = TypeAliasType(\n"
        '    "JsonType", Union[ElementaryType, list["JsonType"], dict[str, "JsonType"]]\n'
        ")\n"
    )


def test_apply_builtin_formatter_normalizes_blank_lines_without_imports() -> None:
    """Test built-in formatter normalizes top-level blanks when no imports exist."""
    code = "Alias = str\n\n\n\nOtherAlias = Alias\n"

    assert apply_builtin_formatter(code) == "Alias = str\n\n\nOtherAlias = Alias\n"


@pytest.mark.skipif(sys.version_info < (3, 12), reason="type statements require Python 3.12")
def test_apply_builtin_formatter_normalizes_type_alias_blank_lines_without_imports() -> None:
    """Test built-in formatter normalizes top-level blanks between type statements."""
    code = "type Foo = str\n\n\n\ntype Bar = Foo\n"

    assert apply_builtin_formatter(code) == "type Foo = str\n\n\ntype Bar = Foo\n"


def test_apply_builtin_formatter_parenthesizes_short_annotated_default() -> None:
    """Test built-in formatter matches black for short overflowing Annotated defaults."""
    code = (
        "from typing import Annotated, Literal\n"
        "from pydantic import Field\n"
        "\n"
        "\n"
        "class Model:\n"
        "    typename__: Annotated[Literal['Notification'] | None, Field(alias='__typename')] = 'Notification'\n"
    )

    assert apply_builtin_formatter(code) == (
        "from typing import Annotated, Literal\n"
        "\n"
        "from pydantic import Field\n"
        "\n"
        "\n"
        "class Model:\n"
        "    typename__: Annotated[Literal['Notification'] | None, Field(alias='__typename')] = (\n"
        "        'Notification'\n"
        "    )\n"
    )


def test_apply_builtin_formatter_parenthesizes_long_union_annotation() -> None:
    """Test built-in formatter matches black for long generated union annotations."""
    code = (
        "class Model:\n"
        "    optional_oneof_with_null_and_constraint: OptionalOneofWithNullAndConstraint | None | UnsetType = UNSET\n"
        "    optional_nullable_with_constraint: Annotated[str, Meta(max_length=50)] | UnsetType = UNSET\n"
    )

    assert apply_builtin_formatter(code) == (
        "class Model:\n"
        "    optional_oneof_with_null_and_constraint: (\n"
        "        OptionalOneofWithNullAndConstraint | None | UnsetType\n"
        "    ) = UNSET\n"
        "    optional_nullable_with_constraint: (\n"
        "        Annotated[str, Meta(max_length=50)] | UnsetType\n"
        "    ) = UNSET\n"
    )


def test_apply_builtin_formatter_wraps_union_subscript_annotation() -> None:
    """Test built-in formatter matches black for generated Union annotations."""
    code = (
        "class Api(Struct):\n"
        "    apiKey: Union[Annotated[str, Meta(description='To be used as a dataset parameter value')], "
        "UnsetType] = UNSET\n"
        "    optional_nullable_with_constraint: Union[Annotated[str, Meta(max_length=50)], UnsetType] = UNSET\n"
    )

    assert apply_builtin_formatter(code) == (
        "class Api(Struct):\n"
        "    apiKey: Union[\n"
        "        Annotated[str, Meta(description='To be used as a dataset parameter value')],\n"
        "        UnsetType,\n"
        "    ] = UNSET\n"
        "    optional_nullable_with_constraint: Union[\n"
        "        Annotated[str, Meta(max_length=50)], UnsetType\n"
        "    ] = UNSET\n"
    )


def test_format_code_builtin_formatter_wraps_generated_model_statements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test built-in formatter wraps generated model statements that Black would split."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
    )

    formatted_code = formatter.format_code(
        "from typing import Annotated\n"
        "from pydantic import BaseModel, ConfigDict, Field\n"
        "\n"
        "class Model(BaseModel):\n"
        "    model_config = ConfigDict(extra='forbid', populate_by_name=True, json_schema_extra={'x-one': 'two'})\n"
        "    name: str = Field(None, examples=['dog', 'cat'], description='description', "
        "title='Long Title That makes it exceed line length maybe')\n"
        "    pet: Annotated[VeryLongGeneratedTypeNameThatExceedsTheDefaultLineLength, "
        "Field(description='x', title='y')]\n"
    )

    assert (
        formatted_code == "from typing import Annotated\n"
        "\n"
        "from pydantic import BaseModel, ConfigDict, Field\n"
        "\n"
        "\n"
        "class Model(BaseModel):\n"
        "    model_config = ConfigDict(\n"
        "        extra='forbid', populate_by_name=True, json_schema_extra={'x-one': 'two'}\n"
        "    )\n"
        "    name: str = Field(\n"
        "        None,\n"
        "        examples=['dog', 'cat'],\n"
        "        description='description',\n"
        "        title='Long Title That makes it exceed line length maybe',\n"
        "    )\n"
        "    pet: Annotated[\n"
        "        VeryLongGeneratedTypeNameThatExceedsTheDefaultLineLength,\n"
        "        Field(description='x', title='y'),\n"
        "    ]\n"
    )


def test_format_code_builtin_formatter_handles_additional_generated_model_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test less common generated model formatting branches."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BUILTIN],
        builtin_format_line_length=72,
    )
    long_pattern = "a" * 80

    formatted_code = formatter.format_code(
        "import sys  # noqa: F401\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    VALUE = 1\n"
        "\n"
        "class Model:\n"
        "    model_config_with_an_extremely_long_name_to_force_formatting = ConfigDict()\n"
        "    model_config = ConfigDict(**CONFIG_WITH_A_LONG_NAME_TO_FORCE_FORMATTING)\n"
        "    alias: str = pydantic.Field(None, description='uses attribute field call')\n"
        "    plain_value = 'this line is long enough to be inspected but is not a generated formatter target'\n"
        "    existing: str = Field(\n"
        "        None,\n"
        "        description='already wrapped',\n"
        "    )\n"
        "    metadata: Annotated[VeryLongGeneratedTypeNameThatExceedsTheConfiguredLineLength]\n"
        "    defaulted_metadata: Annotated[VeryLongGeneratedTypeNameThatExceedsTheConfiguredLineLength, "
        "Field(description='kept as-is because it already has a default')] = None\n"
        "    typename__: Annotated[Literal['Notification'] | None, Field(alias='__typename')] = 'Notification'\n"
        f"    hostName: constr(pattern=r'{long_pattern}', strict=True) | None = None\n"
        "    optional_nested_value: list[list[VeryLongGeneratedTypeNameThatExceedsTheConfiguredLineLength | None] "
        "| None] "
        "| None = None\n"
        "    nested: Annotated[VeryLongGeneratedTypeNameThatExceedsTheConfiguredLineLength, "
        "Field(description='This nested field is long enough to wrap inside Annotated')]\n"
    )

    assert (
        formatted_code == "import sys  # noqa: F401\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    VALUE = 1\n"
        "\n"
        "class Model:\n"
        "    model_config_with_an_extremely_long_name_to_force_formatting = ConfigDict()\n"
        "    model_config = ConfigDict(\n"
        "        **CONFIG_WITH_A_LONG_NAME_TO_FORCE_FORMATTING\n"
        "    )\n"
        "    alias: str = pydantic.Field(\n"
        "        None, description='uses attribute field call'\n"
        "    )\n"
        "    plain_value = 'this line is long enough to be inspected but is not a generated formatter target'\n"
        "    existing: str = Field(\n"
        "        None,\n"
        "        description='already wrapped',\n"
        "    )\n"
        "    metadata: Annotated[\n"
        "        VeryLongGeneratedTypeNameThatExceedsTheConfiguredLineLength\n"
        "    ]\n"
        "    defaulted_metadata: Annotated[\n"
        "        VeryLongGeneratedTypeNameThatExceedsTheConfiguredLineLength,\n"
        "        Field(\n"
        "            description='kept as-is because it already has a default'\n"
        "        ),\n"
        "    ] = None\n"
        "    typename__: Annotated[\n"
        "        Literal['Notification'] | None, Field(alias='__typename')\n"
        "    ] = 'Notification'\n"
        "    hostName: (\n"
        "        constr(\n"
        f"            pattern=r'{long_pattern}',\n"
        "            strict=True,\n"
        "        )\n"
        "        | None\n"
        "    ) = None\n"
        "    optional_nested_value: list[list[VeryLongGeneratedTypeNameThatExceedsTheConfiguredLineLength | None] "
        "| None] "
        "| None = (\n"
        "        None\n"
        "    )\n"
        "    nested: Annotated[\n"
        "        VeryLongGeneratedTypeNameThatExceedsTheConfiguredLineLength,\n"
        "        Field(\n"
        "            description='This nested field is long enough to wrap inside Annotated'\n"
        "        ),\n"
        "    ]\n"
    )


def test_apply_builtin_formatter_wraps_msgspec_field_default_factory() -> None:
    """Test built-in formatter matches black for generated msgspec field defaults."""
    code = (
        "class Bar(Struct):\n"
        "    original_foo: Foo_1 | UnsetType = field(default_factory=lambda: "
        "convert({'text': 'abc', 'number': 123}, type=Foo_1))\n"
        "    baz: list[Foo_1] | UnsetType = field(default_factory=lambda: "
        "convert([{'text': 'abc', 'number': 123}, {'text': 'efg', 'number': 456}], type=list[Foo_1]))\n"
    )

    assert apply_builtin_formatter(code) == (
        "class Bar(Struct):\n"
        "    original_foo: Foo_1 | UnsetType = field(\n"
        "        default_factory=lambda: convert({'text': 'abc', 'number': 123}, type=Foo_1)\n"
        "    )\n"
        "    baz: list[Foo_1] | UnsetType = field(\n"
        "        default_factory=lambda: convert(\n"
        "            [{'text': 'abc', 'number': 123}, {'text': 'efg', 'number': 456}],\n"
        "            type=list[Foo_1],\n"
        "        )\n"
        "    )\n"
    )


@pytest.mark.parametrize(
    ("code", "expected_code"),
    [
        ("", ""),
        ("class Model:\n    pass", "class Model:\n    pass\n"),
        ("if", "if\n"),
        ("import typing as t", "import typing as t\n"),
    ],
)
def test_apply_builtin_formatter_handles_simple_edge_cases(code: str, expected_code: str) -> None:
    """Test built-in formatter behavior when no import block can be rewritten."""
    assert apply_builtin_formatter(code) == expected_code


def test_apply_builtin_formatter_matches_black_isort_for_normalized_expected_files(tmp_path: Path) -> None:
    """Keep built-in formatting aligned with black + isort for generated model outputs."""
    expected_path = Path(__file__).parent / "data" / "expected"
    isort_config = isort.Config(settings_path=str(tmp_path))
    black_mode = black.FileMode(line_length=88, string_normalization=False)
    checked_files = 0
    mismatches: list[str] = []

    for path in sorted(expected_path.rglob("*.py")):
        relative_path = path.relative_to(expected_path).as_posix()
        if relative_path in BLACK_VERSION_DEPENDENT_NORMALIZED_EXPECTED_FILES:
            continue

        code = path.read_text(encoding="utf-8")
        try:
            black_isort_code = black.format_str(
                isort.code(code, config=isort_config),
                mode=black_mode,
            )
        except black.InvalidInput:
            continue

        if code != black_isort_code:
            continue

        checked_files += 1
        if apply_builtin_formatter(code) != black_isort_code:
            mismatches.append(relative_path)  # pragma: no cover

    assert checked_files > 1000
    assert not mismatches


def test_format_code_un_exist_custom_formatter() -> None:
    """Test error when custom formatter module doesn't exist."""
    with pytest.raises(ModuleNotFoundError):
        _ = CodeFormatter(
            PythonVersionMin,
            custom_formatters=[UN_EXIST_FORMATTER],
            formatters=[Formatter.BLACK, Formatter.ISORT],
        )


def test_format_code_invalid_formatter_name() -> None:
    """Test error when custom formatter has no CodeFormatter class."""
    with pytest.raises(NameError):
        _ = CodeFormatter(
            PythonVersionMin,
            custom_formatters=[WRONG_FORMATTER],
            formatters=[Formatter.BLACK, Formatter.ISORT],
        )


def test_format_code_is_not_subclass() -> None:
    """Test error when custom formatter doesn't inherit CustomCodeFormatter."""
    with pytest.raises(TypeError):
        _ = CodeFormatter(
            PythonVersionMin,
            custom_formatters=[NOT_SUBCLASS_FORMATTER],
            formatters=[Formatter.BLACK, Formatter.ISORT],
        )


def test_format_code_with_custom_formatter_without_kwargs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test custom formatter that doesn't require kwargs."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        custom_formatters=[ADD_COMMENT_FORMATTER],
        formatters=[Formatter.BLACK, Formatter.ISORT],
    )

    formatted_code = formatter.format_code("x = 1\ny = 2")

    assert formatted_code == "# a comment\nx = 1\ny = 2" + "\n"


def test_format_code_with_custom_formatter_with_kwargs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test custom formatter with kwargs."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        custom_formatters=[ADD_LICENSE_FORMATTER],
        custom_formatters_kwargs={"license_file": EXAMPLE_LICENSE_FILE},
        formatters=[Formatter.BLACK, Formatter.ISORT],
    )

    formatted_code = formatter.format_code("x = 1\ny = 2")

    assert (
        formatted_code
        == """# MIT License
#
# Copyright (c) 2023 Blah-blah
#
x = 1
y = 2
"""
    )


def test_format_code_with_two_custom_formatters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test chaining multiple custom formatters."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        custom_formatters=[
            ADD_COMMENT_FORMATTER,
            ADD_LICENSE_FORMATTER,
        ],
        custom_formatters_kwargs={"license_file": EXAMPLE_LICENSE_FILE},
        formatters=[Formatter.BLACK, Formatter.ISORT],
    )

    formatted_code = formatter.format_code("x = 1\ny = 2")

    assert (
        formatted_code
        == """# MIT License
#
# Copyright (c) 2023 Blah-blah
#
# a comment
x = 1
y = 2
"""
    )


def test_format_code_ruff_format_formatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ruff format formatter."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_FORMAT],
    )
    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.stdout = b"output"
        formatted_code = formatter.format_code("input")

    assert formatted_code == "output"
    mock_run.assert_called_once_with(
        (FAKE_RUFF_PATH, "format", "-"),
        input=b"input",
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_format_code_ruff_check_formatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test ruff check formatter with auto-fix."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK],
    )
    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.stdout = b"output"
        formatted_code = formatter.format_code("input")

    assert formatted_code == "output"
    mock_run.assert_called_once_with(
        (FAKE_RUFF_PATH, "check", "--fix", "--unsafe-fixes", "-"),
        input=b"input",
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_format_code_ruff_check_formatter_without_type_checking_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test ruff check formatter keeps runtime imports when requested."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK],
        use_type_checking_imports=False,
    )
    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value.stdout = b"output"
        formatted_code = formatter.format_code("input")

    assert formatted_code == "output"
    mock_run.assert_called_once_with(
        (FAKE_RUFF_PATH, "check", "--fix", "--unsafe-fixes", "--unfixable", "TC001,TC002,TC003", "-"),
        input=b"input",
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


@pytest.mark.parametrize("explicit_value", [True, False])
def test_resolve_use_type_checking_imports_respects_explicit_value(explicit_value: bool) -> None:
    """Test explicit TYPE_CHECKING import settings are preserved."""
    assert (
        resolve_use_type_checking_imports(
            explicit_value,
            is_multi_module_output=True,
            formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
            requires_runtime_imports_with_ruff_check=True,
        )
        is explicit_value
    )


def test_resolve_use_type_checking_imports_defaults_to_runtime_imports_for_deferred_pydantic_ruff() -> None:
    """Test deferred Ruff formatting keeps runtime imports for modular Pydantic output by default."""
    assert not resolve_use_type_checking_imports(
        None,
        is_multi_module_output=True,
        formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
        requires_runtime_imports_with_ruff_check=True,
    )


def test_resolve_use_type_checking_imports_keeps_existing_default_outside_deferred_pydantic_ruff() -> None:
    """Test non-modular or non-Pydantic output keeps TYPE_CHECKING imports enabled by default."""
    assert resolve_use_type_checking_imports(
        None,
        is_multi_module_output=False,
        formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
        requires_runtime_imports_with_ruff_check=True,
    )
    assert resolve_use_type_checking_imports(
        None,
        is_multi_module_output=True,
        formatters=[Formatter.RUFF_CHECK],
        requires_runtime_imports_with_ruff_check=False,
    )
    assert resolve_use_type_checking_imports(
        None,
        is_multi_module_output=True,
        formatters=[Formatter.RUFF_FORMAT],
        requires_runtime_imports_with_ruff_check=True,
    )


def test_format_code_ruff_check_and_format_uses_resolved_ruff_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test combined Ruff formatting reuses the resolved Ruff executable."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
    )
    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH) as mock_find_ruff_path,
        mock.patch("subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [
            mock.Mock(stdout=b"checked"),
            mock.Mock(stdout=b"formatted"),
        ]
        formatted_code = formatter.format_code("input")

    assert formatted_code == "formatted"
    mock_find_ruff_path.assert_called_once_with()
    assert mock_run.call_args_list == [
        mock.call(
            (FAKE_RUFF_PATH, "check", "--fix", "--unsafe-fixes", "-"),
            input=b"input",
            capture_output=True,
            check=False,
            cwd=str(tmp_path),
        ),
        mock.call(
            (FAKE_RUFF_PATH, "format", "-"),
            input=b"checked",
            capture_output=True,
            check=False,
            cwd=str(tmp_path),
        ),
    ]


def test_settings_path_with_existing_file(tmp_path: Path) -> None:
    """Test settings_path with existing file uses parent directory."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")
    existing_file = tmp_path / "existing.py"
    existing_file.write_text("", encoding="utf-8")

    formatter = CodeFormatter(
        PythonVersionMin, settings_path=existing_file, formatters=[Formatter.BLACK, Formatter.ISORT]
    )

    assert formatter.settings_path == str(tmp_path)


def test_settings_path_with_nonexistent_file(tmp_path: Path) -> None:
    """Test settings_path with nonexistent file uses existing parent."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")
    nonexistent_file = tmp_path / "nonexistent.py"

    formatter = CodeFormatter(
        PythonVersionMin, settings_path=nonexistent_file, formatters=[Formatter.BLACK, Formatter.ISORT]
    )

    assert formatter.settings_path == str(tmp_path)


def test_settings_path_with_deeply_nested_nonexistent_path(tmp_path: Path) -> None:
    """Test settings_path with deeply nested nonexistent path finds existing ancestor."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")
    nested_path = tmp_path / "a" / "b" / "c" / "nonexistent.py"

    formatter = CodeFormatter(
        PythonVersionMin, settings_path=nested_path, formatters=[Formatter.BLACK, Formatter.ISORT]
    )

    assert formatter.settings_path == str(tmp_path)


def test_format_directory_ruff_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test format_directory with ruff check."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK],
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("subprocess.run") as mock_run,
    ):
        formatter.format_directory(output_dir)

    mock_run.assert_called_once_with(
        (FAKE_RUFF_PATH, "check", "--fix", "--unsafe-fixes", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_format_directory_ruff_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test format_directory with ruff format."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_FORMAT],
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("subprocess.run") as mock_run,
    ):
        formatter.format_directory(output_dir)

    mock_run.assert_called_once_with(
        (FAKE_RUFF_PATH, "format", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_format_directory_both_ruff_formatters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test format_directory with both ruff check and format."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("subprocess.run") as mock_run,
    ):
        formatter.format_directory(output_dir)

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        (FAKE_RUFF_PATH, "check", "--fix", "--unsafe-fixes", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )
    mock_run.assert_any_call(
        (FAKE_RUFF_PATH, "format", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_format_directory_ruff_check_without_type_checking_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test format_directory keeps runtime imports when requested."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK],
        use_type_checking_imports=False,
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("subprocess.run") as mock_run,
    ):
        formatter.format_directory(output_dir)

    mock_run.assert_called_once_with(
        (FAKE_RUFF_PATH, "check", "--fix", "--unsafe-fixes", "--unfixable", "TC001,TC002,TC003", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_format_directory_both_ruff_formatters_without_type_checking_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test format_directory keeps runtime imports with both Ruff formatters."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
        use_type_checking_imports=False,
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with (
        mock.patch.object(formatter, "_find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("subprocess.run") as mock_run,
    ):
        formatter.format_directory(output_dir)

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        (FAKE_RUFF_PATH, "check", "--fix", "--unsafe-fixes", "--unfixable", "TC001,TC002,TC003", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )
    mock_run.assert_any_call(
        (FAKE_RUFF_PATH, "format", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=str(tmp_path),
    )


def test_defer_formatting_skips_ruff_in_format_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that defer_formatting=True skips ruff in format_code."""
    monkeypatch.chdir(tmp_path)
    formatter = CodeFormatter(
        PythonVersionMin,
        formatters=[Formatter.BLACK, Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
        defer_formatting=True,
    )

    with mock.patch("subprocess.run") as mock_run:
        formatted_code = formatter.format_code("x = 1")

    mock_run.assert_not_called()
    assert "x = 1" in formatted_code


def test_generate_with_ruff_batch_formatting(tmp_path: Path) -> None:
    """Test that generate uses batch ruff formatting for directory output."""
    from datamodel_code_generator import ModuleSplitMode, generate

    schema = """
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        }
    }
    """
    output_dir = tmp_path / "output"

    with (
        mock.patch("datamodel_code_generator.format.CodeFormatter._find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("datamodel_code_generator.format.subprocess.run") as mock_run,
    ):
        generate(
            input_=schema,
            output=output_dir,
            formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
            module_split_mode=ModuleSplitMode.Single,
        )

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        (
            FAKE_RUFF_PATH,
            "check",
            "--fix",
            "--unsafe-fixes",
            "--unfixable",
            "TC001,TC002,TC003",
            str(output_dir),
        ),
        capture_output=True,
        check=False,
        cwd=mock.ANY,
    )
    mock_run.assert_any_call(
        (FAKE_RUFF_PATH, "format", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=mock.ANY,
    )


def test_generate_with_ruff_batch_formatting_and_explicit_type_checking_imports(tmp_path: Path) -> None:
    """Test explicit TYPE_CHECKING imports override the modular Pydantic Ruff default."""
    from datamodel_code_generator import ModuleSplitMode, generate

    schema = """
    {
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        }
    }
    """
    output_dir = tmp_path / "output"

    with (
        mock.patch("datamodel_code_generator.format.CodeFormatter._find_ruff_path", return_value=FAKE_RUFF_PATH),
        mock.patch("datamodel_code_generator.format.subprocess.run") as mock_run,
    ):
        generate(
            input_=schema,
            output=output_dir,
            formatters=[Formatter.RUFF_CHECK, Formatter.RUFF_FORMAT],
            module_split_mode=ModuleSplitMode.Single,
            use_type_checking_imports=True,
        )

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        (FAKE_RUFF_PATH, "check", "--fix", "--unsafe-fixes", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=mock.ANY,
    )
    mock_run.assert_any_call(
        (FAKE_RUFF_PATH, "format", str(output_dir)),
        capture_output=True,
        check=False,
        cwd=mock.ANY,
    )


def test_code_formatter_warns_when_formatters_is_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that FutureWarning is emitted when formatters is None (default)."""
    monkeypatch.chdir(tmp_path)
    _warn_default_formatters_deprecation.cache_clear()
    with pytest.warns(FutureWarning, match="external formatters"):
        CodeFormatter(PythonVersionMin)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        CodeFormatter(PythonVersionMin)


def test_code_formatter_no_warning_when_formatters_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that no warning is emitted when formatters is explicitly specified."""
    monkeypatch.chdir(tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        CodeFormatter(PythonVersionMin, formatters=[Formatter.BLACK, Formatter.ISORT])


def test_code_formatter_no_warning_when_formatters_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that no warning is emitted when formatters is empty list."""
    monkeypatch.chdir(tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        CodeFormatter(PythonVersionMin, formatters=[])
