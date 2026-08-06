"""Collect lexical and resolved local resources used by one watch-mode generation."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from importlib.util import source_from_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from datamodel_code_generator.__main__ import Config


_current_collector: ContextVar[WatchDependencies | None] = ContextVar("watch_dependencies", default=None)
_JSON_CONFIG_FIELDS = frozenset({
    "aliases",
    "base_class_map",
    "custom_formatters_kwargs",
    "default_values",
    "duplicate_name_suffix",
    "enum_field_as_literal_map",
    "extra_template_data",
    "import_overrides",
    "model_name_map",
    "serialization_aliases",
    "type_overrides",
    "validators",
})


def _path_variants(path: Path) -> frozenset[Path]:
    """Keep lexical and resolved locations so symlink retargeting remains observable."""
    lexical_path = Path(os.path.abspath(path.expanduser()))  # noqa: PTH100
    try:
        parent_resolved_path = lexical_path.parent.resolve(strict=False) / lexical_path.name
        resolved_path = lexical_path.resolve(strict=False)
    except (OSError, ValueError):
        return frozenset({lexical_path})
    return frozenset({lexical_path, parent_resolved_path, resolved_path})


def _resolved_path(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser())).resolve(strict=False)  # noqa: PTH100


def _existing_file(value: object) -> Path | None:
    if not isinstance(value, (str, Path)):
        return None
    try:
        path = Path(os.path.abspath(Path(value).expanduser()))  # noqa: PTH100
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None


def _configured_path(config_values: Mapping[str, Any], field_name: str, fallback: str | Path | None) -> Path | None:
    value = config_values.get(field_name, fallback)
    return Path(value) if isinstance(value, (str, Path)) else fallback


def _logical_working_directory() -> Path:
    working_directory = Path.cwd()
    logical_working_directory = Path(os.environ.get("PWD", working_directory)).expanduser()
    try:
        return logical_working_directory if logical_working_directory.samefile(working_directory) else working_directory
    except OSError:
        return working_directory


@dataclass(slots=True)
class WatchDependencies:
    """Path-only dependency state for one persistent watch session."""

    _static_files: set[Path] = field(default_factory=set)
    _static_directories: set[Path] = field(default_factory=set)
    _static_symlink_parents: set[Path] = field(default_factory=set)
    _generation_files: set[Path] = field(default_factory=set)
    _generation_symlink_parents: set[Path] = field(default_factory=set)
    _output: Path | None = None

    def configure(
        self,
        config: Config,
        *,
        config_values: Mapping[str, Any],
    ) -> None:
        """Replace the static dependencies resolved from the current CLI config."""
        self._static_files.clear()
        self._static_directories.clear()
        self._static_symlink_parents.clear()
        self._output = _resolved_path(config.output) if config.output is not None else None

        input_path = _configured_path(config_values, "input", config.input)
        if input_path is not None:
            self.add_directory(input_path) if input_path.is_dir() else self.add_file(input_path)
        self.add_file(_nearest_pyproject_toml(_logical_working_directory()))
        self.add_file(_configured_path(config_values, "custom_file_header_path", config.custom_file_header_path))
        self.add_directory(_configured_path(config_values, "custom_template_dir", config.custom_template_dir))
        self.add_directory(_configured_path(config_values, "http_local_ref_path", config.http_local_ref_path))
        if (class_name_generator := getattr(config, "custom_class_name_generator", None)) is not None and (
            module_path := record_module_dependency(sys.modules.get(class_name_generator.__module__))
        ) is not None:
            self.add_file(module_path)
        for field_name in _JSON_CONFIG_FIELDS:
            self.add_file(_existing_file(config_values.get(field_name)))

    @contextmanager
    def generation(self) -> Iterator[None]:
        """Collect paths for one generation and retain the prior graph on failure."""
        previous_files = self._generation_files
        previous_symlink_parents = self._generation_symlink_parents
        self._generation_files = set()
        self._generation_symlink_parents = set()
        token = _current_collector.set(self)
        try:
            yield
        except BaseException:
            self._generation_files.update(previous_files)
            self._generation_symlink_parents.update(previous_symlink_parents)
            raise
        finally:
            _current_collector.reset(token)

    def add_file(self, path: Path | None) -> None:
        """Add one static local file dependency."""
        if path is None:
            return
        self._static_files.update(_path_variants(path))
        if path.is_symlink():
            self._static_symlink_parents.update(_path_variants(path.parent))

    def add_directory(self, path: Path | None) -> None:
        """Add one recursively watched local directory dependency."""
        if path is None:
            return
        self._static_directories.update(_path_variants(path))
        if path.is_symlink():
            self._static_symlink_parents.update(_path_variants(path.parent))

    def record_file(self, path: Path) -> None:
        """Add one file used by the active generation."""
        self._generation_files.update(_path_variants(path))
        if path.is_symlink():
            self._generation_symlink_parents.update(_path_variants(path.parent))

    @property
    def files(self) -> frozenset[Path]:
        """Return all exact file dependencies."""
        return frozenset((*self._static_files, *self._generation_files))

    @property
    def directories(self) -> frozenset[Path]:
        """Return recursively watched dependency directories."""
        return frozenset(self._static_directories)

    @property
    def output(self) -> Path | None:
        """Return the current generated output path, if generation writes files."""
        return self._output

    def watch_roots(self) -> tuple[Path, ...]:
        """Return existing directories to give to ``watchfiles.watch``."""
        roots: set[Path] = {_nearest_existing_directory(path.parent) for path in self.files}
        roots.update(_nearest_existing_directory(directory) for directory in self.directories)
        return tuple(sorted((path for path in roots if path.is_dir()), key=lambda path: path.as_posix()))

    def includes(self, path: Path) -> bool:
        """Return whether a filesystem event belongs to this dependency graph."""
        path_variants = _path_variants(path)
        if path_variants & (self.files | self._static_symlink_parents | self._generation_symlink_parents):
            return True
        return any(
            path_variant.is_relative_to(directory) for path_variant in path_variants for directory in self.directories
        )


def record_local_dependency(path: Path) -> None:
    """Record a local file when dependency collection is active."""
    if (collector := _current_collector.get()) is not None:
        collector.record_file(path)


def record_module_dependency(module: object) -> Path | None:
    """Record an imported module's source file when generation collection is active."""
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        return None
    module_path = Path(module_file)
    if module_path.suffix == ".pyc":
        with suppress(ValueError):
            module_path = Path(source_from_cache(str(module_path)))
    record_local_dependency(module_path)
    return module_path


def _nearest_pyproject_toml(path: Path) -> Path | None:
    for parent in (path, *path.parents):
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def _nearest_existing_directory(path: Path) -> Path:
    while not path.is_dir():
        path = path.parent
    return path
