"""Select deterministic file-level pytest shards for CI."""

from __future__ import annotations

import argparse
from pathlib import Path

EXCLUDED_PARTS = frozenset({"__pycache__", "cli_doc", "data"})
TESTS_ROOT = Path("tests")


def _is_test_file(path: Path) -> bool:
    if EXCLUDED_PARTS & set(path.parts):
        return False
    return path.name.startswith("test_") and path.suffix == ".py"


def _collect_test_files(root: Path = TESTS_ROOT) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if _is_test_file(path))


def _select_shard(paths: list[Path], shard_index: int, shard_total: int) -> list[Path]:
    return [path for offset, path in enumerate(paths) if offset % shard_total == shard_index - 1]


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("shard_index", type=int)
    parser.add_argument("shard_total", type=int)
    args = parser.parse_args()

    match args:
        case argparse.Namespace(shard_index=shard_index, shard_total=shard_total) if 1 <= shard_index <= shard_total:
            if not (paths := _select_shard(_collect_test_files(), shard_index, shard_total)):
                msg = f"No tests selected for shard {shard_index}/{shard_total}"
                raise SystemExit(msg)
            print(*(path.as_posix() for path in paths), sep="\n")
        case _:
            msg = "shard_index must be between 1 and shard_total"
            raise SystemExit(msg)


if __name__ == "__main__":
    _main()
