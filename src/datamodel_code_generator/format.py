"""Code formatting utilities and Python version handling.

Provides CodeFormatter for applying black, isort, and ruff formatting,
along with PythonVersion enum and DatetimeClassType for output configuration.
"""

from __future__ import annotations

import ast
import shutil
import subprocess  # noqa: S404
import sys
from collections import defaultdict
from enum import Enum
from functools import cached_property, lru_cache
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any
from warnings import warn

from datamodel_code_generator.util import load_toml

if TYPE_CHECKING:
    from collections.abc import Sequence


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
        warn(
            "has_type_alias is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
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
DEFAULT_LINE_LENGTH = 88


def _find_pyproject_toml(settings_path: Path) -> Path | None:
    for path in (settings_path, *settings_path.parents):
        pyproject_toml = path / "pyproject.toml"
        if pyproject_toml.is_file():
            return pyproject_toml
    return None


def _get_builtin_line_length(settings_path: Path, explicit_line_length: int | None = None) -> int:
    if explicit_line_length is not None:
        return explicit_line_length

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
        if isinstance(line_length, int):
            return line_length
    return DEFAULT_LINE_LENGTH


def _format_alias(alias: ast.alias) -> str:
    if alias.asname:
        return f"{alias.name} as {alias.asname}"
    return alias.name


def _format_from_import(module: str, aliases: list[str], line_length: int) -> str:
    line = f"from {module} import {', '.join(aliases)}"
    if len(line) <= line_length and "*" not in aliases:
        return line
    imports = "\n".join(f"    {alias}," for alias in aliases)
    return f"from {module} import (\n{imports}\n)"


def _import_category(module: str, level: int) -> int:
    if module == "__future__":
        return 0
    if level:
        return 3
    top_level_module = module.split(".", 1)[0]
    if top_level_module in sys.stdlib_module_names:
        return 1
    return 2


def _build_builtin_import_block(import_nodes: list[ast.Import | ast.ImportFrom], line_length: int) -> str:
    categorized_lines: defaultdict[int, set[str]] = defaultdict(set)
    grouped_from_imports: defaultdict[tuple[int, int, str], set[str]] = defaultdict(set)

    for node in import_nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                line = f"import {_format_alias(alias)}"
                categorized_lines[_import_category(alias.name, 0)].add(line)
            continue

        module = "." * node.level + (node.module or "")
        category = _import_category(node.module or "", node.level)
        for alias in node.names:
            grouped_from_imports[category, node.level, module].add(_format_alias(alias))

    for (category, _level, module), aliases in grouped_from_imports.items():
        categorized_lines[category].add(_format_from_import(module, sorted(aliases), line_length))

    groups = ["\n".join(sorted(categorized_lines[category])) for category in sorted(categorized_lines)]
    return "\n\n".join(group for group in groups if group)


def apply_builtin_formatter(code: str, *, line_length: int = DEFAULT_LINE_LENGTH) -> str:
    """Apply dependency-free formatting for generated Python code."""
    lines = [line.rstrip() for line in code.splitlines()]
    code = "\n".join(lines).strip("\n")
    if not code:
        return ""

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return f"{code}\n"

    import_nodes: list[ast.Import | ast.ImportFrom] = []
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            break
        import_nodes.append(node)

    if not import_nodes:
        return f"{code}\n"

    first_line = import_nodes[0].lineno
    last_line = import_nodes[-1].end_lineno or import_nodes[-1].lineno
    leading = "\n".join(lines[: first_line - 1]).strip("\n")
    body = "\n".join(lines[last_line:]).strip("\n")
    import_block = _build_builtin_import_block(import_nodes, line_length)
    parts = [part for part in (leading, import_block) if part]
    formatted_code = "\n\n".join(parts)
    if body:
        separator = "\n\n\n" if body.startswith(("class ", "def ", "async def ")) else "\n\n"
        formatted_code = f"{formatted_code}{separator}{body}" if formatted_code else body
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
            warn(
                "The default external formatters (black, isort) will become opt-in in a future version. "
                "To keep the current behavior, specify formatters=[Formatter.BLACK, Formatter.ISORT]. "
                "To prepare for dependency-free formatting, use formatters=[Formatter.BUILTIN].",
                FutureWarning,
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

        use_builtin = Formatter.BUILTIN in formatters
        use_black = Formatter.BLACK in formatters
        use_isort = Formatter.ISORT in formatters

        self.builtin_line_length = (
            _get_builtin_line_length(settings_path, builtin_format_line_length) if use_builtin else DEFAULT_LINE_LENGTH
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
        if Formatter.BUILTIN in self.formatters:
            code = self.apply_builtin_formatter(code, line_length=self.builtin_line_length)
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
    def apply_builtin_formatter(code: str, *, line_length: int = DEFAULT_LINE_LENGTH) -> str:
        """Format generated code without external formatter dependencies."""
        return apply_builtin_formatter(code, line_length=line_length)

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
