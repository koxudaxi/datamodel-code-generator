"""Runtime regressions for public exports after dotted module placement."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import Formatter, InputFileType, generate
from datamodel_code_generator.format import PythonVersion, is_supported_in_black
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


_EXPORT_CASES = [
    ("dotted_module_exports", "children", None, None, False, "plain", "children"),
    ("dotted_module_exports", "recursive", None, None, False, "plain", "recursive"),
    ("dotted_module_exports", "children", "single", None, False, "single", "children_single"),
    ("dotted_module_exports", "recursive", "single", None, False, "single", "recursive_single"),
    (
        "dotted_module_exports_collision",
        "recursive",
        "single",
        "minimal-prefix",
        False,
        "collision",
        "collision_minimal",
    ),
    (
        "dotted_module_exports_collision",
        "recursive",
        "single",
        "full-prefix",
        False,
        "collision",
        "collision_full",
    ),
    ("dotted_module_exports_reuse", "recursive", "single", "minimal-prefix", True, "reuse", "reuse"),
    ("dotted_module_exports_cycle", "children", None, None, False, "cycle", "cycle_children"),
    ("dotted_module_exports_cycle", "recursive", None, None, False, "cycle", "cycle_recursive"),
    ("dotted_module_exports_cycle", "children", "single", None, False, "cycle_single", "cycle_children_single"),
    (
        "dotted_module_exports_cycle",
        "recursive",
        "single",
        None,
        False,
        "cycle_single",
        "cycle_recursive_single",
    ),
    (
        "dotted_module_exports_cycle_collision",
        "recursive",
        None,
        "minimal-prefix",
        False,
        "cycle",
        "cycle_minimal",
    ),
    ("dotted_module_exports_cycle_collision", "recursive", None, "full-prefix", False, "cycle", "cycle_full"),
]


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize(
    ("fixture", "scope", "split", "strategy", "reuse", "runtime_case", "expected", "target_version", "validation"),
    [
        (*case, version, "source")
        for case in _EXPORT_CASES
        for version in (list(PythonVersion) if "_cycle" in case[0] else [PythonVersion.PY_310])
    ]
    + [
        (
            *case,
            PythonVersion(f"{sys.version_info.major}.{sys.version_info.minor}")
            if "_cycle" in case[0]
            else PythonVersion.PY_310,
            "runtime",
        )
        for case in _EXPORT_CASES
    ],
)
def test_dotted_module_exports(
    output_dir: Path,
    entrypoint: str,
    target_version: PythonVersion,
    fixture: str,
    scope: str,
    split: str | None,
    strategy: str | None,
    reuse: bool,
    runtime_case: str,
    expected: str,
    validation: str,
) -> None:
    """Keep each export local to its final package and preserve model identities."""
    if target_version == PythonVersion.PY_314:
        expected += "_py314"
    output_dir = output_dir.with_name(f"{expected}_{target_version.name.lower()}_{entrypoint}_{validation}")
    expected_directory = EXPECTED_MAIN_PATH / "jsonschema" / f"dotted_module_exports_{expected}"
    formatter_options = {} if is_supported_in_black(target_version) else {"formatters": [Formatter.BUILTIN]}
    if entrypoint == "cli":
        extra_args = [
            "--target-python-version",
            target_version.value,
            "--treat-dot-as-module",
            "--all-exports-scope",
            scope,
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-exact-imports",
            "--disable-timestamp",
        ]
        if formatter_options:
            extra_args.extend(["--formatters", "builtin"])
        if split:
            extra_args.extend(["--module-split-mode", split])
        if strategy:
            extra_args.extend(["--all-exports-collision-strategy", strategy])
        if reuse:
            extra_args.extend(["--reuse-model", "--reuse-scope", "tree"])
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / fixture,
            output_path=output_dir,
            input_file_type="jsonschema",
            expected_directory=expected_directory,
            extra_args=extra_args,
        )
    else:
        generate(
            JSON_SCHEMA_DATA_PATH / fixture,
            **_default_formatter_generate_options({
                "input_file_type": InputFileType.JsonSchema,
                "target_python_version": target_version,
                "output": output_dir,
                "treat_dot_as_module": True,
                "all_exports_scope": scope,
                "module_split_mode": split,
                "all_exports_collision_strategy": strategy,
                "reuse_model": reuse,
                "reuse_scope": "tree" if reuse else "module",
                "output_model_type": "pydantic_v2.BaseModel",
                "use_exact_imports": True,
                "disable_timestamp": True,
                **formatter_options,
            }),
        )
        assert_directory_content(output_dir, expected_directory)
    if validation == "source":
        return
    result = subprocess.run(
        [
            sys.executable,
            str(DATA_PATH / "python" / "dotted_module_exports_runtime.py"),
            str(output_dir),
            runtime_case,
            target_version.value,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert_output(result.stdout, expected_directory.with_name(f"{expected_directory.name}_runtime.txt"))
