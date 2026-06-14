"""Select deterministic file-level pytest shards for CI."""

from __future__ import annotations

import argparse
from pathlib import Path

EXCLUDED_PARTS = frozenset({"__pycache__", "cli_doc", "data"})
TESTS_ROOT = Path("tests")
WEIGHT_OVERRIDES = {
    "tests/main/test_payload_validation.py": 1_000_000,
    "tests/main/test_main_general.py": 300_000,
    "tests/test_main_kr.py": 250_000,
    "tests/main/jsonschema/test_main_jsonschema.py": 200_000,
    "tests/main/openapi/test_main_openapi.py": 200_000,
    "tests/main/xmlschema/test_main_xmlschema.py": 180_000,
    "tests/parser/test_jsonschema.py": 180_000,
    "tests/parser/test_openapi.py": 180_000,
}


def _is_test_file(path: Path) -> bool:
    if EXCLUDED_PARTS & set(path.parts):
        return False
    return path.name.startswith("test_") and path.suffix == ".py"


def _collect_test_files(root: Path = TESTS_ROOT) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if _is_test_file(path))


def _path_weight(path: Path) -> int:
    return WEIGHT_OVERRIDES.get(path.as_posix(), path.stat().st_size)


def _select_shard(paths: list[Path], shard_index: int, shard_total: int) -> list[Path]:
    shards: list[list[Path]] = [[] for _ in range(shard_total)]
    shard_weights = [0] * shard_total
    weighted_paths = sorted(
        ((_path_weight(path), path) for path in paths),
        key=lambda item: (-item[0], item[1].as_posix()),
    )

    for weight, path in weighted_paths:
        target = min(
            range(shard_total),
            key=lambda index: (shard_weights[index], len(shards[index]), index),
        )
        shards[target].append(path)
        shard_weights[target] += weight

    return sorted(shards[shard_index - 1])


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("shard_index", type=int)
    parser.add_argument("shard_total", type=int)
    args = parser.parse_args()
    shard_index = args.shard_index
    shard_total = args.shard_total

    match 1 <= shard_index <= shard_total:
        case False:
            msg = "shard_index must be between 1 and shard_total"
            raise SystemExit(msg)
        case True:
            if paths := _select_shard(_collect_test_files(), shard_index, shard_total):
                print(*(path.as_posix() for path in paths), sep="\n")
                return

    msg = f"No tests selected for shard {shard_index}/{shard_total}"
    raise SystemExit(msg)


if __name__ == "__main__":
    _main()
