"""Reuse actual Pydantic specializations through public API and real CLI paths."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
from pydantic.version import VERSION as PYDANTIC_VERSION

from datamodel_code_generator import DataModelType, GenerateConfig, InputFileType, generate
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.enums import InputModelRefStrategy
from datamodel_code_generator.format import Formatter
from datamodel_code_generator.input_model import Error as InputModelError
from datamodel_code_generator.input_model import load_model_schema
from tests.conftest import assert_output
from tests.main.conftest import DATA_PATH, EXPECTED_MAIN_PATH, run_main_with_args

if TYPE_CHECKING:
    from pathlib import Path
FIXTURES = DATA_PATH / "python/input_model"
EXPECTED = EXPECTED_MAIN_PATH / "input_model/generic_reuse"
CASES = json.loads((FIXTURES / "generic_reuse_cases.json").read_text())


@pytest.mark.parametrize(
    ("record", "strategy"),
    [
        pytest.param(record, strategy, id=f"{strategy}-{record['name']}")
        for record in CASES
        for strategy in record.get("strategies", ["regenerate-all", "reuse-all", "reuse-foreign"])
    ],
)
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
def test_python_generic_reuse(record: dict, strategy: str, entrypoint: str, formatter: str, tmp_path: Path) -> None:
    """Preserve original validators and specialization identity without changing regeneration."""
    paths = ["tests.data.python.input_model." + source for source in record["sources"]]
    (tmp_path / "pyproject.toml").write_text((FIXTURES / "collision_settings/pyproject.toml").read_text())
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    output = tmp_path / "output.py"
    if entrypoint == "cli":
        args = [argument for path in paths for argument in ("--input-model", path)]
        run_main_with_args([
            *args,
            "--output",
            str(output),
            "--disable-timestamp",
            "--input-model-ref-strategy",
            strategy,
            "--formatters",
            *formatters,
        ])
    else:
        schema = load_model_schema(
            paths, InputFileType.JsonSchema, InputModelRefStrategy(strategy), DataModelType.PydanticV2BaseModel
        )
        schema = json.loads(json.dumps(schema))
        config = GenerateConfig(
            input_file_type=InputFileType.JsonSchema,
            disable_timestamp=True,
            input_filename="<stdin>",
            output=output,
            settings_path=tmp_path,
            formatters=[Formatter(value) for value in formatters],
        )
        generate(schema, config=config)
    expected_strategy = "regenerate-all" if strategy == "regenerate-all" else "reuse-all"
    stem = record["name"] + "_" + expected_strategy
    source_expected = EXPECTED / formatter if record.get("formatter_goldens") else EXPECTED
    if record.get("pydantic20_goldens") and PYDANTIC_VERSION.split(".")[:2] == ["2", "0"]:
        source_expected = EXPECTED / "pydantic20" / formatter
    assert_output(output.read_text(), source_expected / (stem + ".py"))
    runtime = subprocess.run(
        [sys.executable, str(FIXTURES / "generic_reuse_runtime.py"), str(output), json.dumps(record)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert_output(runtime.stdout, EXPECTED / (stem + ".txt"))


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
def test_python_generic_reuse_type_binding(entrypoint: str, formatter: str, tmp_path: Path) -> None:
    """Resolve a transported generic definition from a preserved field expression."""
    fixture = DATA_PATH / "jsonschema/generic_reuse_type.json"
    output = tmp_path / "output.py"
    (tmp_path / "pyproject.toml").write_text((FIXTURES / "collision_settings/pyproject.toml").read_text())
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    if entrypoint == "cli":
        run_main_with_args([
            "--input",
            str(fixture),
            "--output",
            str(output),
            "--input-file-type",
            "jsonschema",
            "--disable-timestamp",
            "--formatters",
            *formatters,
        ])
    else:
        generate(
            fixture,
            config=GenerateConfig(
                input_file_type=InputFileType.JsonSchema,
                output=output,
                disable_timestamp=True,
                settings_path=tmp_path,
                formatters=[Formatter(value) for value in formatters],
            ),
        )
    assert_output(output.read_text(), EXPECTED / "preserved.py")
    runtime = subprocess.run(
        [sys.executable, str(FIXTURES / "generic_reuse_runtime.py"), str(output), json.dumps(CASES[0])],
        capture_output=True,
        text=True,
        check=True,
    )
    assert_output(runtime.stdout, EXPECTED / "int_reuse-all.txt")


@pytest.mark.parametrize("case", ["name", "family", "index_type", "index_negative"])
def test_python_native_field_invalid_path(case: str, tmp_path: Path) -> None:
    """Reject malformed external native paths before generating executable annotations."""
    record = json.loads((DATA_PATH / "payloads/generic_native_fields" / (case + ".json")).read_text())
    with pytest.raises((TypeError, ValueError), match=record["message"]):
        generate(
            record["schema"],
            config=GenerateConfig(input_file_type=InputFileType.JsonSchema, output=tmp_path / "output.py"),
        )


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("strategy", ["reuse-all", "reuse-foreign"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
def test_python_inline_future_generic_diagnostic(
    entrypoint: str, strategy: str, formatter: str, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Diagnose only metadata which has neither a native path nor a stable export."""
    fixture = json.loads((FIXTURES / "generic_reuse_diagnostic.json").read_text())
    if entrypoint == "cli":
        run_main_with_args(
            [
                "--input-model",
                fixture["source"],
                "--input-model-ref-strategy",
                strategy,
                "--output",
                str(tmp_path / "output.py"),
                "--formatters",
                *(["builtin"] if formatter == "builtin" else ["black", "isort"]),
            ],
            expected_exit=Exit.ERROR,
            capsys=capsys,
            expected_stderr_contains=fixture["message"],
        )
    else:
        with pytest.raises(InputModelError, match=fixture["message"]):
            load_model_schema(
                [fixture["source"]],
                InputFileType.JsonSchema,
                InputModelRefStrategy(strategy),
                DataModelType.PydanticV2BaseModel,
            )
