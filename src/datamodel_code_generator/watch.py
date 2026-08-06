"""Watch mode for automatic code regeneration."""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from datamodel_code_generator.__main__ import Config, Exit
    from datamodel_code_generator.watch_dependencies import WatchDependencies


def _get_watchfiles() -> Any:
    """Lazily import watchfiles."""
    try:
        import watchfiles  # noqa: PLC0415
    except ImportError as exc:
        msg = "Please run `pip install 'datamodel-code-generator[watch]'` to use watch mode"
        raise Exception(msg) from exc  # noqa: TRY002
    return watchfiles


def _is_generated_output(path: Path, output: Path | None) -> bool:
    if output is None:
        return False
    resolved_output = output.resolve()
    if output.suffix:
        return path == resolved_output
    return path == resolved_output or path.is_relative_to(resolved_output)


def _watch_filter(dependencies: WatchDependencies) -> Callable[[Any, str], bool]:
    def includes_dependency(_change: Any, path: str) -> bool:
        event_path = Path(path)
        return not _is_generated_output(event_path.resolve(), dependencies.output) and dependencies.includes(event_path)

    return includes_dependency


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


def _watch_once(
    context: _WatchContext,
    watch_roots: tuple[Path, ...],
    *,
    catch_up: bool,
) -> tuple[bool, bool]:
    stop_event = threading.Event()
    condition = threading.Condition()
    pending_changes: set[tuple[Any, str]] = set()
    watcher_error: BaseException | None = None
    watcher_exhausted = False

    def watch_changes() -> None:
        nonlocal watcher_error, watcher_exhausted

        try:
            for changes in context.watchfiles.watch(
                *watch_roots,
                debounce=int(context.config.watch_delay * 1000),
                poll_delay_ms=max(1, min(300, int(context.config.watch_delay * 1000))),
                recursive=True,
                stop_event=stop_event,
                watch_filter=_watch_filter(context.dependencies),
            ):
                with condition:
                    pending_changes.update(changes)
                    condition.notify()
        except KeyboardInterrupt as exc:
            with condition:
                watcher_error = exc
                condition.notify()
        except Exception as exc:  # noqa: BLE001
            with condition:
                watcher_error = exc
                condition.notify()
        finally:
            with condition:
                watcher_exhausted = True
                condition.notify()

    watcher = threading.Thread(target=watch_changes, name="datamodel-codegen-watch", daemon=True)
    watcher.start()
    restart = False
    try:
        if catch_up:
            _regenerate_after_change(None, context.regenerate)
            if context.dependencies.watch_roots() != watch_roots:
                restart = True

        while not restart:
            with condition:
                condition.wait_for(lambda: pending_changes or watcher_error is not None or watcher_exhausted)
                if watcher_error is not None:
                    raise watcher_error
                if not pending_changes:
                    break
                changes = pending_changes.copy()
                pending_changes.clear()
            _regenerate_after_change(changes, context.regenerate)
            if context.dependencies.watch_roots() != watch_roots:
                restart = True
    finally:
        stop_event.set()
        watcher.join()
    with condition:
        return restart, bool(pending_changes)


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
            restart, catch_up = _watch_once(
                watch_context,
                watch_roots,
                catch_up=catch_up,
            )
            if not restart:
                return Exit.OK
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")  # noqa: T201

    return Exit.OK
