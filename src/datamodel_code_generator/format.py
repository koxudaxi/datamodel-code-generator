"""Code formatting utilities and Python version handling.

Provides CodeFormatter for applying black, isort, and ruff formatting,
along with PythonVersion enum and DatetimeClassType for output configuration.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess  # noqa: S404
import sys
import tokenize
from collections import defaultdict
from enum import Enum, IntEnum
from functools import cached_property, lru_cache
from importlib import import_module
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeGuard
from warnings import warn

from datamodel_code_generator.deprecations import warn_deprecated
from datamodel_code_generator.util import load_toml

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


@lru_cache(maxsize=1)
def _get_black() -> Any:
    import black as _black  # noqa: PLC0415

    return _black


@lru_cache(maxsize=1)
def _get_black_mode() -> Any:  # pragma: no cover
    black = _get_black()
    try:
        import black.mode  # noqa: PLC0415
    except ImportError:
        return None
    else:
        return black.mode


@lru_cache(maxsize=1)
def _get_isort() -> Any:
    import isort as _isort  # noqa: PLC0415

    return _isort


class DatetimeClassType(Enum):
    """Output datetime class type options."""

    Datetime = "datetime"
    Awaredatetime = "AwareDatetime"
    Naivedatetime = "NaiveDatetime"
    Pastdatetime = "PastDatetime"
    Futuredatetime = "FutureDatetime"


class DateClassType(Enum):
    """Output date class type options."""

    Date = "date"
    Pastdate = "PastDate"
    Futuredate = "FutureDate"


class _AliasSortCategory(IntEnum):
    CONSTANT = 0
    CLASS = 1
    OTHER = 2


class _ImportCategory(IntEnum):
    FUTURE = 0
    STANDARD_LIBRARY = 1
    THIRD_PARTY = 2
    FIRST_PARTY = 3
    LOCAL = 4


class PythonVersion(Enum):
    """Supported Python version targets for code generation."""

    PY_310 = "3.10"
    PY_311 = "3.11"
    PY_312 = "3.12"
    PY_313 = "3.13"
    PY_314 = "3.14"

    @cached_property
    def version_key(self) -> tuple[int, int]:
        """Return (major, minor) tuple for version comparison."""
        major, minor = self.value.split(".")
        return int(major), int(minor)

    @cached_property
    def _is_py_310_or_later(self) -> bool:  # pragma: no cover
        return True  # 3.10+ always true since minimum is PY_310

    @cached_property
    def _is_py_311_or_later(self) -> bool:  # pragma: no cover
        return self.value != self.PY_310.value  # ty: ignore

    @cached_property
    def _is_py_312_or_later(self) -> bool:  # pragma: no cover
        return self.value not in {self.PY_310.value, self.PY_311.value}  # ty: ignore

    @cached_property
    def _is_py_313_or_later(self) -> bool:
        return self.value not in {self.PY_310.value, self.PY_311.value, self.PY_312.value}  # ty: ignore

    @cached_property
    def _is_py_314_or_later(self) -> bool:
        return self.value not in {  # ty: ignore
            self.PY_310.value,  # ty: ignore
            self.PY_311.value,  # ty: ignore
            self.PY_312.value,  # ty: ignore
            self.PY_313.value,  # ty: ignore
        }

    @property
    def has_union_operator(self) -> bool:  # pragma: no cover
        """Check if Python version supports the union operator (|)."""
        return self._is_py_310_or_later

    @property
    def has_type_alias(self) -> bool:  # pragma: no cover
        """Check if Python version supports TypeAlias.

        .. deprecated::
            This property is unused and will be removed in a future version.
        """
        warn_deprecated("python-api.python-version-has-type-alias", stacklevel=2)
        return self._is_py_310_or_later

    @property
    def has_typed_dict_non_required(self) -> bool:
        """Check if Python version supports TypedDict NotRequired."""
        return self._is_py_311_or_later

    @property
    def has_typed_dict_read_only(self) -> bool:
        """Check if Python version supports TypedDict ReadOnly (PEP 705)."""
        return self._is_py_313_or_later

    @property
    def has_typed_dict_closed(self) -> bool:
        """Check if Python version supports TypedDict closed/extra_items (PEP 728).

        PEP 728 is targeted for Python 3.15. Until then, typing_extensions is required.
        """
        return self.version_key >= (3, 15)

    @property
    def has_kw_only_dataclass(self) -> bool:
        """Check if Python version supports kw_only in dataclasses."""
        return self._is_py_310_or_later

    @property
    def has_type_statement(self) -> bool:
        """Check if Python version supports type statements."""
        return self._is_py_312_or_later

    @property
    def has_native_deferred_annotations(self) -> bool:
        """Check if Python version has native deferred annotations (Python 3.14+)."""
        return self._is_py_314_or_later

    @property
    def has_strenum(self) -> bool:
        """Check if Python version supports StrEnum."""
        return self._is_py_311_or_later


PythonVersionMin = PythonVersion.PY_310


@lru_cache(maxsize=1)
def _get_black_python_version_map() -> dict[PythonVersion, Any]:
    black = _get_black()
    return {
        v: getattr(black.TargetVersion, f"PY{v.name.split('_')[-1]}")
        for v in PythonVersion
        if hasattr(black.TargetVersion, f"PY{v.name.split('_')[-1]}")
    }


def is_supported_in_black(python_version: PythonVersion) -> bool:  # pragma: no cover
    """Check if a Python version is supported by the installed black version."""
    return python_version in _get_black_python_version_map()


def black_find_project_root(sources: Sequence[Path]) -> Path:
    """Find the project root directory for black configuration."""
    from black import find_project_root as _find_project_root  # noqa: PLC0415

    project_root = _find_project_root(tuple(str(s) for s in sources))
    if isinstance(project_root, tuple):
        return project_root[0]
    return project_root  # pragma: no cover


class Formatter(Enum):
    """Available code formatters for generated output."""

    BUILTIN = "builtin"
    BLACK = "black"
    ISORT = "isort"
    RUFF_CHECK = "ruff-check"
    RUFF_FORMAT = "ruff-format"


DEFAULT_FORMATTERS = [Formatter.BLACK, Formatter.ISORT]
EXTERNAL_FORMATTERS = frozenset({
    Formatter.BLACK,
    Formatter.ISORT,
    Formatter.RUFF_CHECK,
    Formatter.RUFF_FORMAT,
})
DEFAULT_LINE_LENGTH = 88
DEFAULT_KNOWN_FIRST_PARTY = frozenset({"datamodel_code_generator", "tests"})
MAX_TOP_LEVEL_BLANK_LINES = 2
MAX_SHORT_DEFAULT_OVERFLOW = 13
LONG_TARGET_PREFIX_LENGTH = 30
TYPE_ALIAS_INLINE_ARGUMENT_COUNT = 2
STRING_PREFIX_PATTERN = re.compile(r"(?i)^([rubf]*)(\"\"\"|'''|\"|')")


def _is_valid_builtin_line_length(line_length: Any) -> TypeGuard[int]:
    return isinstance(line_length, int) and not isinstance(line_length, bool) and line_length > 0


def _find_pyproject_toml(settings_path: Path) -> Path | None:
    for path in (settings_path, *settings_path.parents):
        pyproject_toml = path / "pyproject.toml"
        if pyproject_toml.is_file():
            return pyproject_toml
    return None


def _get_builtin_line_length(settings_path: Path, explicit_line_length: int | None = None) -> int:
    if explicit_line_length is not None:
        return explicit_line_length if _is_valid_builtin_line_length(explicit_line_length) else DEFAULT_LINE_LENGTH

    pyproject_toml_path = _find_pyproject_toml(settings_path)
    if pyproject_toml_path is None:
        return DEFAULT_LINE_LENGTH

    tool_config = load_toml(pyproject_toml_path).get("tool", {})
    datamodel_codegen_config = tool_config.get("datamodel-codegen", {})
    ruff_config = tool_config.get("ruff", {})
    black_config = tool_config.get("black", {})
    isort_config = tool_config.get("isort", {})
    for line_length in (
        datamodel_codegen_config.get("builtin-format-line-length"),
        datamodel_codegen_config.get("builtin_format_line_length"),
        ruff_config.get("line-length"),
        black_config.get("line-length"),
        isort_config.get("line_length"),
    ):
        if _is_valid_builtin_line_length(line_length):
            return line_length
    return DEFAULT_LINE_LENGTH


def _get_builtin_known_first_party(settings_path: Path) -> frozenset[str]:
    pyproject_toml_path = _find_pyproject_toml(settings_path)
    if pyproject_toml_path is None:
        return DEFAULT_KNOWN_FIRST_PARTY

    isort_config = load_toml(pyproject_toml_path).get("tool", {}).get("isort", {})
    known_first_party = isort_config.get("known_first_party", [])
    if not isinstance(known_first_party, list):
        return DEFAULT_KNOWN_FIRST_PARTY
    return DEFAULT_KNOWN_FIRST_PARTY | frozenset(item for item in known_first_party if isinstance(item, str))


def _get_builtin_string_normalization(settings_path: Path, *, skip_string_normalization: bool) -> bool:
    if not skip_string_normalization:
        return True

    pyproject_toml_path = _find_pyproject_toml(settings_path)
    if pyproject_toml_path is None:
        return False

    black_config = load_toml(pyproject_toml_path).get("tool", {}).get("black", {})
    skip_black_string_normalization = black_config.get("skip-string-normalization")
    if isinstance(skip_black_string_normalization, bool):
        return not skip_black_string_normalization
    return False


def _format_alias(alias: ast.alias) -> str:
    if alias.asname:
        return f"{alias.name} as {alias.asname}"
    return alias.name


def _alias_imported_name(alias: str) -> str:
    if " as " in alias:
        return alias.split(" as ", 1)[0]
    return alias


def _alias_sort_key(alias: str) -> tuple[_AliasSortCategory, str]:
    name = _alias_imported_name(alias)
    if name.isupper():
        category = _AliasSortCategory.CONSTANT
    elif name[:1].isupper():
        category = _AliasSortCategory.CLASS
    else:
        category = _AliasSortCategory.OTHER
    return category, name.lower()


def _format_from_import(module: str, aliases: list[str], line_length: int) -> str:
    line = f"from {module} import {', '.join(aliases)}"
    if len(line) <= line_length and "*" not in aliases:
        return line
    imports = "\n".join(f"    {alias}," for alias in aliases)
    return f"from {module} import (\n{imports}\n)"


def _import_category(module: str, level: int, known_first_party: frozenset[str]) -> _ImportCategory:
    if module == "__future__":
        return _ImportCategory.FUTURE
    if level:
        return _ImportCategory.LOCAL
    top_level_module = module.split(".", 1)[0]
    if top_level_module in sys.stdlib_module_names:
        return _ImportCategory.STANDARD_LIBRARY
    if top_level_module in known_first_party:
        return _ImportCategory.FIRST_PARTY
    return _ImportCategory.THIRD_PARTY


def _has_inline_comment(lines: list[str], node: ast.AST) -> bool:
    lineno = getattr(node, "lineno", 1)
    end_lineno = getattr(node, "end_lineno", None) or lineno
    return any("#" in line for line in lines[lineno - 1 : end_lineno])


def _format_import_node_without_reordering(
    node: ast.Import | ast.ImportFrom,
    lines: list[str],
    known_first_party: frozenset[str] = DEFAULT_KNOWN_FIRST_PARTY,
) -> tuple[int, str]:
    end_lineno = node.end_lineno or node.lineno
    raw_import = "\n".join(lines[node.lineno - 1 : end_lineno])
    if isinstance(node, ast.Import):
        category = min(_import_category(alias.name, 0, known_first_party) for alias in node.names)
    else:
        category = _import_category(node.module or "", node.level, known_first_party)
    return category, raw_import


def _format_import_node(
    node: ast.Import | ast.ImportFrom,
    line_length: int,
    known_first_party: frozenset[str] = DEFAULT_KNOWN_FIRST_PARTY,
) -> tuple[int, str]:
    if isinstance(node, ast.Import):
        lines = [f"import {_format_alias(alias)}" for alias in sorted(node.names, key=lambda alias: alias.name)]
        category = min(_import_category(alias.name, 0, known_first_party) for alias in node.names)
        return category, "\n".join(lines)

    module = "." * node.level + (node.module or "")
    category = _import_category(node.module or "", node.level, known_first_party)
    if any(alias.asname is not None for alias in node.names):
        lines = [
            _format_from_import(module, [_format_alias(alias)], line_length)
            for alias in sorted(node.names, key=lambda alias: _alias_sort_key(_format_alias(alias)))
        ]
        return category, "\n".join(lines)

    aliases = sorted((_format_alias(alias) for alias in node.names), key=_alias_sort_key)
    return category, _format_from_import(module, aliases, line_length)


def _from_import_key(node: ast.ImportFrom) -> tuple[int, str]:
    return node.level, node.module or ""


def _modules_with_aliased_imports(import_nodes: list[ast.Import | ast.ImportFrom]) -> set[tuple[int, str]]:
    return {
        _from_import_key(node)
        for node in import_nodes
        if isinstance(node, ast.ImportFrom) and any(alias.asname is not None for alias in node.names)
    }


def _can_merge_from_imports(node: ast.ImportFrom, aliased_modules: set[tuple[int, str]]) -> bool:
    return node.level == 0 and _from_import_key(node) not in aliased_modules


def _iter_aliased_from_import_lines(
    module: str,
    aliases: list[tuple[int, str, bool]],
    line_length: int,
) -> Iterator[str]:
    sorted_aliases = sorted(aliases, key=lambda item: _alias_sort_key(item[1]))
    chunk: list[str] = []
    chunk_group: int | None = None
    for group_index, alias, is_aliased in sorted_aliases:
        if is_aliased:
            if chunk:
                yield _format_from_import(module, chunk, line_length)
                chunk = []
                chunk_group = None
            yield _format_from_import(module, [alias], line_length)
            continue

        if chunk and chunk_group != group_index:
            yield _format_from_import(module, chunk, line_length)
            chunk = []
        chunk.append(alias)
        chunk_group = group_index

    if chunk:
        yield _format_from_import(module, chunk, line_length)


def _import_line_sort_key(line: str) -> tuple[int, int, str, int, str, str]:
    if not line.startswith("from "):
        return 0, 0, line.lower(), 0, "", line

    module, _, imported = line.removeprefix("from ").partition(" import ")
    relative_level = len(module) - len(module.lstrip("."))
    alias_category, alias_name = _alias_sort_key(imported.split(",", 1)[0].strip())
    if relative_level:
        return 1, -relative_level, module[relative_level:].lower(), int(alias_category), alias_name, line.lower()
    return 1, 0, module.lower(), int(alias_category), alias_name, line.lower()


def _build_builtin_import_block(
    import_nodes: list[ast.Import | ast.ImportFrom],
    line_length: int,
    lines: list[str],
    known_first_party: frozenset[str],
) -> str:
    categorized_lines: defaultdict[_ImportCategory, set[str]] = defaultdict(set)
    grouped_from_imports: defaultdict[tuple[_ImportCategory, int, str], set[str]] = defaultdict(set)
    aliased_from_imports: defaultdict[tuple[_ImportCategory, int, str], list[tuple[int, str, bool]]] = defaultdict(list)
    aliased_modules = _modules_with_aliased_imports(import_nodes)

    for node_index, node in enumerate(import_nodes):
        if _has_inline_comment(lines, node):
            category, raw_import = _format_import_node_without_reordering(node, lines, known_first_party)
            categorized_lines[category].add(raw_import)
            continue

        if isinstance(node, ast.ImportFrom) and _from_import_key(node) in aliased_modules:
            module = "." * node.level + (node.module or "")
            category = _import_category(node.module or "", node.level, known_first_party)
            for alias in node.names:
                aliased_from_imports[category, node.level, module].append((
                    node_index,
                    _format_alias(alias),
                    alias.asname is not None,
                ))
            continue

        if isinstance(node, ast.ImportFrom) and _can_merge_from_imports(node, aliased_modules):
            module = node.module or ""
            category = _import_category(module, node.level, known_first_party)
            for alias in node.names:
                grouped_from_imports[category, node.level, module].add(_format_alias(alias))
            continue

        category, import_line = _format_import_node(node, line_length, known_first_party)
        categorized_lines[category].add(import_line)

    for (category, _level, module), aliases in grouped_from_imports.items():
        categorized_lines[category].add(_format_from_import(module, sorted(aliases, key=_alias_sort_key), line_length))
    for (category, _level, module), aliases in aliased_from_imports.items():
        for import_line in _iter_aliased_from_import_lines(module, aliases, line_length):
            categorized_lines[category].add(import_line)

    groups = [
        "\n".join(sorted(categorized_lines[category], key=_import_line_sort_key))
        for category in sorted(categorized_lines)
    ]
    return "\n\n".join(group for group in groups if group)


def _is_name_or_attr(node: ast.AST, name: str) -> bool:
    if isinstance(node, ast.Name):
        return node.id == name
    return isinstance(node, ast.Attribute) and node.attr == name


def _is_type_checking_if(node: ast.AST) -> TypeGuard[ast.If]:
    return isinstance(node, ast.If) and _is_name_or_attr(node.test, "TYPE_CHECKING")


def _source_segment(source: str, node: ast.AST) -> str:
    return ast.get_source_segment(source, node) or ast.unparse(node)


def _inline_source_segment(source: str, node: ast.AST) -> str:
    if isinstance(node, ast.Lambda):
        return re.sub(r"^lambda\s+:", "lambda:", ast.unparse(node))
    return _source_segment(source, node)


def _format_call_argument(keyword: ast.keyword, source: str) -> str:
    if keyword.arg is None:
        return f"**{_source_segment(source, keyword.value)}"
    return f"{keyword.arg}={_inline_source_segment(source, keyword.value)}"


def _format_dict_literal(
    dict_node: ast.Dict,
    indent: str,
    source: str,
    line_length: int = DEFAULT_LINE_LENGTH,
) -> str:
    entries: list[str] = []
    entry_indent = f"{indent}    "
    has_trailing_comma = len(dict_node.keys) > 1
    for key, value in zip(dict_node.keys, dict_node.values, strict=True):
        trailing_comma = "," if has_trailing_comma else ""
        if key is None:
            entries.append(f"{entry_indent}**{_source_segment(source, value)}{trailing_comma}")
        elif (
            isinstance(value, ast.Dict)
            and len(f"{entry_indent}{_source_segment(source, key)}: {_source_segment(source, value)}{trailing_comma}")
            > line_length
        ):
            nested_lines = _format_dict_literal(value, entry_indent, source, line_length).splitlines()
            entries.append(f"{entry_indent}{_source_segment(source, key)}: {nested_lines[0]}")
            entries.extend(nested_lines[1:-1])
            entries.append(f"{nested_lines[-1]}{trailing_comma}")
        else:
            entries.append(
                f"{entry_indent}{_source_segment(source, key)}: {_source_segment(source, value)}{trailing_comma}"
            )
    return "{\n" + "\n".join(entries) + f"\n{indent}}}"


def _format_list_literal(list_node: ast.List, indent: str, source: str) -> str:
    element_indent = f"{indent}    "
    has_trailing_comma = len(list_node.elts) > 1
    elements = "\n".join(
        f"{element_indent}{_source_segment(source, element)}{',' if has_trailing_comma else ''}"
        for element in list_node.elts
    )
    return f"[\n{elements}\n{indent}]"


def _split_escaped_string_literal(content: str, max_length: int) -> list[str]:
    chunks: list[str] = []
    remaining = content
    while len(remaining) > max_length:
        split_index = remaining.rfind(" ", 0, max_length + 1)
        if split_index <= 0:
            split_index = max_length
            if remaining[split_index - 1] == "\\":
                split_index -= 1
        chunks.append(remaining[:split_index])
        remaining = remaining[split_index:]
    chunks.append(remaining)
    return chunks


def _format_wrapped_string_literal(value: str, indent: str, line_length: int) -> str:
    escaped = repr(value).removeprefix("'").removesuffix("'")
    literal_indent = f"{indent}    "
    max_content_length = line_length - len(literal_indent) - 2
    literal_lines = "\n".join(
        f"{literal_indent}'{chunk}'" for chunk in _split_escaped_string_literal(escaped, max_content_length)
    )
    return f"(\n{literal_lines}\n{indent})"


def _format_call_argument_for_block(
    keyword: ast.keyword,
    indent: str,
    line_length: int,
    source: str,
    *,
    wrap_string_literal: bool,
) -> str:
    if keyword.arg is None:
        return f"**{_source_segment(source, keyword.value)}"
    argument = f"{keyword.arg}={_inline_source_segment(source, keyword.value)}"
    if (
        wrap_string_literal
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
        and len(f"{indent}{argument}") > line_length
    ):
        return f"{keyword.arg}={_format_wrapped_string_literal(keyword.value.value, indent, line_length)}"
    if isinstance(keyword.value, ast.Dict) and len(f"{indent}{argument}") > line_length:
        return f"{keyword.arg}={_format_dict_literal(keyword.value, indent, source, line_length)}"
    if (
        isinstance(keyword.value, ast.Lambda)
        and isinstance(keyword.value.body, ast.Call)
        and len(f"{indent}{argument}") > line_length
    ):
        formatted_value = _format_call(
            keyword.value.body,
            indent,
            line_length,
            source,
            wrap_string_literal=wrap_string_literal,
        )
        return f"{keyword.arg}=lambda: {formatted_value}"
    if isinstance(keyword.value, ast.Call) and len(f"{indent}{argument}") > line_length:
        formatted_value = _format_call(
            keyword.value,
            indent,
            line_length,
            source,
            wrap_string_literal=wrap_string_literal,
        )
        return f"{keyword.arg}={formatted_value}"
    return argument


def _format_call(  # noqa: PLR0913
    call: ast.Call,
    indent: str,
    line_length: int,
    source: str,
    *,
    force_trailing_comma: bool = False,
    wrap_string_literal: bool = False,
) -> str:
    call_name = _source_segment(source, call.func)
    arguments = [_source_segment(source, argument) for argument in call.args]
    continuation_indent = f"{indent}    "
    arguments.extend(
        _format_call_argument_for_block(
            keyword,
            continuation_indent,
            line_length,
            source,
            wrap_string_literal=wrap_string_literal,
        )
        for keyword in call.keywords
    )
    if not arguments:
        return f"{call_name}()"

    joined_arguments = ", ".join(arguments)
    if "\n" not in joined_arguments and len(f"{continuation_indent}{joined_arguments}") <= line_length:
        return f"{call_name}(\n{continuation_indent}{joined_arguments}\n{indent})"

    has_trailing_comma = force_trailing_comma or len(arguments) > 1
    argument_lines = "\n".join(
        f"{continuation_indent}{argument}{',' if has_trailing_comma else ''}" for argument in arguments
    )
    return f"{call_name}(\n{argument_lines}\n{indent})"


def _format_constrained_call(call: ast.Call, indent: str, line_length: int, source: str) -> str:
    call_name = _source_segment(source, call.func)
    arguments = [_source_segment(source, argument) for argument in call.args]
    arguments.extend(_format_call_argument(keyword, source) for keyword in call.keywords)
    if not arguments:
        return f"{call_name}()"

    inline_call = f"{call_name}({', '.join(arguments)})"
    if len(f"{indent}{inline_call}") <= line_length:
        return inline_call

    continuation_indent = f"{indent}    "
    has_trailing_comma = len(arguments) > 1
    argument_lines = "\n".join(
        f"{continuation_indent}{argument}{',' if has_trailing_comma else ''}" for argument in arguments
    )
    return f"{call_name}(\n{argument_lines}\n{indent})"


def _is_call(node: ast.AST | None, name: str) -> TypeGuard[ast.Call]:
    return isinstance(node, ast.Call) and _is_name_or_attr(node.func, name)


def _is_annotated(node: ast.AST) -> TypeGuard[ast.Subscript]:
    return isinstance(node, ast.Subscript) and _is_name_or_attr(node.value, "Annotated")


def _is_list_of_annotated(node: ast.AST) -> TypeGuard[ast.Subscript]:
    return isinstance(node, ast.Subscript) and _is_name_or_attr(node.value, "list") and _is_annotated(node.slice)


def _is_union(node: ast.AST) -> TypeGuard[ast.Subscript]:
    return isinstance(node, ast.Subscript) and _is_name_or_attr(node.value, "Union")


def _is_constrained_string_call(node: ast.AST | None) -> TypeGuard[ast.Call]:
    return _is_call(node, "constr")


def _contains_constrained_string_call(node: ast.AST) -> bool:
    return any(_is_constrained_string_call(child) for child in ast.walk(node))


def _contains_annotated(node: ast.AST) -> bool:
    return any(_is_annotated(child) for child in ast.walk(node))


def _contains_list_of_annotated(node: ast.AST) -> bool:
    return any(_is_list_of_annotated(child) for child in ast.walk(node))


def _is_simple_union_annotation(node: ast.AST) -> bool:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _is_simple_union_annotation(node.left) and _is_simple_union_annotation(node.right)
    return isinstance(node, ast.Name | ast.Attribute) or (isinstance(node, ast.Constant) and node.value is None)


def _should_format_constrained_string_union(
    annotation: ast.AST,
    value: ast.AST | None,
    annotation_prefix: str,
    line_length: int,
    source: str,
) -> TypeGuard[ast.BinOp]:
    if not isinstance(annotation, ast.BinOp) or not isinstance(annotation.op, ast.BitOr) or value is None:
        return False
    if not (_is_constrained_string_call(annotation.left) or _is_constrained_string_call(annotation.right)):
        return False
    constrained_call = annotation.left if _is_constrained_string_call(annotation.left) else annotation.right
    return (
        not _is_call(value, "Field")
        or len(annotation_prefix) > line_length
        or len(_source_segment(source, constrained_call)) > line_length - 24
    )


def _can_parenthesize_field_value(annotation: ast.AST, target: str) -> bool:
    if isinstance(annotation, ast.BinOp):
        return True
    if _is_constrained_string_call(annotation):
        return target != "root"
    return not _contains_constrained_string_call(annotation)


def _should_format_union_annotation(
    annotation: ast.AST,
    value: ast.AST | None,
    target_prefix: str,
    annotation_prefix: str,
    line_length: int,
) -> TypeGuard[ast.BinOp]:
    return (
        isinstance(annotation, ast.BinOp)
        and isinstance(annotation.op, ast.BitOr)
        and value is not None
        and not (isinstance(value, ast.Constant) and isinstance(value.value, str))
        and (
            (
                len(annotation_prefix) > line_length
                and (_contains_annotated(annotation) or _is_simple_union_annotation(annotation))
            )
            or _contains_list_of_annotated(annotation)
            or (
                len(f"{annotation_prefix} = {ast.unparse(value)}") > line_length
                and len(target_prefix) > LONG_TARGET_PREFIX_LENGTH
                and (_contains_annotated(annotation) or _is_simple_union_annotation(annotation))
            )
        )
    )


def _iter_subscript_elements(node: ast.Subscript) -> list[ast.AST]:
    if isinstance(node.slice, ast.Tuple):
        return list(node.slice.elts)
    return [node.slice]


def _format_annotated(  # noqa: PLR0913
    annotation: ast.Subscript,
    indent: str,
    line_length: int,
    source: str,
    closing_suffix: str = "",
    *,
    wrap_string_literal: bool = False,
) -> str:
    continuation_indent = f"{indent}    "
    inline_elements = [_source_segment(source, element) for element in _iter_subscript_elements(annotation)]
    joined_elements = ", ".join(inline_elements)
    if len(f"{continuation_indent}{joined_elements}") <= line_length:
        return f"Annotated[\n{continuation_indent}{joined_elements}\n{indent}]{closing_suffix}"

    formatted_lines: list[str] = ["Annotated["]
    for element in _iter_subscript_elements(annotation):
        if _is_call(element, "Field") or _is_call(element, "Meta"):
            inline_field = _source_segment(source, element)
            if len(f"{continuation_indent}{inline_field},") <= line_length:
                formatted_lines.append(f"{continuation_indent}{inline_field},")
                continue
            call_lines = _format_call(
                element,
                continuation_indent,
                line_length,
                source,
                wrap_string_literal=wrap_string_literal,
            ).splitlines()
            call_lines[-1] = f"{call_lines[-1]},"
            formatted_lines.extend(
                f"{continuation_indent}{line}" if index == 0 else line for index, line in enumerate(call_lines)
            )
        else:
            formatted_lines.append(f"{continuation_indent}{_source_segment(source, element)},")
    formatted_lines.append(f"{indent}]{closing_suffix}")
    return "\n".join(formatted_lines)


def _config_dict_assignment(statement: ast.stmt) -> tuple[ast.Assign, ast.Call] | None:
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and _is_call(statement.value, "ConfigDict"):
        return statement, statement.value
    return None


def _format_generated_class_statement(  # noqa: PLR0911, PLR0912
    statement: ast.stmt,
    line: str,
    line_length: int,
    source: str,
    *,
    wrap_string_literal: bool,
) -> str | None:
    config_dict = _config_dict_assignment(statement)
    config_dict_needs_formatting = config_dict is not None and (
        len(line) > line_length
        or any(
            isinstance(keyword.value, ast.Dict)
            and len(f"{line[: len(line) - len(line.lstrip())]}    {_format_call_argument(keyword, source)}")
            > line_length
            for keyword in config_dict[1].keywords
        )
    )
    if (len(line) <= line_length and not config_dict_needs_formatting) or "#" in line:
        return None

    indent = line[: len(line) - len(line.lstrip())]
    if isinstance(statement, ast.FunctionDef):
        before_arguments, _, after_open = line.partition("(")
        arguments, _, suffix = after_open.rpartition(")")
        if arguments and suffix.endswith(":"):
            return f"{before_arguments}(\n{indent}    {arguments}\n{indent}){suffix}"

    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        target = statement.target.id
        annotation = _source_segment(source, statement.annotation)
        if statement.value is None and _is_list_of_annotated(statement.annotation):
            return f"{indent}{target}: {_format_list_of_annotated(statement.annotation, indent, line_length, source)}"
        if _should_format_constrained_string_union(
            statement.annotation,
            statement.value,
            f"{indent}{target}: {annotation}",
            line_length,
            source,
        ):
            assert statement.value is not None
            value = _source_segment(source, statement.value)
            return (
                f"{indent}{target}: "
                f"{_format_constrained_string_union(statement.annotation, indent, line_length, source)} = {value}"
            )
        if (
            isinstance(statement.annotation, ast.BinOp)
            and isinstance(statement.annotation.op, ast.BitOr)
            and _is_call(statement.value, "Field")
            and len(f"{indent}{target}: {annotation}") > line_length
        ):
            value = _source_segment(source, statement.value)
            return f"{indent}{target}: (\n{indent}    {annotation}\n{indent}) = {value}"
        if (
            isinstance(statement.annotation, ast.BinOp)
            and isinstance(statement.annotation.op, ast.BitOr)
            and statement.value is not None
            and _contains_constrained_string_call(statement.annotation)
            and len(f"{indent}{target}: {annotation}") > line_length
        ):
            value = _source_segment(source, statement.value)
            return f"{indent}{target}: (\n{indent}    {annotation}\n{indent}) = {value}"
        if _should_format_union_annotation(
            statement.annotation,
            statement.value,
            f"{indent}{target}: ",
            f"{indent}{target}: {annotation}",
            line_length,
        ):
            assert statement.value is not None
            value = _source_segment(source, statement.value)
            return (
                f"{indent}{target}: "
                f"{_format_annotated_union(statement.annotation, indent, line_length, source)} = {value}"
            )
        if (
            _is_union(statement.annotation)
            and statement.value is not None
            and len(f"{indent}{target}: {annotation}") > line_length
        ):
            value = _source_segment(source, statement.value)
            return (
                f"{indent}{target}: "
                f"{_format_union_subscript(statement.annotation, indent, source, f' = {value}', line_length)}"
            )
        if _is_call(statement.value, "Field"):
            value = _source_segment(source, statement.value)
            value_prefix = f"{indent}{target}: {annotation} = "
            if (
                len(value_prefix) > line_length - 16
                and len(f"{value_prefix}{value}") > line_length
                and _can_parenthesize_field_value(statement.annotation, target)
            ):
                if len(f"{indent}    {value}") <= line_length:
                    return f"{value_prefix}(\n{indent}    {value}\n{indent})"
                formatted_value = _format_call(
                    statement.value,
                    f"{indent}    ",
                    line_length,
                    source,
                    wrap_string_literal=wrap_string_literal,
                )
                return f"{value_prefix}(\n{indent}    {formatted_value}\n{indent})"
            formatted_value = _format_call(
                statement.value,
                indent,
                line_length,
                source,
                wrap_string_literal=wrap_string_literal,
            )
            return f"{indent}{target}: {annotation} = {formatted_value}"
        if (
            _is_annotated(statement.annotation)
            and isinstance(statement.value, ast.List)
            and not any(isinstance(element, ast.Dict) for element in statement.value.elts)
            and len(f"{indent}{target}: {annotation} = {_source_segment(source, statement.value)}") > line_length
        ):
            closing_suffix = f" = {_source_segment(source, statement.value)}"
            formatted_annotation = _format_annotated(
                statement.annotation,
                indent,
                line_length,
                source,
                closing_suffix,
                wrap_string_literal=wrap_string_literal,
            )
            return f"{indent}{target}: {formatted_annotation}"
        if isinstance(statement.value, ast.Dict):
            return (
                f"{indent}{target}: {annotation} = {_format_dict_literal(statement.value, indent, source, line_length)}"
            )
        if isinstance(statement.value, ast.List):
            return f"{indent}{target}: {annotation} = {_format_list_literal(statement.value, indent, source)}"
        if _is_call(statement.value, "field"):
            formatted_value = _format_call(
                statement.value,
                indent,
                line_length,
                source,
                wrap_string_literal=wrap_string_literal,
            )
            return f"{indent}{target}: {annotation} = {formatted_value}"
        if _is_annotated(statement.annotation):
            if (
                statement.value is not None
                and len(f"{indent}{target}: {annotation}") <= line_length
                and len(line) <= line_length + MAX_SHORT_DEFAULT_OVERFLOW
            ):
                value = _source_segment(source, statement.value)
                return f"{indent}{target}: {annotation} = (\n{indent}    {value}\n{indent})"
            closing_suffix = "" if statement.value is None else f" = {_source_segment(source, statement.value)}"
            formatted_annotation = _format_annotated(
                statement.annotation,
                indent,
                line_length,
                source,
                closing_suffix,
                wrap_string_literal=wrap_string_literal,
            )
            return f"{indent}{target}: {formatted_annotation}"
        if statement.value is not None:
            value = _source_segment(source, statement.value)
            return f"{indent}{target}: {annotation} = (\n{indent}    {value}\n{indent})"

    if config_dict is not None and config_dict_needs_formatting:
        target = _source_segment(source, config_dict[0].targets[0])
        formatted_value = _format_call(
            config_dict[1],
            indent,
            line_length,
            source,
            force_trailing_comma=True,
            wrap_string_literal=wrap_string_literal,
        )
        return f"{indent}{target} = {formatted_value}"

    return None


def _format_constrained_string_union(
    annotation: ast.BinOp,
    indent: str,
    line_length: int,
    source: str,
) -> str:
    left = annotation.left
    right = annotation.right
    if _is_constrained_string_call(left):
        formatted_left = _format_constrained_call(left, f"{indent}    ", line_length, source)
        inline_union = f"{formatted_left} | {_source_segment(source, right)}"
        if "\n" not in formatted_left and len(f"{indent}    {inline_union}") <= line_length:
            return f"(\n{indent}    {inline_union}\n{indent})"
        return f"(\n{indent}    {formatted_left}\n{indent}    | {_source_segment(source, right)}\n{indent})"
    if _is_constrained_string_call(right):
        return f"{_source_segment(source, left)} | {_format_constrained_call(right, indent, line_length, source)}"
    return _source_segment(source, annotation)  # pragma: no cover


def _format_annotated_union(annotation: ast.BinOp, indent: str, line_length: int, source: str) -> str:
    left = annotation.left
    right = annotation.right
    inline_union = f"{_source_segment(source, left)} | {_source_segment(source, right)}"
    if len(f"{indent}    {inline_union}") <= line_length:
        return f"(\n{indent}    {inline_union}\n{indent})"
    if _is_annotated(left):
        if len(f"{indent}    {_source_segment(source, left)}") > line_length:
            annotated_lines = _format_annotated(left, f"{indent}    ", line_length, source).splitlines()
            formatted_annotated = "\n".join(
                f"{indent}    {line}" if index == 0 else line for index, line in enumerate(annotated_lines)
            )
        else:
            formatted_annotated = f"{indent}    {_source_segment(source, left)}"
        return f"(\n{formatted_annotated}\n{indent}    | {_source_segment(source, right)}\n{indent})"
    if _is_annotated(right):
        return (
            f"(\n{indent}    {_source_segment(source, left)}\n{indent}    | {_source_segment(source, right)}\n{indent})"
        )
    return f"(\n{indent}    {_source_segment(source, annotation)}\n{indent})"


def _format_list_of_annotated(annotation: ast.Subscript, indent: str, line_length: int, source: str) -> str:
    continuation_indent = f"{indent}    "
    assert _is_annotated(annotation.slice)
    inline_annotated = _source_segment(source, annotation.slice)
    if len(f"{continuation_indent}{inline_annotated}") <= line_length:
        formatted_annotated = f"{continuation_indent}{inline_annotated}"
    else:
        annotated_lines = _format_annotated(annotation.slice, continuation_indent, line_length, source).splitlines()
        formatted_annotated = "\n".join(
            f"{continuation_indent}{line}" if index == 0 else line for index, line in enumerate(annotated_lines)
        )
    return f"list[\n{formatted_annotated}\n{indent}]"


def _format_union_subscript(
    union: ast.Subscript,
    indent: str,
    source: str,
    closing_suffix: str = "",
    line_length: int = DEFAULT_LINE_LENGTH,
) -> str:
    continuation_indent = f"{indent}    "
    elements = [_source_segment(source, element) for element in _iter_subscript_elements(union)]
    joined_elements = ", ".join(elements)
    if len(f"{continuation_indent}{joined_elements}") <= line_length:
        return f"Union[\n{continuation_indent}{joined_elements}\n{indent}]{closing_suffix}"

    formatted_lines = ["Union["]
    formatted_lines.extend(f"{continuation_indent}{element}," for element in elements)
    formatted_lines.append(f"{indent}]{closing_suffix}")
    return "\n".join(formatted_lines)


def _format_type_alias_type_call(call: ast.Call, indent: str, line_length: int, source: str) -> str:
    continuation_indent = f"{indent}    "
    inline_arguments = ", ".join(_source_segment(source, argument) for argument in call.args)
    can_inline_type_alias_arguments = (
        len(call.args) == TYPE_ALIAS_INLINE_ARGUMENT_COUNT
        and not call.keywords
        and (_is_annotated(call.args[1]) or _is_union(call.args[1]))
        and "\n" not in inline_arguments
    )
    if can_inline_type_alias_arguments and len(f"{continuation_indent}{inline_arguments}") <= line_length:
        return f"TypeAliasType(\n{continuation_indent}{inline_arguments}\n{indent})"

    formatted_lines = ["TypeAliasType("]
    for argument in call.args:
        if _is_union(argument):
            union_lines = _format_union_subscript(argument, continuation_indent, source, ",", 0).splitlines()
            formatted_lines.extend(
                f"{continuation_indent}{line}" if index == 0 else line for index, line in enumerate(union_lines)
            )
        elif _is_annotated(argument):
            annotated_lines = _format_annotated(argument, continuation_indent, line_length, source, ",").splitlines()
            formatted_lines.extend(
                f"{continuation_indent}{line}" if index == 0 else line for index, line in enumerate(annotated_lines)
            )
        else:
            formatted_lines.append(f"{continuation_indent}{_source_segment(source, argument)},")
    formatted_lines.extend(
        f"{continuation_indent}{_format_call_argument(keyword, source)}," for keyword in call.keywords
    )
    formatted_lines.append(f"{indent})")
    return "\n".join(formatted_lines)


def _format_typed_dict_call(call: ast.Call, indent: str, source: str) -> str:
    continuation_indent = f"{indent}    "
    formatted_lines = ["TypedDict("]
    for argument in call.args:
        if isinstance(argument, ast.Dict):
            dict_lines = _format_dict_literal(argument, continuation_indent, source).splitlines()
            dict_lines[-1] = f"{dict_lines[-1]},"
            formatted_lines.extend(
                f"{continuation_indent}{line}" if index == 0 else line for index, line in enumerate(dict_lines)
            )
        else:
            formatted_lines.append(f"{continuation_indent}{_source_segment(source, argument)},")
    formatted_lines.extend(
        f"{continuation_indent}{_format_call_argument(keyword, source)}," for keyword in call.keywords
    )
    formatted_lines.append(f"{indent})")
    return "\n".join(formatted_lines)


def _is_root_model_constrained_union(base: ast.AST) -> TypeGuard[ast.Subscript]:
    return (
        isinstance(base, ast.Subscript)
        and _is_name_or_attr(base.value, "RootModel")
        and isinstance(base.slice, ast.BinOp)
        and isinstance(base.slice.op, ast.BitOr)
        and (_is_constrained_string_call(base.slice.left) or _is_constrained_string_call(base.slice.right))
    )


def _format_root_model_constrained_union_base(
    base: ast.Subscript,
    indent: str,
    line_length: int,
    source: str,
) -> str:
    continuation_indent = f"{indent}    "
    inner_indent = f"{continuation_indent}    "
    union = base.slice
    assert isinstance(union, ast.BinOp)
    formatted_lines = ["RootModel["]
    if _is_constrained_string_call(union.left):
        call_lines = _format_constrained_call(union.left, inner_indent, line_length, source).splitlines()
        formatted_lines.extend(f"{inner_indent}{line}" if index == 0 else line for index, line in enumerate(call_lines))
        formatted_lines.append(f"{inner_indent}| {_source_segment(source, union.right)}")
    elif _is_constrained_string_call(union.right):  # pragma: no branch
        formatted_lines.append(f"{inner_indent}{_source_segment(source, union.left)}")
        call_lines = _format_constrained_call(union.right, inner_indent, line_length, source).splitlines()
        formatted_lines.append(f"{inner_indent}| {call_lines[0]}")
        formatted_lines.extend(call_lines[1:])
    formatted_lines.append(f"{continuation_indent}]")
    return "\n".join(formatted_lines)


def _format_generated_class_definition(
    statement: ast.ClassDef,
    line: str,
    line_length: int,
    source: str,
) -> str | None:
    if len(line) <= line_length or "#" in line:
        return None

    indent = line[: len(line) - len(line.lstrip())]
    if len(statement.bases) > 1:
        formatted_bases = "\n".join(f"{indent}    {_source_segment(source, base)}," for base in statement.bases)
        return f"{indent}class {statement.name}(\n{formatted_bases}\n{indent}):"
    if len(statement.bases) != 1:
        return None

    if _is_root_model_constrained_union(statement.bases[0]):
        base = _format_root_model_constrained_union_base(statement.bases[0], indent, line_length, source)
    elif _is_name_or_attr(statement.bases[0], "RootModel") or (
        isinstance(statement.bases[0], ast.Subscript) and _is_name_or_attr(statement.bases[0].value, "RootModel")
    ):
        base = _source_segment(source, statement.bases[0])
    else:
        return None
    return f"{indent}class {statement.name}(\n{indent}    {base}\n{indent}):"


def _format_generated_module_statement(  # noqa: PLR0911
    statement: ast.stmt, line: str, line_length: int, source: str
) -> str | None:
    if "#" in line:
        return None
    if (
        sys.version_info >= (3, 12)
        and isinstance(statement, ast.TypeAlias)
        and _is_annotated(statement.value)
        and len(line) > line_length
    ):
        indent = line[: len(line) - len(line.lstrip())]
        target = _source_segment(source, statement.name)
        return f"{indent}type {target} = {_format_annotated(statement.value, indent, line_length, source)}"
    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
        return None
    if _is_call(statement.value, "TypedDict") and any(
        isinstance(argument, ast.Dict) for argument in statement.value.args
    ):
        indent = line[: len(line) - len(line.lstrip())]
        target = _source_segment(source, statement.targets[0])
        return f"{indent}{target} = {_format_typed_dict_call(statement.value, indent, source)}"
    if not _is_call(statement.value, "TypeAliasType"):
        return None
    if not any(
        (
            _is_union(argument)
            and (len(line) > line_length or argument.lineno != (argument.end_lineno or argument.lineno))
        )
        or (_is_annotated(argument) and len(line) > line_length)
        for argument in statement.value.args
    ):
        return None
    if len(line) <= line_length and statement.lineno == (statement.end_lineno or statement.lineno):
        return None  # pragma: no cover

    indent = line[: len(line) - len(line.lstrip())]
    target = _source_segment(source, statement.targets[0])
    return f"{indent}{target} = {_format_type_alias_type_call(statement.value, indent, line_length, source)}"


def _format_type_checking_block(
    node: ast.If, lines: list[str], line_length: int, known_first_party: frozenset[str]
) -> str | None:
    import_nodes = [statement for statement in node.body if isinstance(statement, (ast.Import, ast.ImportFrom))]
    if not import_nodes or len(import_nodes) != len(node.body):
        return None

    indent = lines[node.lineno - 1][: len(lines[node.lineno - 1]) - len(lines[node.lineno - 1].lstrip())]
    import_block = _build_builtin_import_block(import_nodes, line_length, lines, known_first_party)
    indented_import_block = "\n".join(f"{indent}    {line}" if line else line for line in import_block.splitlines())
    return f"{indent}if TYPE_CHECKING:\n{indented_import_block}"


_LineReplacement = tuple[int, int, list[str]]


def _collect_builtin_replacements(  # noqa: PLR0912, PLR0913
    tree: ast.Module,
    lines: list[str],
    line_length: int,
    source: str,
    known_first_party: frozenset[str],
    *,
    wrap_string_literal: bool,
) -> list[_LineReplacement]:
    replacements: list[_LineReplacement] = []
    for node in tree.body:
        if _is_type_checking_if(node):
            formatted_type_checking = _format_type_checking_block(node, lines, line_length, known_first_party)
            if formatted_type_checking is not None:
                replacements.append((node.lineno, node.end_lineno or node.lineno, formatted_type_checking.splitlines()))
            continue

        formatted_statement = _format_generated_module_statement(node, lines[node.lineno - 1], line_length, source)
        if formatted_statement is not None:
            replacements.append((node.lineno, node.end_lineno or node.lineno, formatted_statement.splitlines()))

        if isinstance(node, ast.ClassDef):
            formatted_definition = _format_generated_class_definition(node, lines[node.lineno - 1], line_length, source)
            if formatted_definition is not None:
                replacements.append((node.lineno, node.lineno, formatted_definition.splitlines()))
            if len(node.body) > 1 and (docstring_node := _docstring_node(node.body[0])) is not None:
                docstring_end = docstring_node.end_lineno or docstring_node.lineno
                next_statement = node.body[1]
                if docstring_end + 1 == next_statement.lineno:
                    replacements.append((docstring_end, docstring_end, [lines[docstring_end - 1], ""]))
                elif docstring_end + 2 < next_statement.lineno:
                    replacements.append((docstring_end + 1, next_statement.lineno - 1, [""]))
            for previous_statement, next_statement in zip(node.body, node.body[1:], strict=False):
                if previous_statement is node.body[0] and _docstring_node(previous_statement) is not None:
                    continue
                previous_end = previous_statement.end_lineno or previous_statement.lineno
                next_start = min(
                    (decorator.lineno for decorator in getattr(next_statement, "decorator_list", [])),
                    default=next_statement.lineno,
                )
                if previous_end + 2 < next_start:
                    replacements.append((previous_end + 1, next_start - 1, [""]))
            for statement in node.body:
                is_long_function_definition = (
                    isinstance(statement, ast.FunctionDef) and len(lines[statement.lineno - 1]) > line_length
                )
                if (
                    statement.lineno != (statement.end_lineno or statement.lineno)
                    and not is_long_function_definition
                    and not (
                        isinstance(statement, ast.Assign)
                        and len(statement.targets) == 1
                        and _is_call(statement.value, "ConfigDict")
                    )
                ):
                    continue
                formatted_statement = _format_generated_class_statement(
                    statement,
                    lines[statement.lineno - 1],
                    line_length,
                    source,
                    wrap_string_literal=wrap_string_literal,
                )
                if formatted_statement is not None:
                    replacement_end = statement.lineno if is_long_function_definition else statement.end_lineno
                    replacements.append((
                        statement.lineno,
                        replacement_end or statement.lineno,
                        formatted_statement.splitlines(),
                    ))

    return replacements


def _module_docstring_node(tree: ast.Module) -> ast.Expr | None:
    if not tree.body:
        return None
    return _docstring_node(tree.body[0])


def _docstring_node(first_node: ast.stmt) -> ast.Expr | None:
    if (
        isinstance(first_node, ast.Expr)
        and isinstance(first_node.value, ast.Constant)
        and isinstance(first_node.value.value, str)
    ):
        return first_node
    return None


def _leading_lines_before_imports(lines: list[str], first_import_line: int, tree: ast.Module) -> list[str]:
    leading_lines = list(lines[: first_import_line - 1])
    docstring_node = _module_docstring_node(tree)
    if (
        docstring_node is not None
        and docstring_node.end_lineno == len(leading_lines)
        and (not leading_lines or leading_lines[-1].strip())
    ):
        leading_lines.append("")
    return leading_lines


def _iter_module_import_nodes(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
    body_nodes = tree.body
    docstring_node = _module_docstring_node(tree)
    if docstring_node is not None:
        body_nodes = body_nodes[1:]

    import_nodes: list[ast.Import | ast.ImportFrom] = []
    for node in body_nodes:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            break
        import_nodes.append(node)
    return import_nodes


def _apply_line_replacements(lines: list[str], replacements: list[_LineReplacement], *, offset: int = 0) -> list[str]:
    formatted_lines = list(lines)
    for start, end, replacement_lines in sorted(replacements, reverse=True):
        start_index = start - offset - 1
        end_index = end - offset
        if start_index < 0 or end_index > len(formatted_lines):  # pragma: no cover
            continue
        formatted_lines[start_index:end_index] = replacement_lines
    return formatted_lines


def _normalize_top_level_blank_lines(code: str) -> str:
    string_lines: set[int] = set()
    for token in tokenize.generate_tokens(StringIO(code).readline):
        if token.type == tokenize.STRING and token.start[0] != token.end[0]:
            string_lines.update(range(token.start[0], token.end[0] + 1))

    lines = code.splitlines()
    formatted_lines: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        if line and not line.startswith((" ", "\t")) and line_number not in string_lines:
            if line.startswith(("@", "class ", "def ", "async def ")):
                previous_line_index = len(formatted_lines) - 1
                while previous_line_index >= 0 and not formatted_lines[previous_line_index]:
                    previous_line_index -= 1
                if previous_line_index >= 0 and formatted_lines[previous_line_index].startswith("@"):
                    while formatted_lines and not formatted_lines[-1]:
                        formatted_lines.pop()
                elif (
                    line.startswith(("class ", "def ", "async def "))
                    and previous_line_index >= 0
                    and not formatted_lines[previous_line_index].startswith((" ", "\t"))
                ):
                    while len(formatted_lines) - previous_line_index - 1 < MAX_TOP_LEVEL_BLANK_LINES:
                        formatted_lines.append("")
            while len(formatted_lines) > MAX_TOP_LEVEL_BLANK_LINES and formatted_lines[
                -(MAX_TOP_LEVEL_BLANK_LINES + 1) :
            ] == [""] * (MAX_TOP_LEVEL_BLANK_LINES + 1):
                formatted_lines.pop()
        formatted_lines.append(line)
    return "\n".join(formatted_lines)


def _normalize_string_quotes(code: str) -> str:
    tokens: list[tokenize.TokenInfo] = []
    for token in tokenize.generate_tokens(StringIO(code).readline):
        normalized_token = token
        if token.type == tokenize.STRING:
            match = STRING_PREFIX_PATTERN.match(token.string)
            if match is not None:  # pragma: no branch
                prefix, quote = match.groups()
                if quote == "'":
                    body = token.string[match.end() : -1]
                    if '"' not in body and not body.endswith("\\"):
                        normalized_token = tokenize.TokenInfo(
                            token.type,
                            f'{prefix}"{body}"',
                            token.start,
                            token.end,
                            token.line,
                        )
        tokens.append(normalized_token)
    return tokenize.untokenize(tokens)


def apply_builtin_formatter(  # noqa: PLR0913
    code: str,
    *,
    line_length: int = DEFAULT_LINE_LENGTH,
    known_first_party: frozenset[str] = DEFAULT_KNOWN_FIRST_PARTY,
    wrap_string_literal: bool = False,
    string_normalization: bool = False,
    python_version: PythonVersion | None = None,
) -> str:
    """Apply dependency-free formatting for generated Python code."""
    lines = [line.rstrip() for line in code.splitlines()]
    code = "\n".join(lines).strip("\n")
    if not code:
        return ""

    try:
        tree = ast.parse(code, feature_version=python_version.version_key if python_version is not None else None)
    except SyntaxError:
        return f"{code}\n"

    replacements = _collect_builtin_replacements(
        tree,
        lines,
        line_length,
        code,
        known_first_party,
        wrap_string_literal=wrap_string_literal,
    )
    import_nodes = _iter_module_import_nodes(tree)

    if not import_nodes:
        formatted_lines = _apply_line_replacements(lines, replacements)
        formatted_code = "\n".join(formatted_lines).strip("\n")
        formatted_code = _normalize_top_level_blank_lines(formatted_code)
        if string_normalization:
            formatted_code = _normalize_string_quotes(formatted_code)
        return f"{formatted_code}\n"

    first_line = import_nodes[0].lineno
    last_line = import_nodes[-1].end_lineno or import_nodes[-1].lineno
    leading = "\n".join(_leading_lines_before_imports(lines, first_line, tree))
    body_lines = _apply_line_replacements(lines[last_line:], replacements, offset=last_line)
    body = "\n".join(body_lines).strip("\n")
    import_block = _build_builtin_import_block(import_nodes, line_length, lines, known_first_party)
    formatted_code = f"{leading}\n{import_block}" if leading else import_block
    if body:
        separator = "\n\n\n" if body.startswith(("class ", "def ", "async def ", "@")) else "\n\n"
        formatted_code = f"{formatted_code}{separator}{body}" if formatted_code else body
    formatted_code = _normalize_top_level_blank_lines(formatted_code)
    if string_normalization:
        formatted_code = _normalize_string_quotes(formatted_code)
    return f"{formatted_code}\n"


def resolve_use_type_checking_imports(
    use_type_checking_imports: bool | None,  # noqa: FBT001
    *,
    is_multi_module_output: bool,
    formatters: list[Formatter] | None,
    requires_runtime_imports_with_ruff_check: bool,
) -> bool:
    """Resolve the effective TYPE_CHECKING import behavior."""
    if use_type_checking_imports is not None:
        return use_type_checking_imports

    has_ruff_check = bool(formatters) and Formatter.RUFF_CHECK in formatters
    return not (is_multi_module_output and has_ruff_check and requires_runtime_imports_with_ruff_check)


class CodeFormatter:
    """Formats generated code using black, isort, ruff, and custom formatters."""

    def __init__(  # noqa: PLR0912, PLR0913, PLR0915, PLR0917
        self,
        python_version: PythonVersion,
        settings_path: Path | None = None,
        wrap_string_literal: bool | None = None,  # noqa: FBT001
        skip_string_normalization: bool = True,  # noqa: FBT001, FBT002
        known_third_party: list[str] | None = None,
        custom_formatters: list[str] | None = None,
        custom_formatters_kwargs: dict[str, Any] | None = None,
        encoding: str = "utf-8",
        formatters: list[Formatter] | None = None,
        builtin_format_line_length: int | None = None,
        use_type_checking_imports: bool = True,  # noqa: FBT001, FBT002
        defer_formatting: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize code formatter with configuration for black, isort, ruff, and custom formatters."""
        if formatters is None:
            warn_deprecated(
                "format.default-formatters",
                details=(
                    "To keep the current behavior, specify formatters=[Formatter.BLACK, Formatter.ISORT]. "
                    "To prepare for dependency-free formatting, use formatters=[Formatter.BUILTIN]. "
                    "To suppress this warning, specify formatters explicitly."
                ),
                stacklevel=2,
            )
            formatters = list(DEFAULT_FORMATTERS)

        if not settings_path:
            settings_path = Path.cwd()
        elif settings_path.is_file():
            settings_path = settings_path.parent
        elif not settings_path.exists():
            for parent in settings_path.parents:
                if parent.exists():
                    settings_path = parent
                    break
            else:
                settings_path = Path.cwd()  # pragma: no cover

        self.settings_path: str = str(settings_path)
        self.formatters = formatters
        self.defer_formatting = defer_formatting
        self.encoding = encoding
        self.use_type_checking_imports = use_type_checking_imports
        self.python_version = python_version

        has_external_formatter = bool(EXTERNAL_FORMATTERS.intersection(formatters))
        if Formatter.BUILTIN in formatters and has_external_formatter:
            warn(
                "The built-in formatter is ignored when an external formatter is selected.",
                UserWarning,
                stacklevel=2,
            )
        use_builtin = Formatter.BUILTIN in formatters and not has_external_formatter
        use_black = Formatter.BLACK in formatters
        use_isort = Formatter.ISORT in formatters
        self.use_builtin_formatter = use_builtin

        self.builtin_line_length = (
            _get_builtin_line_length(settings_path, builtin_format_line_length) if use_builtin else DEFAULT_LINE_LENGTH
        )
        self.builtin_known_first_party = (
            _get_builtin_known_first_party(settings_path) if use_builtin else DEFAULT_KNOWN_FIRST_PARTY
        )
        self.builtin_wrap_string_literal = bool(wrap_string_literal)
        self.builtin_string_normalization = (
            _get_builtin_string_normalization(settings_path, skip_string_normalization=skip_string_normalization)
            if use_builtin
            else False
        )

        if use_black:
            root = black_find_project_root((settings_path,))
            path = root / "pyproject.toml"
            if path.is_file():
                pyproject_toml = load_toml(path)
                config = pyproject_toml.get("tool", {}).get("black", {})
            else:
                config = {}

            black = _get_black()
            black_mode = _get_black_mode()

            black_kwargs: dict[str, Any] = {}
            if wrap_string_literal is not None:
                experimental_string_processing = wrap_string_literal
            elif black.__version__ < "24.1.0":  # pragma: no cover
                experimental_string_processing = config.get("experimental-string-processing")
            else:
                experimental_string_processing = config.get("preview", False) and (  # pragma: no cover
                    config.get("unstable", False) or "string_processing" in config.get("enable-unstable-feature", [])
                )

            if experimental_string_processing is not None:  # pragma: no cover
                if black.__version__.startswith("19."):
                    warn(
                        f"black doesn't support `experimental-string-processing` option"
                        f" for wrapping string literal in {black.__version__}",
                        stacklevel=2,
                    )
                elif black.__version__ < "24.1.0":
                    black_kwargs["experimental_string_processing"] = experimental_string_processing
                elif experimental_string_processing:
                    black_kwargs["preview"] = True
                    black_kwargs["unstable"] = config.get("unstable", False)
                    black_kwargs["enabled_features"] = {black_mode.Preview.string_processing}

            self.black_mode = black.FileMode(
                target_versions={_get_black_python_version_map()[python_version]},
                line_length=config.get("line-length", black.DEFAULT_LINE_LENGTH),
                string_normalization=not skip_string_normalization or not config.get("skip-string-normalization", True),
                **black_kwargs,
            )
        else:
            self.black_mode = None  # type: ignore[assignment]

        if use_isort:
            isort = _get_isort()
            self.isort_config_kwargs: dict[str, Any] = {}
            if known_third_party:
                self.isort_config_kwargs["known_third_party"] = known_third_party

            if isort.__version__.startswith("4."):  # pragma: no cover
                self.isort_config = None
            else:
                self.isort_config = isort.Config(settings_path=self.settings_path, **self.isort_config_kwargs)
        else:
            self.isort_config_kwargs = {}
            self.isort_config = None

        self.custom_formatters_kwargs = custom_formatters_kwargs or {}
        self.custom_formatters = self._check_custom_formatters(custom_formatters)

    def _load_custom_formatter(self, custom_formatter_import: str) -> CustomCodeFormatter:
        """Load and instantiate a custom formatter from a module path."""
        import_ = import_module(custom_formatter_import)

        if not hasattr(import_, "CodeFormatter"):
            msg = f"Custom formatter module `{import_.__name__}` must contains object with name CodeFormatter"
            raise NameError(msg)

        formatter_class = import_.__getattribute__("CodeFormatter")  # noqa: PLC2801

        if not issubclass(formatter_class, CustomCodeFormatter):
            msg = f"The custom module {custom_formatter_import} must inherit from `datamodel-code-generator`"
            raise TypeError(msg)

        return formatter_class(formatter_kwargs=self.custom_formatters_kwargs)

    def _check_custom_formatters(self, custom_formatters: list[str] | None) -> list[CustomCodeFormatter]:
        """Validate and load all custom formatters."""
        if custom_formatters is None:
            return []

        return [self._load_custom_formatter(custom_formatter_import) for custom_formatter_import in custom_formatters]

    def format_code(
        self,
        code: str,
    ) -> str:
        """Apply all configured formatters to the code string."""
        if Formatter.ISORT in self.formatters:
            code = self.apply_isort(code)
        if self.use_builtin_formatter:
            code = self.apply_builtin_formatter(
                code,
                line_length=self.builtin_line_length,
                known_first_party=self.builtin_known_first_party,
                wrap_string_literal=self.builtin_wrap_string_literal,
                string_normalization=self.builtin_string_normalization,
                python_version=self.python_version,
            )
        if Formatter.BLACK in self.formatters:
            code = self.apply_black(code)

        if not self.defer_formatting:
            has_ruff_check = Formatter.RUFF_CHECK in self.formatters
            has_ruff_format = Formatter.RUFF_FORMAT in self.formatters
            if has_ruff_check and has_ruff_format:
                code = self.apply_ruff_check_and_format(code)
            elif has_ruff_check:
                code = self.apply_ruff_lint(code)
            elif has_ruff_format:
                code = self.apply_ruff_formatter(code)

        for formatter in self.custom_formatters:
            code = formatter.apply(code)

        return code

    def apply_black(self, code: str) -> str:
        """Format code using black."""
        black = _get_black()
        return black.format_str(
            code,
            mode=self.black_mode,
        )

    @staticmethod
    def apply_builtin_formatter(  # noqa: PLR0913
        code: str,
        *,
        line_length: int = DEFAULT_LINE_LENGTH,
        known_first_party: frozenset[str] = DEFAULT_KNOWN_FIRST_PARTY,
        wrap_string_literal: bool = False,
        string_normalization: bool = False,
        python_version: PythonVersion | None = None,
    ) -> str:
        """Format generated code without external formatter dependencies."""
        return apply_builtin_formatter(
            code,
            line_length=line_length,
            known_first_party=known_first_party,
            wrap_string_literal=wrap_string_literal,
            string_normalization=string_normalization,
            python_version=python_version,
        )

    def apply_ruff_lint(self, code: str) -> str:
        """Run ruff check with auto-fix on code."""
        result = subprocess.run(  # noqa: S603
            self._ruff_check_command("-"),
            input=code.encode(self.encoding),
            capture_output=True,
            check=False,
            cwd=self.settings_path,
        )
        return result.stdout.decode(self.encoding)

    def apply_ruff_formatter(self, code: str) -> str:
        """Format code using ruff format."""
        ruff_path = self._find_ruff_path()
        result = subprocess.run(  # noqa: S603
            (ruff_path, "format", "-"),
            input=code.encode(self.encoding),
            capture_output=True,
            check=False,
            cwd=self.settings_path,
        )
        return result.stdout.decode(self.encoding)

    def apply_ruff_check_and_format(self, code: str) -> str:
        """Run ruff check and format sequentially for reliable processing."""
        ruff_path = self._find_ruff_path()
        check_result = subprocess.run(  # noqa: S603
            self._ruff_check_command("-", ruff_path=ruff_path),
            input=code.encode(self.encoding),
            capture_output=True,
            check=False,
            cwd=self.settings_path,
        )
        format_result = subprocess.run(  # noqa: S603
            (ruff_path, "format", "-"),
            input=check_result.stdout,
            capture_output=True,
            check=False,
            cwd=self.settings_path,
        )
        return format_result.stdout.decode(self.encoding)

    def _ruff_check_command(self, *paths: str, ruff_path: str | None = None) -> tuple[str, ...]:
        """Build the Ruff check command for the current formatter settings."""
        if ruff_path is None:
            ruff_path = self._find_ruff_path()
        command: tuple[str, ...] = (ruff_path, "check", "--fix", "--unsafe-fixes")
        if not self.use_type_checking_imports:
            command += ("--unfixable", "TC001,TC002,TC003")
        return (*command, *paths)

    @staticmethod
    def _find_ruff_path() -> str:
        """Find ruff executable path, checking virtual environment first."""
        bin_dir = Path(sys.executable).parent
        ruff_name = "ruff.exe" if sys.platform == "win32" else "ruff"
        ruff_in_venv = bin_dir / ruff_name
        if ruff_in_venv.exists():
            return str(ruff_in_venv)
        return shutil.which("ruff") or "ruff"  # pragma: no cover

    def apply_isort(self, code: str) -> str:
        """Sort imports using isort."""
        isort = _get_isort()
        if self.isort_config is None:  # pragma: no cover
            return isort.SortImports(
                file_contents=code,
                settings_path=self.settings_path,
                **self.isort_config_kwargs,
            ).output
        return isort.code(code, config=self.isort_config)

    def format_directory(self, directory: Path) -> None:
        """Apply ruff formatting to all Python files in a directory."""
        ruff_path = self._find_ruff_path()
        if Formatter.RUFF_CHECK in self.formatters:
            subprocess.run(  # noqa: S603
                self._ruff_check_command(str(directory), ruff_path=ruff_path),
                capture_output=True,
                check=False,
                cwd=self.settings_path,
            )
        if Formatter.RUFF_FORMAT in self.formatters:
            subprocess.run(  # noqa: S603
                (ruff_path, "format", str(directory)),
                capture_output=True,
                check=False,
                cwd=self.settings_path,
            )


class CustomCodeFormatter:
    """Base class for custom code formatters.

    Subclasses must implement the apply() method to transform code.
    """

    def __init__(self, formatter_kwargs: dict[str, Any]) -> None:
        """Initialize custom formatter with optional keyword arguments."""
        self.formatter_kwargs = formatter_kwargs

    def apply(self, code: str) -> str:
        """Apply formatting to code. Must be implemented by subclasses."""
        raise NotImplementedError
