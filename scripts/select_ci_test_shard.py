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
    # Rounded milliseconds from a full local pytest --durations run on 2026-07-03.
    "tests/main/asyncapi/test_main_asyncapi.py": 420,
    "tests/main/avro/test_main_avro.py": 2_270,
    "tests/main/graphql/test_annotated.py": 80,
    "tests/main/graphql/test_main_graphql.py": 1_180,
    "tests/main/jsonschema/test_main_jsonschema.py": 13_210,
    "tests/main/openapi/test_main_openapi.py": 7_530,
    "tests/main/protobuf/test_main_protobuf.py": 520,
    "tests/main/test_cli_fast_paths.py": 1_710,
    "tests/main/test_dynamic_models.py": 550,
    "tests/main/test_error_messages.py": 40,
    "tests/main/test_exec_validation.py": 320,
    "tests/main/test_generation_determinism.py": 860,
    "tests/main/test_jsonschema_suite_conformance.py": 1,
    "tests/main/test_main_csv.py": 50,
    "tests/main/test_main_general.py": 3_990,
    "tests/main/test_main_json.py": 120,
    "tests/main/test_main_watch.py": 2_220,
    "tests/main/test_main_yaml.py": 40,
    "tests/main/test_parsed_source_cache_parity.py": 50,
    "tests/main/test_performance.py": 1,
    "tests/main/test_public_api_signature_baseline.py": 170,
    "tests/main/test_types.py": 1,
    "tests/main/xmlschema/test_main_xmlschema.py": 810,
    "tests/model/dataclass/test_param.py": 1,
    "tests/model/pydantic_v2/test_base_model.py": 1,
    "tests/model/pydantic_v2/test_config.py": 1,
    "tests/model/pydantic_v2/test_dataclass.py": 1,
    "tests/model/pydantic_v2/test_root_model.py": 1,
    "tests/model/pydantic_v2/test_root_model_type_alias.py": 1,
    "tests/model/pydantic_v2/test_types.py": 1,
    "tests/model/pydantic_v2/test_version.py": 1,
    "tests/model/test_base.py": 10,
    "tests/model/test_dataclass.py": 1,
    "tests/parser/test_base.py": 990,
    "tests/parser/test_default_put_dict.py": 1,
    "tests/parser/test_generation.py": 1,
    "tests/parser/test_generation_store_usage.py": 200,
    "tests/parser/test_graph.py": 1,
    "tests/parser/test_graphql.py": 190,
    "tests/parser/test_imports.py": 230,
    "tests/parser/test_jsonschema.py": 200,
    "tests/parser/test_openapi.py": 1_960,
    "tests/parser/test_scc.py": 100,
    "tests/parser/test_schema_version.py": 210,
    "tests/parser/test_xmlschema.py": 50,
    "tests/skills/datamodel-code-generator/test_skill_flag_drift.py": 50,
    "tests/skills/datamodel-code-generator/test_skill_recipes.py": 3_700,
    "tests/test_assert_helper_usage.py": 190,
    "tests/test_build_architecture_docs_script.py": 380,
    "tests/test_build_conformance_docs_script.py": 50,
    "tests/test_build_deprecation_docs_script.py": 100,
    "tests/test_build_docs_examples_script.py": 40,
    "tests/test_build_experimental_docs_script.py": 100,
    "tests/test_build_llms_txt_script.py": 50,
    "tests/test_build_playground_assets_script.py": 1,
    "tests/test_build_preset_docs_script.py": 490,
    "tests/test_build_release_benchmark_docs_script.py": 1_340,
    "tests/test_build_schema_docs_script.py": 220,
    "tests/test_conftest_helpers.py": 1,
    "tests/test_deprecations.py": 1,
    "tests/test_enums.py": 1,
    "tests/test_experimental.py": 1,
    "tests/test_format.py": 6_170,
    "tests/test_generate_changelog_script.py": 230,
    "tests/test_http.py": 1_090,
    "tests/test_imports.py": 1,
    "tests/test_infer_input_type.py": 110,
    "tests/test_input_model.py": 1_630,
    "tests/test_main_kr.py": 3_920,
    "tests/test_package_metadata.py": 380,
    "tests/test_prompt.py": 1,
    "tests/test_reference.py": 1,
    "tests/test_resolver.py": 1,
    "tests/test_select_ci_test_shard_script.py": 250,
    "tests/test_types.py": 10,
    "tests/test_update_command_help_on_markdown_script.py": 1,
    "tests/test_util.py": 40,
    "tests/test_validate_release_draft_analysis_script.py": 1,
    "tests/test_validators.py": 1,
    "tests/test_yaml_backend.py": 1,
}
SPLIT_NODE_WEIGHT_OVERRIDES = {
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_payload_backend_accepts_representative_schema_payloads": 3_330,
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_payload_backend_rejects_representative_schema_invalid_payloads": 850,
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_pydantic_v2_model_accepts_schema_derived_payloads": 109_400,
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_pydantic_v2_model_dumps_schema_valid_payloads": 106_910,
    f"{PAYLOAD_VALIDATION_FILE}::test_generated_pydantic_v2_model_rejects_schema_invalid_payloads": 58_170,
    f"{PAYLOAD_VALIDATION_FILE}::test_msgspec_schema_runtime_exclusions_cover_known_semantic_gaps": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_msgspec_schema_runtime_exclusions_detect_untyped_fractional_multiple_of": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_msgspec_schema_runtime_exclusions_ignore_literal_payloads": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_backend_all_case_mode_widens_runtime_validating_backends": 10,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_backend_case_mode_env_is_configurable": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_backend_case_mode_env_rejects_invalid_values": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_backend_full_matrix_exclusions_are_classified": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_backend_representative_matrix_is_classified": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_max_examples_env_is_configurable": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_max_examples_env_rejects_invalid_values": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_rejection_oracle_covers_supported_policy_constraints": 20,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_rejection_oracle_policy_is_classified": 10,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_round_trip_exclusions_are_classified": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_payload_validation_cases_cover_discovered_schema_files": 690,
    f"{PAYLOAD_VALIDATION_FILE}::test_pydantic_round_trip_exclusions_cover_uri_unique_items_normalization": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_pydantic_v2_dataclass_legacy_exclusions_cover_fractional_multiple_of": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_pydantic_v2_legacy_runtime_exclusions_are_classified": 1,
    f"{PAYLOAD_VALIDATION_FILE}::test_pydantic_v2_legacy_runtime_exclusions_are_version_gated": 1,
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
