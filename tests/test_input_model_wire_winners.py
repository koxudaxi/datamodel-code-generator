"""Real Python input-model conversion with colliding validation properties."""

from __future__ import annotations

import importlib
import json
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import TypeAdapter, ValidationError

from datamodel_code_generator import GenerateConfig, InputFileType, generate
from datamodel_code_generator.format import Formatter
from datamodel_code_generator.input_model import load_model_schema
from tests.conftest import assert_output
from tests.main.conftest import _generated_model
from tests.test_input_model import EXPECTED_INPUT_MODEL_PATH, _input_model_args, run_main_with_args

if TYPE_CHECKING:
    from pathlib import Path

SOURCE_MODULE = "tests.data.python.input_model.wire_winners"
CASES = json.loads((EXPECTED_INPUT_MODEL_PATH.parents[2] / "python/input_model/wire_winners.json").read_text())


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["external", "builtin"])
def test_input_model_validation_property_winners(tmp_path: Path, case: str, entrypoint: str, formatter: str) -> None:
    """Only the field whose schema survives may supplement the emitted property."""
    options = CASES[case]
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    output = tmp_path / "model.py"
    paths = [f"{SOURCE_MODULE}:{name}" for name in options.get("models", [case])]
    model_name = options.get("model", case)
    if entrypoint == "cli":
        run_main_with_args(
            _input_model_args(
                paths, output_path=output, extra_args=["--disable-timestamp", "--formatters", *formatters]
            )
        )
    else:
        schema = load_model_schema(paths, InputFileType.JsonSchema)
        if case == "InlinedWins":
            assert_output(json.dumps(schema["examples"]), EXPECTED_INPUT_MODEL_PATH / "wire_winner_examples.txt")
        assert "x-datamodel-code-generator-field-" not in json.dumps({
            key: value for key, value in schema.items() if key != "examples"
        })
        generate(
            schema,
            config=GenerateConfig(
                input_file_type=InputFileType.JsonSchema,
                output=output,
                disable_timestamp=True,
                input_filename="<stdin>",
                formatters=[Formatter(value) for value in formatters],
            ),
        )
    assert_output(output.read_text(), EXPECTED_INPUT_MODEL_PATH / f"wire_winner_{case.lower()}.py")
    payload: dict[str, Any] = {"first": 1, "shared": int if options.get("callable") else [1, 1, 2], "last": "end"}
    if case == "PathWins":
        payload["values"] = payload.pop("shared")
        payload["data"] = {"values": [7, 7]}
    elif case in {"Serialization", "PlainData", "PlainTyped"}:
        payload["values"] = payload.pop("shared")
        if case == "Serialization":
            payload["items"] = [3, 3, 4]
    elif case == "Populated":
        payload.update(values=[7, 7], items=[8, 8])
    source_type = getattr(importlib.import_module(SOURCE_MODULE), model_name)
    native = TypeAdapter(source_type).validate_python({"item": payload} if options.get("nested") else payload)
    with _generated_model(output, f"generated_winner_{case}", model_name) as model:
        generated = model.model_validate({"item": payload} if options.get("nested") else payload)
        if options.get("nested"):
            native, generated = native.item, generated.item
        assert list(type(generated).model_fields) == options["order"]
        for wire_name, attribute_name in options["fields"].items():
            expected = native[attribute_name] if isinstance(native, dict) else getattr(native, attribute_name)
            actual = getattr(generated, wire_name)
            assert actual == expected
            assert type(actual) is type(expected)
        if options.get("reject_noncallable"):
            payload["shared"] = "not callable"
            with pytest.raises(ValidationError):
                TypeAdapter(source_type).validate_python(payload)
            with pytest.raises(ValidationError):
                model.model_validate(payload)
