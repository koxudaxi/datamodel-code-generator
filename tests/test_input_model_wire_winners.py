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
        assert_output(
            json.dumps(schema, indent=2), EXPECTED_INPUT_MODEL_PATH / f"wire_winner_{case.lower()}_schema.txt"
        )
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
        for instance, fields, order in (
            (native, options["fields"], options["order"]),
            (generated, {name: name for name in options["fields"]}, list(type(generated).model_fields)),
        ):
            values = {}
            for wire_name, attribute_name in fields.items():
                value = instance[attribute_name] if isinstance(instance, dict) else getattr(instance, attribute_name)
                values[wire_name] = {
                    "type": type(value).__name__,
                    "value": value(7) if callable(value) else sorted(value) if isinstance(value, frozenset) else value,
                }
            assert_output(
                json.dumps({"order": order, "values": values}, indent=2),
                EXPECTED_INPUT_MODEL_PATH / f"wire_winner_{case.lower()}_runtime.txt",
            )
        if options.get("reject_noncallable"):
            payload["shared"] = "not callable"
            with pytest.raises(ValidationError):
                TypeAdapter(source_type).validate_python(payload)
            with pytest.raises(ValidationError):
                model.model_validate(payload)


@pytest.mark.parametrize("case", ["UserExtensions", "CollisionExtensions", "ExtensionContainer"])
def test_validation_property_user_extensions(case: str) -> None:
    """Internal ownership metadata preserves native schema extensions and instance data."""
    source_type = getattr(importlib.import_module(SOURCE_MODULE), case)
    native_schema = TypeAdapter(source_type).json_schema()
    schema = load_model_schema([f"{SOURCE_MODULE}:{case}"], InputFileType.JsonSchema)
    observed = schema["$defs"]["CollisionExtensions"] if case == "ExtensionContainer" else schema
    expected = native_schema["$defs"]["CollisionExtensions"] if case == "ExtensionContainer" else native_schema
    for candidate in (observed, expected):
        keys = ("x-datamodel-code-generator-field-name", "x-datamodel-code-generator-field-names")
        records = {
            "root": {key: candidate[key] for key in (*keys, "examples")},
            "property": {key: candidate["properties"]["shared"][key] for key in keys},
            "default": candidate["properties"]["metadata"]["default"],
        }
        assert_output(
            json.dumps(records, indent=2), EXPECTED_INPUT_MODEL_PATH / f"wire_winner_{case.lower()}_extensions.txt"
        )
