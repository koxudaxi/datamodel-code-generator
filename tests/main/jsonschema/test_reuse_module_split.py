"""Runtime regression tests for tree reuse with per-model modules."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import InputFileType, generate
from tests.conftest import assert_directory_content, assert_output
from tests.main.conftest import (
    DATA_PATH,
    EXPECTED_MAIN_PATH,
    JSON_SCHEMA_DATA_PATH,
    _default_formatter_generate_options,
    run_main_and_assert,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("metadata", [False, True])
@pytest.mark.parametrize("collapse", [False, True])
@pytest.mark.parametrize("exact", [False, True])
def test_reuse_tree_single_module_imports(
    output_dir: Path, entrypoint: str, metadata: bool, collapse: bool, exact: bool
) -> None:
    """Resolve moved canonical models and retained wrappers in a fresh interpreter."""
    fixture = "reuse_scope_tree_single" + ("_collapsed" if collapse else "") + ("_exact" if exact else "")
    expected_directory = EXPECTED_MAIN_PATH / "jsonschema" / fixture
    metadata_path = output_dir.parent / "model-map.json"
    if entrypoint == "cli":
        extra_args = [
            "--reuse-model",
            "--reuse-scope",
            "tree",
            "--module-split-mode",
            "single",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--disable-timestamp",
        ]
        if metadata:
            extra_args.extend(["--emit-model-metadata", str(metadata_path)])
        if collapse:
            extra_args.append("--collapse-reuse-models")
        if exact:
            extra_args.append("--use-exact-imports")
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / "reuse_scope_tree",
            output_path=output_dir,
            input_file_type="jsonschema",
            expected_directory=expected_directory,
            extra_args=extra_args,
        )
    else:
        generate(
            JSON_SCHEMA_DATA_PATH / "reuse_scope_tree",
            **_default_formatter_generate_options({
                "input_file_type": InputFileType.JsonSchema,
                "output": output_dir,
                "reuse_model": True,
                "reuse_scope": "tree",
                "module_split_mode": "single",
                "output_model_type": "pydantic_v2.BaseModel",
                "disable_timestamp": True,
                "collapse_reuse_models": collapse,
                "use_exact_imports": exact,
                "emit_model_metadata": metadata_path if metadata else None,
            }),
        )
        assert_directory_content(output_dir, expected_directory)
    if metadata:
        assert_output(
            metadata_path.read_text(encoding="utf-8"),
            expected_directory.with_name(f"{fixture}_metadata.txt"),
        )
    result = subprocess.run(
        [sys.executable, str(DATA_PATH / "python" / "reuse_tree_single_runtime.py"), str(output_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert_output(
        result.stdout,
        EXPECTED_MAIN_PATH / "jsonschema" / f"reuse_scope_tree_single_runtime{'_collapsed' if collapse else ''}.txt",
    )
