"""Select deterministic pytest shards for CI."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

EXCLUDED_PARTS = frozenset({"__pycache__", "cli_doc", "data"})
PAYLOAD_VALIDATION_FILE = "tests/main/test_payload_validation.py"
SPLIT_NODE_FILES = frozenset({PAYLOAD_VALIDATION_FILE})
RECIPE_VERSION = 1
TESTS_ROOT = Path("tests")
WEIGHT_OVERRIDES = {
    "tests/main/test_main_general.py": 300_000,
    "tests/test_main_kr.py": 250_000,
    "tests/main/jsonschema/test_main_jsonschema.py": 200_000,
    "tests/main/openapi/test_main_openapi.py": 200_000,
    "tests/main/xmlschema/test_main_xmlschema.py": 180_000,
    "tests/parser/test_jsonschema.py": 180_000,
    "tests/parser/test_openapi.py": 180_000,
}
SPLIT_NODE_WEIGHT_OVERRIDES = {
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_pydantic_v2_model_accepts_schema_derived_payloads": 500_000,
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_pydantic_v2_model_dumps_schema_valid_payloads": 500_000,
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_pydantic_v2_model_rejects_schema_invalid_payloads": 260_000,
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_payload_backend_accepts_representative_schema_payloads": 80_000,
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_payload_backend_rejects_representative_schema_invalid_payloads": 80_000,
}


def _as_posix(path: Path) -> str:
    return path.as_posix()


def _is_test_file(path: Path) -> bool:
    if EXCLUDED_PARTS & set(path.parts):
        return False
    return path.name.startswith("test_") and path.suffix == ".py" and path.as_posix() not in SPLIT_NODE_FILES


def _collect_split_nodeids(path: Path) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=_as_posix(path))
    nodeids: list[str] = []

    for node in module.body:
        match node:
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name) if name.startswith("test_"):
                nodeids.append(f"{_as_posix(path)}::{name}")
            case ast.ClassDef(name=class_name) if class_name.startswith("Test"):
                for child in node.body:
                    match child:
                        case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name) if name.startswith("test_"):
                            nodeids.append(f"{_as_posix(path)}::{class_name}::{name}")

    return sorted(nodeids)


def _collect_test_items(root: Path = TESTS_ROOT) -> list[str]:
    file_items = (path.as_posix() for path in root.rglob("*.py") if _is_test_file(path))
    split_node_items = (
        nodeid for split_file in sorted(SPLIT_NODE_FILES) for nodeid in _collect_split_nodeids(Path(split_file))
    )
    return sorted([*file_items, *split_node_items])


def _item_weight(item: str) -> int:
    path = Path(item.partition("::")[0])
    if "::" in item:
        return SPLIT_NODE_WEIGHT_OVERRIDES.get(item, 10_000)
    return WEIGHT_OVERRIDES.get(item, path.stat().st_size)


def _build_recipe_items() -> list[dict[str, int | str]]:
    return [{"nodeid": item, "weight": _item_weight(item)} for item in _collect_test_items()]


def _validate_recipe_items(items: Any) -> list[dict[str, int | str]]:
    if not isinstance(items, list):
        msg = "recipe items must be a list"
        raise SystemExit(msg)

    validated: list[dict[str, int | str]] = []
    for item in items:
        match item:
            case {"nodeid": str(nodeid), "weight": int(weight)} if not isinstance(weight, bool):
                validated.append({"nodeid": nodeid, "weight": weight})
            case _:
                msg = f"invalid recipe item: {item!r}"
                raise SystemExit(msg)
    return validated


def _load_recipe_items(path: Path) -> list[dict[str, int | str]]:
    recipe = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(recipe, dict) or recipe.get("version") != RECIPE_VERSION or "items" not in recipe:
        msg = f"unsupported shard recipe: {recipe!r}"
        raise SystemExit(msg)
    return _validate_recipe_items(recipe["items"])


def _write_recipe(path: Path, items: list[dict[str, int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": RECIPE_VERSION, "items": items}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _select_shard(items: list[dict[str, int | str]], shard_index: int, shard_total: int) -> list[str]:
    shards: list[list[str]] = [[] for _ in range(shard_total)]
    shard_weights = [0] * shard_total
    weighted_items = sorted(
        ((int(item["weight"]), str(item["nodeid"])) for item in items),
        key=lambda item: (-item[0], item[1]),
    )

    for weight, item in weighted_items:
        target = min(
            range(shard_total),
            key=lambda index: (shard_weights[index], len(shards[index]), index),
        )
        shards[target].append(item)
        shard_weights[target] += weight

    return sorted(shards[shard_index - 1])


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("shard_index", type=int, nargs="?")
    parser.add_argument("shard_total", type=int, nargs="?")
    parser.add_argument("--recipe", type=Path)
    parser.add_argument("--write-recipe", type=Path)
    args = parser.parse_args()

    items = _load_recipe_items(args.recipe) if args.recipe else _build_recipe_items()
    if args.write_recipe:
        _write_recipe(args.write_recipe, items)
        if args.shard_index is None and args.shard_total is None:
            return

    if args.shard_index is None or args.shard_total is None:
        parser.error("shard_index and shard_total are required unless only --write-recipe is used")

    shard_index = args.shard_index
    shard_total = args.shard_total

    match 1 <= shard_index <= shard_total:
        case False:
            msg = "shard_index must be between 1 and shard_total"
            raise SystemExit(msg)
        case True:
            if selected := _select_shard(items, shard_index, shard_total):
                print(*selected, sep="\n")
                return

    msg = f"No tests selected for shard {shard_index}/{shard_total}"
    raise SystemExit(msg)


if __name__ == "__main__":
    _main()
