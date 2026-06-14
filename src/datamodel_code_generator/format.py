"""Code formatting utilities and Python version handling.

Provides CodeFormatter for applying black, isort, and ruff formatting,
along with PythonVersion enum and DatetimeClassType for output configuration.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # noqa: S404
import sys
from enum import Enum
from functools import cached_property, lru_cache
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any
from warnings import warn

from datamodel_code_generator.deprecations import warn_deprecated
from datamodel_code_generator.util import load_toml

if TYPE_CHECKING:
    from collections.abc import Sequence


DEFAULT_LINE_LENGTH = 88
DEFAULT_KNOWN_FIRST_PARTY = frozenset({"datamodel_code_generator", "tests"})
MAX_TOP_LEVEL_BLANK_LINES = 2
MAX_SHORT_DEFAULT_OVERFLOW = 13
LONG_TARGET_PREFIX_LENGTH = 30
TYPE_ALIAS_INLINE_ARGUMENT_COUNT = 2
STRING_PREFIX_PATTERN = re.compile(r"(?i)^([rubf]*)(\"\"\"|'''|\"|')")


# Keep the re-export shim visible to auto-fixers without changing star-import behavior.
_BUILTIN_FORMATTER_REEXPORTS: tuple[str, ...] = (
    "_AliasSortCategory",
    "_ImportCategory",
    "DEFAULT_LINE_LENGTH",
    "DEFAULT_KNOWN_FIRST_PARTY",
    "MAX_TOP_LEVEL_BLANK_LINES",
    "MAX_SHORT_DEFAULT_OVERFLOW",
    "LONG_TARGET_PREFIX_LENGTH",
    "TYPE_ALIAS_INLINE_ARGUMENT_COUNT",
    "STRING_PREFIX_PATTERN",
    "_is_valid_builtin_line_length",
    "_line_indent",
    "_indent_first_line",
    "_find_pyproject_toml",
    "_get_builtin_line_length",
    "_get_builtin_known_first_party",
    "_get_builtin_string_normalization",
    "_format_alias",
    "_alias_imported_name",
    "_alias_sort_key",
    "_format_from_import",
    "_import_category",
    "_has_inline_comment",
    "_format_import_node_without_reordering",
    "_import_node_category",
    "_format_import_node",
    "_from_import_key",
    "_modules_with_aliased_imports",
    "_can_merge_from_imports",
    "_iter_aliased_from_import_lines",
    "_import_line_sort_key",
    "_build_builtin_import_block",
    "_is_name_or_attr",
    "_is_type_checking_if",
    "_source_segment",
    "_inline_source_segment",
    "_format_call_argument",
    "_format_dict_literal",
    "_format_list_literal",
    "_split_escaped_string_literal",
    "_format_wrapped_string_literal",
    "_format_call_argument_for_block",
    "_format_call",
    "_format_constrained_call",
    "_is_call",
    "_has_attribute_root",
    "_is_datetime_module_call",
    "_is_annotated",
    "_is_list_of_annotated",
    "_is_union",
    "_CONSTRAINED_CALL_NAMES",
    "_is_constrained_string_call",
    "_is_constrained_call",
    "_contains_constrained_string_call",
    "_contains_annotated",
    "_contains_list_of_annotated",
    "_is_simple_union_annotation",
    "_should_format_constrained_call_union",
    "_can_parenthesize_field_value",
    "_should_format_union_annotation",
    "_iter_bit_or_elements",
    "_format_bit_or_element",
    "_format_bit_or_elements",
    "_format_parenthesized_bit_or_annotation",
    "_should_format_field_bit_or_annotation_assignment",
    "_should_format_field_bit_or_value_assignment",
    "_format_parenthesized_field_value",
    "_should_format_string_bit_or_annotation_assignment",
    "_format_bit_or_annotation_assignment",
    "_iter_subscript_elements",
    "_format_annotated",
    "_config_dict_assignment",
    "_format_generated_annotation_assignment",
    "_format_generated_class_statement",
    "_format_constrained_call_union",
    "_format_annotated_union",
    "_format_list_of_annotated",
    "_format_union_subscript",
    "_format_subscript_value",
    "_format_type_alias_type_call",
    "_format_type_alias_union_assignment",
    "_format_typed_dict_call",
    "_is_root_model_constrained_union",
    "_format_root_model_constrained_union_base",
    "_format_root_model_union_base",
    "_format_generated_class_definition",
    "_format_generated_module_statement",
    "_format_type_checking_block",
    "_LineReplacement",
    "_collect_builtin_replacements",
    "_module_docstring_node",
    "_docstring_node",
    "_leading_lines_before_imports",
    "_iter_module_import_nodes",
    "_apply_line_replacements",
    "_previous_non_empty_line_index",
    "_ensure_post_class_annotation_assignment_spacing",
    "_normalize_top_level_blank_lines",
    "_normalize_string_quotes",
    "_finalize_builtin_code",
)


@lru_cache(maxsize=1)
def _get_builtin_formatter_module() -> Any:
    from datamodel_code_generator import _builtin_formatter  # noqa: PLC0415

    return _builtin_formatter


def _builtin_formatter_attr(name: str) -> Any:
    return getattr(_get_builtin_formatter_module(), name)


def _builtin_formatter_global(name: str) -> Any:
    return getattr(sys.modules[__name__], name)


def __getattr__(name: str) -> Any:
    if name not in _BUILTIN_FORMATTER_REEXPORTS:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    value = _builtin_formatter_attr(name)
    globals()[name] = value
    return value


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


_ISORT_CONFIG_FILENAMES = ("pyproject.toml", ".isort.cfg", "setup.cfg", "tox.ini", ".editorconfig")
_ISORT_CONFIG_STOP_DIRS = (".git", ".hg")
_IsortConfigFileStats = tuple[tuple[str, int, int], ...]


def _get_isort_config_file_stats(settings_path: str) -> _IsortConfigFileStats:
    """Return file stats for isort config candidates that can invalidate cached configs."""
    current_path = Path(settings_path).resolve()
    search_path = current_path if current_path.is_dir() else current_path.parent
    config_stats: list[tuple[str, int, int]] = []

    for directory in (search_path, *search_path.parents):
        for filename in _ISORT_CONFIG_FILENAMES:
            candidate = directory / filename
            try:
                stat = candidate.stat()
            except FileNotFoundError:
                continue
            if candidate.is_file():
                config_stats.append((str(candidate), stat.st_mtime_ns, stat.st_size))
        if any((directory / stop_dir).exists() for stop_dir in _ISORT_CONFIG_STOP_DIRS):
            break

    return tuple(config_stats)


@lru_cache(maxsize=128)
def _get_cached_isort_config(
    settings_path: str,
    known_third_party: tuple[str, ...],
    config_file_stats: _IsortConfigFileStats,
) -> Any:
    """Return a reusable isort Config for equivalent formatter settings."""
    del config_file_stats
    kwargs: dict[str, Any] = {}
    if known_third_party:
        kwargs["known_third_party"] = list(known_third_party)
    return _get_isort().Config(settings_path=settings_path, **kwargs)


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
        return self.version_key >= (3, 11)

    @cached_property
    def _is_py_312_or_later(self) -> bool:  # pragma: no cover
        return self.version_key >= (3, 12)

    @cached_property
    def _is_py_313_or_later(self) -> bool:
        return self.version_key >= (3, 13)

    @cached_property
    def _is_py_314_or_later(self) -> bool:
        return self.version_key >= (3, 14)

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
    return _builtin_formatter_attr("apply_builtin_formatter")(
        code,
        line_length=line_length,
        known_first_party=known_first_party,
        wrap_string_literal=wrap_string_literal,
        string_normalization=string_normalization,
        python_version=python_version,
    )


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

    def __init__(  # noqa: PLR0912, PLR0913, PLR0914, PLR0915, PLR0917
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

        builtin_tool_config: dict[str, Any] | None = None
        if use_builtin:
            is_valid_builtin_line_length = _builtin_formatter_global("_is_valid_builtin_line_length")
            if builtin_format_line_length is not None and not is_valid_builtin_line_length(builtin_format_line_length):
                msg = "builtin_format_line_length must be a positive integer"
                raise ValueError(msg)
            if (pyproject_toml_path := _builtin_formatter_global("_find_pyproject_toml")(settings_path)) is not None:
                builtin_tool_config = load_toml(pyproject_toml_path).get("tool", {})
            else:
                builtin_tool_config = {}

        self.builtin_line_length = (
            _builtin_formatter_global("_get_builtin_line_length")(
                settings_path,
                builtin_format_line_length,
                tool_config=builtin_tool_config,
            )
            if use_builtin
            else DEFAULT_LINE_LENGTH
        )
        self.builtin_known_first_party = (
            _builtin_formatter_global("_get_builtin_known_first_party")(
                settings_path,
                tool_config=builtin_tool_config,
            )
            if use_builtin
            else DEFAULT_KNOWN_FIRST_PARTY
        )
        self.builtin_wrap_string_literal = bool(wrap_string_literal)
        self.builtin_string_normalization = (
            _builtin_formatter_global("_get_builtin_string_normalization")(
                settings_path,
                skip_string_normalization=skip_string_normalization,
                tool_config=builtin_tool_config,
            )
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
            known_third_party_key: tuple[str, ...] = ()
            if known_third_party:
                self.isort_config_kwargs["known_third_party"] = known_third_party
                known_third_party_key = tuple(known_third_party)

            if isort.__version__.startswith("4."):  # pragma: no cover
                self.isort_config = None
            else:
                isort_settings_path = str(Path(self.settings_path).resolve())
                self.isort_config = _get_cached_isort_config(
                    isort_settings_path,
                    known_third_party_key,
                    _get_isort_config_file_stats(isort_settings_path),
                )
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
