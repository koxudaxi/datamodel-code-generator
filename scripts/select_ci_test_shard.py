"""Select deterministic pytest shards for CI."""

from __future__ import annotations

import argparse
from pathlib import Path

EXCLUDED_PARTS = frozenset({"__pycache__", "cli_doc", "data"})
PAYLOAD_VALIDATION_FILE = "tests/main/test_payload_validation.py"
SPLIT_NODE_FILES = frozenset({PAYLOAD_VALIDATION_FILE})
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


def _payload_node(function_name: str) -> str:
    return f"{PAYLOAD_VALIDATION_FILE}::{function_name}"


SPLIT_NODE_WEIGHT_OVERRIDES = {
    _payload_node("test_generated_pydantic_v2_model_accepts_schema_derived_payloads"): 500_000,
    _payload_node("test_generated_pydantic_v2_model_dumps_schema_valid_payloads"): 500_000,
    _payload_node("test_generated_pydantic_v2_model_rejects_schema_invalid_payloads"): 260_000,
    _payload_node("test_generated_payload_backend_accepts_representative_schema_payloads"): 80_000,
    _payload_node("test_generated_payload_backend_rejects_representative_schema_invalid_payloads"): 80_000,
}
SPLIT_NODEIDS = (
    _payload_node("test_payload_validation_cases_cover_discovered_schema_files"),
    _payload_node("test_payload_rejection_oracle_policy_is_classified"),
    _payload_node("test_payload_rejection_oracle_covers_supported_policy_constraints"),
    _payload_node("test_payload_backend_representative_matrix_is_classified"),
    _payload_node("test_payload_backend_full_matrix_exclusions_are_classified"),
    _payload_node("test_payload_round_trip_exclusions_are_classified"),
    _payload_node("test_pydantic_v2_legacy_runtime_exclusions_are_classified"),
    _payload_node("test_pydantic_v2_legacy_runtime_exclusions_are_version_gated"),
    _payload_node("test_payload_max_examples_env_is_configurable"),
    _payload_node("test_payload_max_examples_env_rejects_invalid_values"),
    _payload_node("test_payload_backend_case_mode_env_is_configurable"),
    _payload_node("test_payload_backend_case_mode_env_rejects_invalid_values"),
    _payload_node("test_payload_backend_all_case_mode_widens_runtime_validating_backends"),
    _payload_node("test_generated_pydantic_v2_model_accepts_schema_derived_payloads"),
    _payload_node("test_generated_pydantic_v2_model_dumps_schema_valid_payloads"),
    _payload_node("test_generated_pydantic_v2_model_rejects_schema_invalid_payloads"),
    _payload_node("test_generated_payload_backend_accepts_representative_schema_payloads"),
    _payload_node("test_generated_payload_backend_rejects_representative_schema_invalid_payloads"),
)


def _is_test_file(path: Path) -> bool:
    if EXCLUDED_PARTS & set(path.parts):
        return False
    return path.name.startswith("test_") and path.suffix == ".py" and path.as_posix() not in SPLIT_NODE_FILES


def _collect_test_items(root: Path = TESTS_ROOT) -> list[str]:
    return sorted(path.as_posix() for path in root.rglob("*.py") if _is_test_file(path))


def _item_weight(item: str) -> int:
    path = Path(item.partition("::")[0])
    if "::" in item:
        return SPLIT_NODE_WEIGHT_OVERRIDES.get(item, 10_000)
    return WEIGHT_OVERRIDES.get(item, path.stat().st_size)


def _select_shard(items: list[str], shard_index: int, shard_total: int) -> list[str]:
    shards: list[list[str]] = [[] for _ in range(shard_total)]
    shard_weights = [0] * shard_total
    weighted_items = sorted(
        ((_item_weight(item), item) for item in items),
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
            items = [*_collect_test_items(), *SPLIT_NODEIDS]
            if selected := _select_shard(items, shard_index, shard_total):
                print(*selected, sep="\n")
                return

    msg = f"No tests selected for shard {shard_index}/{shard_total}"
    raise SystemExit(msg)


if __name__ == "__main__":
    _main()
