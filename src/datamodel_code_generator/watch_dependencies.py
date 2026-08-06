"""Collect lexical and resolved local resources used by one watch-mode generation."""

from __future__ import annotations

import os
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass, field
from importlib.util import source_from_cache
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from datamodel_code_generator.__main__ import Config

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


@dataclass(slots=True, weakref_slot=True)
class _CollectedGeneration:
    """Private graph additions that become visible only after a generation ends."""

    owner: WatchDependencies
    files: set[Path] = field(default_factory=set)
    symlink_events: set[Path] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class _DependencySnapshot:
    """An immutable dependency graph safely shared with the watcher thread."""

    files: frozenset[Path]
    directories: frozenset[Path]
    event_paths: frozenset[Path]
    output: Path | None
    outputs: frozenset[Path]
    watch_roots: tuple[Path, ...]


@dataclass(slots=True)
class _StaticDependencies:
    """One bounded static candidate awaiting generation publication."""

    files: set[Path] = field(default_factory=set)
    directories: set[Path] = field(default_factory=set)
    symlink_events: set[Path] = field(default_factory=set)
    output: Path | None = None


_current_collector: ContextVar[_CollectedGeneration | None] = ContextVar("watch_dependencies", default=None)


def _lexical_path(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))  # noqa: PTH100


def _path_variants(path: Path) -> frozenset[Path]:
    """Keep lexical and resolved locations so symlink retargeting remains observable."""
    lexical_path = _lexical_path(path)
    try:
        parent_resolved_path = lexical_path.parent.resolve(strict=False) / lexical_path.name
        resolved_path = lexical_path.resolve(strict=False)
    except (OSError, ValueError):
        return frozenset({lexical_path})
    return frozenset({lexical_path, parent_resolved_path, resolved_path})


def _symlink_event_paths(path: Path) -> frozenset[Path]:
    """Return symlink ancestors and parents whose events can repoint a lexical path."""
    event_paths: set[Path] = set()
    current = _lexical_path(path)
    while current != current.parent:
        try:
            if current.is_symlink():
                parent = current.parent
                if parent != parent.parent:
                    event_paths.update(_path_variants(current))
                    event_paths.update(_path_variants(parent))
        except OSError:
            break
        current = current.parent
    return frozenset(event_paths)


def _resolved_path(path: Path) -> Path:
    return _lexical_path(path).resolve(strict=False)


def _configured_path(config_values: Mapping[str, Any], field_name: str, fallback: str | Path | None) -> Path | None:
    value = config_values.get(field_name, fallback)
    if isinstance(value, (str, Path)):
        return Path(value)
    return Path(fallback) if isinstance(fallback, str) else fallback


def _logical_working_directory() -> Path:
    working_directory = Path.cwd()
    logical_working_directory = Path(os.environ.get("PWD", working_directory)).expanduser()
    try:
        return logical_working_directory if logical_working_directory.samefile(working_directory) else working_directory
    except OSError:
        return working_directory


def _nearest_existing_directory(path: Path) -> Path:
    while not path.is_dir():
        path = path.parent
    return path


@dataclass(slots=True, weakref_slot=True)
class WatchDependencies:
    """Path-only dependency state for one persistent watch session."""

    _static_files: set[Path] = field(default_factory=set)
    _static_directories: set[Path] = field(default_factory=set)
    _static_symlink_events: set[Path] = field(default_factory=set)
    _generation_files: set[Path] = field(default_factory=set)
    _generation_symlink_events: set[Path] = field(default_factory=set)
    _output: Path | None = None
    _pending_static: _StaticDependencies | None = None
    _failed_static: _StaticDependencies | None = None
    _failed_generation_files: set[Path] = field(default_factory=set)
    _failed_generation_symlink_events: set[Path] = field(default_factory=set)
    _lock: RLock = field(default_factory=RLock)
    _snapshot: _DependencySnapshot = field(init=False)

    def __post_init__(self) -> None:
        """Publish the initial empty immutable graph."""
        self._snapshot = self._create_snapshot()

    def _create_snapshot(self) -> _DependencySnapshot:
        static_files = self._static_files.copy()
        static_directories = self._static_directories.copy()
        static_symlink_events = self._static_symlink_events.copy()
        candidate = self._pending_static or self._failed_static
        if candidate is not None:
            static_files |= candidate.files
            static_directories |= candidate.directories
            static_symlink_events |= candidate.symlink_events
        failed_generation_files = self._failed_generation_files if self._pending_static is None else set()
        failed_generation_symlink_events = (
            self._failed_generation_symlink_events if self._pending_static is None else set()
        )
        files = frozenset(static_files | self._generation_files | failed_generation_files)
        directories = frozenset(static_directories)
        event_paths = frozenset(
            files | static_symlink_events | self._generation_symlink_events | failed_generation_symlink_events
        )
        roots = {_nearest_existing_directory(path.parent) for path in files}
        roots.update(_nearest_existing_directory(path) for path in directories)
        roots.update(_nearest_existing_directory(path) for path in event_paths)
        watch_roots = tuple(sorted((path for path in roots if path.is_dir()), key=lambda path: path.as_posix()))
        outputs = frozenset(output for output in (self._output, candidate.output if candidate else None) if output)
        return _DependencySnapshot(files, directories, event_paths, self._output, outputs, watch_roots)

    def _publish(self) -> None:
        self._snapshot = self._create_snapshot()

    @staticmethod
    def _add_path(path: Path, paths: set[Path], symlink_events: set[Path]) -> None:
        try:
            paths.update(_path_variants(path))
            symlink_events.update(_symlink_event_paths(path))
        except (OSError, ValueError):
            return

    def configure(
        self,
        config: Config,
        *,
        config_values: Mapping[str, Any],
    ) -> None:
        """Stage a static graph without exposing a generation-sized membership gap."""
        files: set[Path] = set()
        directories: set[Path] = set()
        symlink_events: set[Path] = set()

        def add_file(path: Path | None) -> None:
            if path is not None:
                self._add_path(path, files, symlink_events)

        def add_directory(path: Path | None) -> None:
            if path is not None:
                self._add_path(path, directories, symlink_events)

        input_path = _configured_path(config_values, "input", config.input)
        if input_path is not None:
            (add_directory if input_path.is_dir() else add_file)(input_path)
        add_file(_nearest_pyproject_toml(_logical_working_directory()))
        add_file(_configured_path(config_values, "custom_file_header_path", config.custom_file_header_path))
        add_directory(_configured_path(config_values, "custom_template_dir", config.custom_template_dir))
        add_directory(_configured_path(config_values, "http_local_ref_path", config.http_local_ref_path))
        for field_name in _JSON_CONFIG_FIELDS:
            value = config_values.get(field_name)
            add_file(Path(value) if isinstance(value, (str, Path)) else None)

        candidate = _StaticDependencies(
            files=files,
            directories=directories,
            symlink_events=symlink_events,
            output=_resolved_path(config.output) if config.output is not None else None,
        )
        with self._lock:
            self._pending_static = candidate
            self._publish()

    def stage_raw_config(self, config_values: Mapping[str, Any]) -> None:
        """Stage lexical raw paths before typed config validation can fail."""
        candidate = _StaticDependencies()

        def add_file(value: object) -> None:
            if isinstance(value, (str, Path)):
                self._add_path(Path(value), candidate.files, candidate.symlink_events)

        def add_directory(value: object) -> None:
            if isinstance(value, (str, Path)):
                self._add_path(Path(value), candidate.directories, candidate.symlink_events)

        input_value = config_values.get("input")
        if isinstance(input_value, (str, Path)):
            (add_directory if Path(input_value).is_dir() else add_file)(input_value)
        add_file(config_values.get("custom_file_header_path"))
        add_directory(config_values.get("custom_template_dir"))
        add_directory(config_values.get("http_local_ref_path"))
        for field_name in _JSON_CONFIG_FIELDS:
            add_file(config_values.get(field_name))
        if isinstance(output := config_values.get("output"), (str, Path)):
            with suppress(OSError, ValueError):
                candidate.output = _resolved_path(Path(output))
        with self._lock:
            self._pending_static = candidate
            self._publish()

    @contextmanager
    def generation(self) -> Iterator[None]:
        """Collect one generation privately, publishing a complete graph only at its end."""
        collected = _CollectedGeneration(self)
        token = _current_collector.set(collected)
        try:
            yield
        except BaseException:
            with self._lock:
                self._failed_static = self._pending_static
                self._pending_static = None
                self._failed_generation_files = collected.files
                self._failed_generation_symlink_events = collected.symlink_events
                self._publish()
            raise
        else:
            with self._lock:
                if self._pending_static is not None:
                    self._static_files = self._pending_static.files
                    self._static_directories = self._pending_static.directories
                    self._static_symlink_events = self._pending_static.symlink_events
                    self._output = self._pending_static.output
                    self._pending_static = None
                self._generation_files = collected.files
                self._generation_symlink_events = collected.symlink_events
                self._failed_static = None
                self._failed_generation_files.clear()
                self._failed_generation_symlink_events.clear()
                self._publish()
        finally:
            _current_collector.reset(token)

    def add_file(self, path: Path | None) -> None:
        """Add one static local file dependency."""
        if path is None:
            return
        with self._lock:
            self._add_path(path, self._static_files, self._static_symlink_events)
            self._publish()

    def add_directory(self, path: Path | None) -> None:
        """Add one recursively watched local directory dependency."""
        if path is None:
            return
        with self._lock:
            self._add_path(path, self._static_directories, self._static_symlink_events)
            self._publish()

    def record_file(self, path: Path) -> None:
        """Add a generated dependency to the private collector or current snapshot."""
        if (collector := _current_collector.get()) is not None and collector.owner is self:
            self._add_path(path, collector.files, collector.symlink_events)
            return
        with self._lock:
            self._add_path(path, self._generation_files, self._generation_symlink_events)
            self._publish()

    @property
    def files(self) -> frozenset[Path]:
        """All exact file dependencies from one immutable snapshot."""
        return self._snapshot.files

    @property
    def directories(self) -> frozenset[Path]:
        """Recursively watched dependency directories from one snapshot."""
        return self._snapshot.directories

    @property
    def output(self) -> Path | None:
        """The current generated output path, if generation writes files."""
        return self._snapshot.output

    @property
    def outputs(self) -> frozenset[Path]:
        """Every output path excluded from watch events."""
        return self._snapshot.outputs

    def watch_roots(self) -> tuple[Path, ...]:
        """Return existing roots cached when the dependency graph was published."""
        return self._snapshot.watch_roots

    @staticmethod
    def _includes_snapshot(snapshot: _DependencySnapshot, path_variants: frozenset[Path]) -> bool:
        if path_variants & snapshot.event_paths:
            return True
        return any(
            path_variant.is_relative_to(directory)
            for path_variant in path_variants
            for directory in snapshot.directories
        )

    def includes(self, path: Path) -> bool:
        """Return whether an event belongs to the immutable current dependency graph."""
        return self._includes_snapshot(self._snapshot, _path_variants(path))

    def accepts_event(self, path: Path) -> bool:
        """Return whether one event is both outside outputs and inside this snapshot."""
        snapshot = self._snapshot
        try:
            resolved_path = path.resolve(strict=False)
        except (OSError, ValueError):
            resolved_path = path
        if any(
            resolved_path == output or (not output.suffix and resolved_path.is_relative_to(output))
            for output in snapshot.outputs
        ):
            return False
        return self._includes_snapshot(snapshot, _path_variants(path))


def collector_is_active() -> bool:
    """Return whether watch dependency collection is active without importing watch mode."""
    return _current_collector.get() is not None


def collector_identity() -> object | None:
    """Return the identity of the active generation collector."""
    return _current_collector.get()


def record_local_dependency(path: Path) -> None:
    """Record a local file when dependency collection is active."""
    if (collector := _current_collector.get()) is not None:
        collector.owner.record_file(path)


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
