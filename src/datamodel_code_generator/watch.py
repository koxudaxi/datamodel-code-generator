"""Watch mode for automatic code regeneration."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datamodel_code_generator.__main__ import Config, Exit


def _get_watchfiles() -> Any:
    """Lazily import watchfiles."""
    try:
        import watchfiles  # noqa: PLC0415  # pyright: ignore[reportMissingImports]
    except ImportError as exc:
        msg = "Please run `pip install 'datamodel-code-generator[watch]'` to use watch mode"
        raise Exception(msg) from exc  # noqa: TRY002
    return watchfiles


def watch_and_regenerate(
    config: Config,
    extra_template_data: dict[str, Any] | None,
    aliases: dict[str, str] | None,
    custom_formatters_kwargs: dict[str, str] | None,
) -> Exit:
    """Watch input files and regenerate on changes."""
    from datamodel_code_generator.__main__ import Exit, run_generate_from_config  # noqa: PLC0415

    watchfiles = _get_watchfiles()

    watch_path = Path(config.input) if isinstance(config.input, (str, Path)) else None
    if watch_path is None:
        print("Watch mode requires --input file path", file=sys.stderr)  # noqa: T201
        return Exit.ERROR

    print(f"Watching {watch_path} for changes... (Ctrl+C to stop)")  # noqa: T201

    try:
        for changes in watchfiles.watch(
            watch_path,
            debounce=int(config.watch_delay * 1000),
            recursive=watch_path.is_dir(),
        ):
            print(f"\nDetected changes: {changes}")  # noqa: T201
            print("Regenerating...")  # noqa: T201
            try:
                run_generate_from_config(
                    config=config,
                    input_=config.input,  # pyright: ignore[reportArgumentType]
                    output=config.output,
                    extra_template_data=extra_template_data,
                    aliases=aliases,
                    command_line=None,
                    custom_formatters_kwargs=custom_formatters_kwargs,
                )
                print("Done.")  # noqa: T201
            except Exception as e:  # noqa: BLE001
                print(f"Error: {e}", file=sys.stderr)  # noqa: T201
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")  # noqa: T201

    return Exit.OK
