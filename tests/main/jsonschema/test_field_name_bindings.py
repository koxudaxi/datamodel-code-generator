"""End-to-end field names that shadow annotation types or field helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, get_args, get_type_hints

import msgspec
import pytest

from datamodel_code_generator import DataModelType, InputFileType, PythonVersion
from datamodel_code_generator.format import Formatter, is_supported_in_black
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _assert_python_module_importable,
    _generated_model,
    _model_json_validator,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("target", [PythonVersion.PY_310, PythonVersion.PY_314])
@pytest.mark.parametrize("union", [False, True])
@pytest.mark.parametrize("case", ["collision", "control", "required", "late", "unused", "forward", "wire"])
@pytest.mark.parametrize(
    "backend",
    [
        DataModelType.PydanticV2BaseModel,
        DataModelType.PydanticV2Dataclass,
        DataModelType.DataclassesDataclass,
        DataModelType.MsgspecStruct,
    ],
)
def test_field_name_bindings(
    output_file: Path, entrypoint: str, target: PythonVersion, union: bool, case: str, backend: DataModelType
) -> None:
    """Preserve fields, literal text and runtime types when class names shadow imports."""
    schema_path = JSON_SCHEMA_DATA_PATH / "field_name_bindings" / f"{case}.json"
    expected = f"field_name_bindings/{case}/{backend.name}_{target.value}_{union}.py"
    alias_path = DATA_PATH / "payloads/field_name_bindings_runtime/wire_aliases.json"
    aliases = json.loads(alias_path.read_text()) if case == "wire" else {}
    use_builtin = not is_supported_in_black(target)
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=schema_path,
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=expected,
            extra_args=[
                "--output-model-type",
                backend.value,
                "--target-python-version",
                target.value,
                "--use-standard-collections",
                "--use-union-operator" if union else "--no-use-union-operator",
                "--enum-field-as-literal",
                "all",
                "--disable-timestamp",
                *(["--formatters", "builtin"] if use_builtin else []),
                *(["--aliases", str(alias_path)] if case == "wire" else []),
                *(
                    ["--disable-future-imports", "--use-schema-description", "--use-field-description"]
                    if case == "forward"
                    else []
                ),
            ],
        )
    else:
        run_generate_file_and_assert(
            input_path=schema_path,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            assert_func=assert_file_content,
            expected_file=expected,
            output_model_type=backend,
            target_python_version=target,
            use_standard_collections=True,
            use_annotated=backend == DataModelType.MsgspecStruct,
            field_constraints=backend == DataModelType.MsgspecStruct,
            use_union_operator=union,
            enum_field_as_literal="all",
            disable_timestamp=True,
            aliases=aliases,
            disable_future_imports=case == "forward",
            use_schema_description=case == "forward",
            use_field_description=case == "forward",
            **({"formatters": [Formatter.BUILTIN]} if use_builtin else {}),
        )
    if case == "forward" and target == PythonVersion.PY_314 and backend != DataModelType.MsgspecStruct:
        try:
            _assert_python_module_importable(
                DATA_PATH / "python/field_name_bindings/native_delayed_annotations.py", "native_delayed", "Child"
            )
        except NameError as native_error:
            with pytest.raises(NameError) as generated_error:
                _assert_python_module_importable(output_file, "generated_delayed", "Record")
            assert_output(
                f"native: {native_error}\ngenerated: {generated_error.value}\n",
                DATA_PATH / "payloads/field_name_bindings_runtime/native_delayed_error.txt",
            )
            return
    properties = json.loads(schema_path.read_text())["properties"]
    with _generated_model(output_file, "field_name_binding_model", "Record") as model:
        hints = get_type_hints(model)
        observations = {"fields": list(hints)}
        data = dict.fromkeys(properties, "list")
        if "items" in properties:
            data.update(items=[1, 2], count=3, child={"value": 4})
            observations["items_annotation"] = list[int] in get_args(hints["items"])
            observations["choice_literals"] = get_args(next(arg for arg in get_args(hints["choice"]) if get_args(arg)))
        elif "count" in properties:
            data["count"] = 3
        if backend == DataModelType.MsgspecStruct:
            parsed = msgspec.convert(data, type=model)
            assert_output(
                json.dumps(
                    {"decode_matches_convert": msgspec.json.decode(json.dumps(data), type=model) == parsed}, indent=2
                )
                + "\n",
                DATA_PATH / "payloads/field_name_bindings_runtime/decode.txt",
            )
        else:
            payload = (
                {aliases.get(name, name): value for name, value in data.items()}
                if backend == DataModelType.DataclassesDataclass
                else data
            )
            parsed = _model_json_validator(model)(json.dumps(payload))
        observations["values"] = {
            aliases.get(name, name): getattr(parsed, aliases.get(name, name))
            for name in properties
            if name not in {"child", "items"}
        }
        if "items" in properties:
            observations["items"] = parsed.items
            observations["child_value"] = parsed.child.value
        if case == "forward":
            observations["docstring_preserved"] = "Field Optional list metadata" in model.__doc__
            defaulted = (
                msgspec.convert({}, type=model)
                if backend == DataModelType.MsgspecStruct
                else _model_json_validator(model)("{}")
            )
            observations["default_value"] = defaulted.list
            observations["forward_identity"] = get_args(get_type_hints(type(parsed.child))["sibling"])[0] is type(
                parsed.child
            )
        assert_output(
            json.dumps(observations, ensure_ascii=False, indent=2) + "\n",
            DATA_PATH / "payloads/field_name_bindings_runtime" / f"{case}.txt",
        )


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("template", ["factory", "wrapper", "nested"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
def test_field_name_factory_template(output_file: Path, entrypoint: str, template: str, formatter: str) -> None:
    """Keep custom factories that resolve annotations outside a class body unchanged."""
    schema = JSON_SCHEMA_DATA_PATH / "field_name_bindings/factory.json"
    template_dir = JSON_SCHEMA_DATA_PATH.parent / f"templates_field_name_{template}"
    expected = f"field_name_bindings/{template}.py"
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=schema,
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=expected,
            extra_args=[
                "--output-model-type",
                "dataclasses.dataclass",
                "--target-python-version",
                "3.10",
                "--use-standard-collections",
                "--no-use-union-operator",
                "--enum-field-as-literal",
                "all",
                "--disable-timestamp",
                "--custom-template-dir",
                str(template_dir),
                "--formatters",
                *formatters,
            ],
        )
    else:
        run_generate_file_and_assert(
            input_path=schema,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            assert_func=assert_file_content,
            expected_file=expected,
            output_model_type=DataModelType.DataclassesDataclass,
            target_python_version=PythonVersion.PY_310,
            use_standard_collections=True,
            use_union_operator=False,
            enum_field_as_literal="all",
            disable_timestamp=True,
            custom_template_dir=template_dir,
            formatters=[Formatter(value) for value in formatters],
        )
    with _generated_model(output_file, "field_name_factory", "Record") as model:
        hints = get_type_hints(model)
        observations = {"fields": list(hints), "items_annotation": dict[str, list[int]] in get_args(hints["items"])}
        result = _model_json_validator(model)('{"items": {"first": [1, 2]}}')
        observations.update(items=result.items, Optional=result.Optional, choice=result.choice)
        assert_output(
            json.dumps(observations, ensure_ascii=False, indent=2) + "\n",
            DATA_PATH / "payloads/field_name_bindings_runtime/factory.txt",
        )


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
@pytest.mark.parametrize("case", ["helper_normal", "helper_collision"])
def test_field_name_template_helper(output_file: Path, entrypoint: str, formatter: str, case: str) -> None:
    """Inspect the actual model instead of an unrelated preceding helper class."""
    schema = JSON_SCHEMA_DATA_PATH / f"field_name_bindings/{case}.json"
    template_dir = JSON_SCHEMA_DATA_PATH.parent / f"templates_field_name_{case}"
    expected = f"field_name_bindings/{case}.py"
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    if entrypoint == "cli":
        run_main_and_assert(
            input_path=schema,
            output_path=output_file,
            input_file_type="jsonschema",
            assert_func=assert_file_content,
            expected_file=expected,
            extra_args=[
                "--output-model-type",
                "dataclasses.dataclass",
                "--target-python-version",
                "3.10",
                "--use-standard-collections",
                "--no-use-union-operator",
                "--disable-timestamp",
                "--custom-template-dir",
                str(template_dir),
                "--formatters",
                *formatters,
            ],
        )
    else:
        run_generate_file_and_assert(
            input_path=schema,
            output_path=output_file,
            input_file_type=InputFileType.JsonSchema,
            assert_func=assert_file_content,
            expected_file=expected,
            output_model_type=DataModelType.DataclassesDataclass,
            target_python_version=PythonVersion.PY_310,
            use_standard_collections=True,
            use_union_operator=False,
            disable_timestamp=True,
            custom_template_dir=template_dir,
            formatters=[Formatter(value) for value in formatters],
        )
    with _generated_model(output_file, "field_name_helper", "Record") as model:
        hints = get_type_hints(model)
        observations = {"fields": list(hints), "items_annotation": list[int] in get_args(hints["items"])}
        result = _model_json_validator(model)('{"Optional": "ok", "items": [1, 2]}')
        observations.update(Optional=result.Optional, items=result.items)
        assert_output(
            json.dumps(observations, indent=2) + "\n",
            DATA_PATH / "payloads/field_name_bindings_runtime/helper_model.txt",
        )
    with _generated_model(output_file, "field_name_helper", "Helper") as helper:
        observations = {"value": helper().value}
        if case == "helper_normal":
            observations["annotation_preserved"] = get_type_hints(helper)["value"] == int | None
        assert_output(
            json.dumps(observations, indent=2) + "\n",
            DATA_PATH / "payloads/field_name_bindings_runtime" / f"{case}.txt",
        )
