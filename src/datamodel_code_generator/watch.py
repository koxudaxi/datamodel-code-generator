"""Watch mode for automatic code regeneration."""

from __future__ import annotations

import sys
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


def _watch_filter(dependencies: WatchDependencies, output: Path | None) -> Callable[[Any, str], bool]:
    def includes_dependency(_change: Any, path: str) -> bool:
        resolved_path = Path(path).resolve()
        return not _is_generated_output(resolved_path, output) and dependencies.includes(resolved_path)

    return includes_dependency


def _regenerate(regenerate: Callable[[], Exit]) -> None:
    from datamodel_code_generator.__main__ import Exit  # noqa: PLC0415
    from datamodel_code_generator.model.base import _clear_custom_template_caches  # noqa: PLC0415

    _clear_custom_template_caches()
    if regenerate() == Exit.OK:
        return
    msg = "Generation failed"
    raise RuntimeError(msg)


def _watch_once(
    watchfiles: Any,
    watch_roots: tuple[Path, ...],
    config: Config,
    dependencies: WatchDependencies,
    regenerate: Callable[[], Exit],
) -> bool:
    for changes in watchfiles.watch(
        *watch_roots,
        debounce=int(config.watch_delay * 1000),
        recursive=True,
        watch_filter=_watch_filter(dependencies, dependencies.output),
    ):
        print(f"\nDetected changes: {changes}")  # noqa: T201
        print("Regenerating...")  # noqa: T201
        try:
            _regenerate(regenerate)
            print("Done.")  # noqa: T201
        except Exception as e:  # noqa: BLE001
            print(f"Error: {e}", file=sys.stderr)  # noqa: T201
        return True
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

    try:
        while watch_roots := dependencies.watch_roots():
            if not _watch_once(
                watchfiles,
                watch_roots,
                config,
                dependencies,
                regenerate,
            ):
                return Exit.OK
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")  # noqa: T201

    return Exit.OK
