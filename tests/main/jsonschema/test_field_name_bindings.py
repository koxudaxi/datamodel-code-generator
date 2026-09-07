"""End-to-end field names that shadow annotation types or field helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, get_args, get_type_hints

import msgspec
import pytest

from datamodel_code_generator import DataModelType, InputFileType, PythonVersion
from tests.main.conftest import (
    JSON_SCHEMA_DATA_PATH,
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
    alias_path = JSON_SCHEMA_DATA_PATH / "field_name_bindings/wire_aliases.json"
    aliases = json.loads(alias_path.read_text()) if case == "wire" else {}
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
        )
    properties = json.loads(schema_path.read_text())["properties"]
    with _generated_model(output_file, "field_name_binding_model", "Record") as model:
        hints = get_type_hints(model)
        assert list(hints) == [aliases.get(name, name) for name in properties]
        data = dict.fromkeys(properties, "list")
        if "items" in properties:
            data.update(items=[1, 2], count=3, child={"value": 4})
            assert list[int] in get_args(hints["items"])
            assert get_args(next(arg for arg in get_args(hints["choice"]) if get_args(arg))) == (
                "list",
                "Optional",
                "Field",
            )
        elif "count" in properties:
            data["count"] = 3
        if backend == DataModelType.MsgspecStruct:
            parsed = msgspec.convert(data, type=model)
            assert msgspec.json.decode(json.dumps(data), type=model) == parsed
        else:
            payload = (
                {aliases.get(name, name): value for name, value in data.items()}
                if backend == DataModelType.DataclassesDataclass
                else data
            )
            parsed = _model_json_validator(model)(json.dumps(payload))
        for name in properties:
            if name not in {"child", "items"}:
                assert getattr(parsed, aliases.get(name, name)) == data[name]
        if "items" in properties:
            assert parsed.items == [1, 2]
            assert parsed.child.value == 4
        if case == "forward":
            assert "Field Optional list metadata" in model.__doc__
            defaulted = (
                msgspec.convert({}, type=model)
                if backend == DataModelType.MsgspecStruct
                else _model_json_validator(model)("{}")
            )
            assert defaulted.list == "Field Optional list — 名前"
            assert get_args(get_type_hints(type(parsed.child))["sibling"])[0] is type(parsed.child)


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("template", ["factory", "wrapper", "nested"])
def test_field_name_factory_template(output_file: Path, entrypoint: str, template: str) -> None:
    """Keep custom factories that resolve annotations outside a class body unchanged."""
    schema = JSON_SCHEMA_DATA_PATH / "field_name_bindings/factory.json"
    template_dir = JSON_SCHEMA_DATA_PATH.parent / f"templates_field_name_{template}"
    expected = f"field_name_bindings/{template}.py"
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
        )
    with _generated_model(output_file, "field_name_factory", "Record") as model:
        hints = get_type_hints(model)
        assert list(hints) == ["items", "Optional", "choice"]
        assert dict[str, list[int]] in get_args(hints["items"])
        result = _model_json_validator(model)('{"items": {"first": [1, 2]}}')
        assert result.items == {"first": [1, 2]}
        assert result.Optional == "Optional Field list — 名前"
        assert result.choice == "Optional"
