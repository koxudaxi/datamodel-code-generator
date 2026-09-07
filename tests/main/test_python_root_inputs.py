"""Preserve native RootModel input schemas through CLI and API generation."""

from __future__ import annotations

import importlib
import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from datamodel_code_generator import DataModelType, InputFileType, InputModelRefStrategy, PythonVersion, generate
from datamodel_code_generator.input_model import load_model_schema
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    _generated_model,
    _uses_external_test_default_formatter,
    run_main_with_args,
)

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED = DATA_PATH / "expected/main/input_model/root_models"


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("input_format", ["module", "file"])
@pytest.mark.parametrize(
    "case",
    json.loads((DATA_PATH / "payloads/input_model_roots.json").read_text()),
    ids=lambda case: f"{case['name']}-{case['strategy']}",
)
def test_python_root_model_inputs(
    output_file: Path, entrypoint: str, input_format: str, case: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep root values, constraints, defaults and ordinary model inheritance."""
    from datamodel_code_generator.format import Formatter

    (output_file.parent / "pyproject.toml").write_bytes(
        (DATA_PATH / "python/input_model/root_models_format/pyproject.toml").read_bytes()
    )
    formatters = [Formatter.BLACK, Formatter.ISORT] if _uses_external_test_default_formatter() else [Formatter.BUILTIN]
    name = case["name"]
    strategy = case["strategy"]
    source = (
        f"tests.data.python.input_model.root_models:{name}"
        if input_format == "module"
        else f"tests/data/python/input_model/root_models.py:{name}"
    )
    expected = EXPECTED / f"{name}_{strategy}{'_file' if input_format == 'file' else ''}.py"
    if entrypoint == "cli":
        run_main_with_args(
            [
                "--output",
                str(output_file),
                "--input-file-type",
                "jsonschema",
                "--input-model",
                source,
                "--input-model-ref-strategy",
                strategy,
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.10",
                "--custom-file-header",
                "# RootModel input control",
                "--field-constraints",
                "--formatters",
                *(formatter.value for formatter in formatters),
            ],
        )
        assert_output(output_file.read_text(encoding="utf-8"), expected)
    else:
        schema = load_model_schema(
            [source],
            InputFileType.JsonSchema,
            ref_strategy=InputModelRefStrategy(strategy),
            output_model_type=DataModelType.PydanticV2BaseModel,
        )
        generate(
            schema,
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=PythonVersion.PY_310,
            field_constraints=True,
            custom_file_header="# RootModel input control",
            formatters=formatters,
            output=output_file,
        )
        assert_output(output_file.read_text(encoding="utf-8"), expected)
    if input_format == "file":
        monkeypatch.syspath_prepend(str(DATA_PATH / "python/input_model"))
    native = getattr(importlib.import_module("tests.data.python.input_model.root_models"), name)
    with _generated_model(output_file, "generated_python_root_input", name) as model:
        value = model.model_validate_json(json.dumps(case["valid"]))
        native_value = native.model_validate_json(json.dumps(case["valid"]))
        result = {"dump": value.model_dump(mode="json"), "rejects_invalid": True}
        with pytest.raises(ValidationError):
            model.model_validate_json(json.dumps(case["invalid"]))
        with pytest.raises(ValidationError):
            native.model_validate_json(json.dumps(case["invalid"]))
        if "default" in case:
            result["default"] = model().model_dump(mode="json")
        result["root_model"] = model.__pydantic_root_model__
        if native.__pydantic_root_model__:
            with pytest.raises(ValidationError):
                model.model_validate({})
            with pytest.raises(ValidationError):
                native.model_validate({})
            result["rejects_object"] = True
        expected_result = EXPECTED / f"{name}_{strategy}.txt"
        assert_output(json.dumps(result, indent=2) + "\n", expected_result)
        result["dump"] = native_value.model_dump(mode="json")
        result["root_model"] = native.__pydantic_root_model__
        if "default" in case:
            result["default"] = native().model_dump(mode="json")
        assert_output(json.dumps(result, indent=2) + "\n", expected_result)
