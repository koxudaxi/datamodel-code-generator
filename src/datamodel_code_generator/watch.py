"""Watch mode for automatic code regeneration."""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from datamodel_code_generator.__main__ import Config, Exit
    from datamodel_code_generator.watch_dependencies import WatchDependencies

_PENDING_CHANGE_SAMPLE_LIMIT = 32


def _get_watchfiles() -> Any:
    """Lazily import watchfiles."""
    try:
        import watchfiles  # noqa: PLC0415
    except ImportError as exc:
        msg = "Please run `pip install 'datamodel-code-generator[watch]'` to use watch mode"
        raise Exception(msg) from exc  # noqa: TRY002
    return watchfiles


def _watch_filter(
    dependencies: WatchDependencies, *, accept_directory_events: bool = False
) -> Callable[[Any, str], bool]:
    def includes_dependency(_change: Any, path: str) -> bool:
        return dependencies.accepts_event(Path(path), accept_directory_events=accept_directory_events)

    return includes_dependency


def _force_polling(watch_roots: tuple[Path, ...]) -> bool:
    """Avoid the macOS native backend's multi-root atomic-replace blind spot."""
    return sys.platform == "darwin" and len(watch_roots) > 1


def _regenerate(regenerate: Callable[[], Exit]) -> None:
    from datamodel_code_generator.__main__ import Exit  # noqa: PLC0415
    from datamodel_code_generator.model.base import _clear_custom_template_caches  # noqa: PLC0415

    _clear_custom_template_caches()
    if regenerate() == Exit.OK:
        return
    msg = "Generation failed"
    raise RuntimeError(msg)


@dataclass(frozen=True)
class _WatchContext:
    watchfiles: Any
    config: Config
    dependencies: WatchDependencies
    regenerate: Callable[[], Exit]


@dataclass(slots=True)
class _WatcherState:
    """Small bounded hand-off from the watch thread to the regeneration loop."""

    pending_change_sample: set[tuple[Any, str]]
    has_pending_changes: bool = False
    error: BaseException | None = None
    exhausted: bool = False

    def add_changes(self, changes: set[tuple[Any, str]]) -> None:
        """Keep a diagnostic sample without retaining an unbounded event stream."""
        self.has_pending_changes = True
        remaining = _PENDING_CHANGE_SAMPLE_LIMIT - len(self.pending_change_sample)
        if remaining > 0:
            self.pending_change_sample.update(islice(changes, remaining))

    def take_changes(self) -> set[tuple[Any, str]]:
        """Drain the diagnostic sample while retaining the change notification."""
        changes = self.pending_change_sample.copy()
        self.pending_change_sample.clear()
        self.has_pending_changes = False
        return changes

    @property
    def is_ready(self) -> bool:
        """Whether the main watch loop has work, an error, or completion to process."""
        return self.has_pending_changes or self.error is not None or self.exhausted


def _regenerate_after_change(changes: set[tuple[Any, str]] | None, regenerate: Callable[[], Exit]) -> None:
    if changes is None:
        print("\nDetected changes while restarting the watcher.")  # noqa: T201
    else:
        print(f"\nDetected changes: {changes}")  # noqa: T201
    print("Regenerating...")  # noqa: T201
    try:
        _regenerate(regenerate)
        print("Done.")  # noqa: T201
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)  # noqa: T201


def _watch_changes(
    context: _WatchContext,
    watch_roots: tuple[Path, ...],
    stop_event: threading.Event,
    condition: threading.Condition,
    state: _WatcherState,
) -> None:
    """Publish filesystem changes from the persistent background watch stream."""
    force_polling = _force_polling(watch_roots)
    try:
        for changes in context.watchfiles.watch(
            *watch_roots,
            debounce=int(context.config.watch_delay * 1000),
            force_polling=force_polling,
            poll_delay_ms=max(1, min(300, int(context.config.watch_delay * 1000))),
            recursive=True,
            stop_event=stop_event,
            watch_filter=_watch_filter(context.dependencies, accept_directory_events=force_polling),
        ):
            with condition:
                state.add_changes(changes)
                condition.notify()
    except (KeyboardInterrupt, Exception) as exc:  # noqa: BLE001
        with condition:
            state.error = exc
            condition.notify()
    finally:
        with condition:
            state.exhausted = True
            condition.notify()


def _wait_for_changes(condition: threading.Condition, state: _WatcherState) -> set[tuple[Any, str]] | None:
    """Block for a watched change, raising a background watcher failure when present."""
    with condition:
        while not state.is_ready:
            condition.wait()
        if state.error is not None:
            raise state.error
        if not state.has_pending_changes:
            return None
        return state.take_changes()


def _watch_once(
    context: _WatchContext,
    watch_roots: tuple[Path, ...],
    *,
    catch_up: bool,
) -> bool:
    stop_event = threading.Event()
    condition = threading.Condition()
    state = _WatcherState(set())
    watcher = threading.Thread(
        target=_watch_changes,
        args=(context, watch_roots, stop_event, condition, state),
        name="datamodel-codegen-watch",
        daemon=True,
    )
    watcher.start()
    try:
        if catch_up:
            _regenerate_after_change(None, context.regenerate)
            if context.dependencies.watch_roots() != watch_roots:
                return True

        while (changes := _wait_for_changes(condition, state)) is not None:
            _regenerate_after_change(changes, context.regenerate)
            if context.dependencies.watch_roots() != watch_roots:
                return True
    finally:
        stop_event.set()
        watcher.join()
    return False


def watch_and_regenerate(
    config: Config,
    *,
    dependencies: WatchDependencies | None = None,
    regenerate: Callable[[], Exit],
) -> Exit:
    """Watch every local generation dependency and fully regenerate on changes."""
    from datamodel_code_generator.__main__ import Exit  # noqa: PLC0415
    from datamodel_code_generator.watch_dependencies import WatchDependencies  # noqa: PLC0415

    watchfiles = _get_watchfiles()

    watch_path = Path(config.input) if isinstance(config.input, (str, Path)) else None
    if watch_path is None:
        print("Watch mode requires --input file path", file=sys.stderr)  # noqa: T201
        return Exit.ERROR

    if dependencies is None:
        dependencies = WatchDependencies()
        dependencies.configure(config, config_values={})

    print(f"Watching {watch_path} for changes... (Ctrl+C to stop)")  # noqa: T201

    watch_context = _WatchContext(watchfiles, config, dependencies, regenerate)
    catch_up = False
    try:
        while watch_roots := dependencies.watch_roots():
            restart = _watch_once(
                watch_context,
                watch_roots,
                catch_up=catch_up,
            )
            if not restart:
                return Exit.OK
            catch_up = True
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")  # noqa: T201

    return Exit.OK
