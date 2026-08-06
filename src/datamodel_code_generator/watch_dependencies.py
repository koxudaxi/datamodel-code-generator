"""Collect the local resources used by one watch-mode generation.

The collector stores only resolved paths.  It is intentionally independent from
``watchfiles`` so ordinary generation never imports the optional watch extra.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
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


def _resolved_path(path: Path) -> Path:
    return path.expanduser().resolve()


def _existing_file(value: object) -> Path | None:
    if not isinstance(value, (str, Path)):
        return None
    try:
        path = _resolved_path(Path(value))
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None


@dataclass(slots=True)
class WatchDependencies:
    """Path-only dependency state for one persistent watch session."""

    _static_files: set[Path] = field(default_factory=set)
    _static_directories: set[Path] = field(default_factory=set)
    _generation_files: set[Path] = field(default_factory=set)
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
        self._output = _resolved_path(config.output) if config.output is not None else None

        if isinstance(config.input, Path):
            self.add_directory(config.input) if config.input.is_dir() else self.add_file(config.input)
        self.add_file(_nearest_pyproject_toml(Path.cwd()))
        self.add_file(config.custom_file_header_path)
        self.add_directory(config.custom_template_dir)
        self.add_directory(config.http_local_ref_path)
        for field_name in _JSON_CONFIG_FIELDS:
            self.add_file(_existing_file(config_values.get(field_name)))

    @contextmanager
    def generation(self) -> Iterator[None]:
        """Collect paths for one generation and retain the prior graph on failure."""
        previous_files = self._generation_files
        self._generation_files = set()
        token = _current_collector.set(self)
        try:
            yield
        except BaseException:
            self._generation_files.update(previous_files)
            raise
        finally:
            _current_collector.reset(token)

    def add_file(self, path: Path | None) -> None:
        """Add one static local file dependency."""
        if path is None:
            return
        self._static_files.add(_resolved_path(path))

    def add_directory(self, path: Path | None) -> None:
        """Add one recursively watched local directory dependency."""
        if path is None:
            return
        self._static_directories.add(_resolved_path(path))

    def record_file(self, path: Path) -> None:
        """Add one file used by the active generation."""
        self._generation_files.add(_resolved_path(path))

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
        roots: set[Path] = {path.parent for path in self.files}
        roots.update(path for path in self.directories if path.is_dir())
        return tuple(sorted((path for path in roots if path.is_dir()), key=lambda path: path.as_posix()))

    def includes(self, path: Path) -> bool:
        """Return whether a filesystem event belongs to this dependency graph."""
        resolved_path = _resolved_path(path)
        if resolved_path in self.files:
            return True
        return any(resolved_path.is_relative_to(directory) for directory in self.directories)


def record_local_dependency(path: Path) -> None:
    """Record a local file when dependency collection is active."""
    if (collector := _current_collector.get()) is not None:
        collector.record_file(path)


def _nearest_pyproject_toml(path: Path) -> Path | None:
    for parent in (path, *path.parents):
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None
