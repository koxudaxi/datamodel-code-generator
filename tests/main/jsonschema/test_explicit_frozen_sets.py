"""Preserve native frozen value hashes for explicitly declared model sets."""

from __future__ import annotations

import json
import operator
import sys
from collections import defaultdict
from typing import TYPE_CHECKING

import pytest
from pydantic import TypeAdapter, ValidationError

from datamodel_code_generator import GenerateConfig, InputFileType, generate
from datamodel_code_generator.format import Formatter
from datamodel_code_generator.model.base import TEMPLATE_DIR
from tests.conftest import assert_output
from tests.data.python.unique_model_sets.explicit_native import MODELS
from tests.main.conftest import DATA_PATH, JSON_SCHEMA_DATA_PATH, _generated_model, run_main_with_args
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("formatter", ["builtin", "external"])
@pytest.mark.parametrize("conversion", [False, True])
@pytest.mark.parametrize(
    "case",
    json.loads((DATA_PATH / "payloads/explicit_frozen_sets/cases.json").read_text()),
    ids=operator.itemgetter("name"),
)
def test_explicit_frozen_set_hashes(
    tmp_path: Path, entrypoint: str, formatter: str, conversion: bool, case: dict
) -> None:
    """Compare real generation, native hashes, and preserved opaque controls."""
    source = JSON_SCHEMA_DATA_PATH / "explicit_frozen_sets" / f"{case['name']}.json"
    output = tmp_path / "model.py"
    (tmp_path / "pyproject.toml").write_text('[tool.isort]\nknown_first_party = ["tests"]\n')
    options = {"enable_faux_immutability": True, **case["options"]}
    directory = (
        DATA_PATH / "templates_unique_model_sets_partial"
        if case.get("partial")
        else DATA_PATH / "templates_unique_model_sets"
        if case.get("custom")
        else TEMPLATE_DIR
        if case.get("packaged")
        else None
    )
    formatters = ["builtin"] if formatter == "builtin" else ["black", "isort"]
    if entrypoint == "cli":
        args = [
            "--input",
            str(source),
            "--input-file-type",
            "jsonschema",
            "--output",
            str(output),
            "--disable-timestamp",
            "--formatters",
            *formatters,
        ]
        if conversion:
            args.append("--use-unique-items-as-set")
        if directory:
            args.extend(["--custom-template-dir", str(directory)])
        if case.get("validators"):
            args.extend(["--extra-template-data", str(DATA_PATH / "payloads/explicit_frozen_sets/validators.json")])
        for key, value in options.items():
            if value:
                args.append("--" + key.replace("_", "-"))
                if not isinstance(value, bool):
                    args.append(value)
        run_main_with_args(args)
    else:
        if case.get("validators"):
            options["extra_template_data"] = defaultdict(
                dict, json.loads((DATA_PATH / "payloads/explicit_frozen_sets/validators.json").read_text())
            )
        generate(
            source,
            config=GenerateConfig(
                input_file_type=InputFileType.JsonSchema,
                output=output,
                disable_timestamp=True,
                use_unique_items_as_set=conversion,
                custom_template_dir=directory,
                formatters=[Formatter(f) for f in formatters],
                **options,
            ),
        )
    code = output.read_text(encoding="utf-8")
    assert_output(code, EXPECTED_JSON_SCHEMA_PATH / "explicit_frozen_sets" / f"{case['name']}.py")
    with _generated_model(output, "explicit_set_output", "Container") as container:
        item = sys.modules[container.__module__].Item
        payload = {"value": case["payload"]}
        first, second = item.model_validate(payload), item.model_validate(payload)
        assert first == second
        if not case["safe"]:
            assert "__hash__ = object.__hash__" in code
            assert first.model_dump(mode="json") == second.model_dump(mode="json")
            return
        native = MODELS[case["name"]]
        originals = [native.model_validate(payload), native.model_validate(payload)]
        assert list(item.model_fields) == list(native.model_fields)
        assert first.model_dump(mode="json") == originals[0].model_dump(mode="json")
        for pair in ([first, second], originals):
            assert pair[0] == pair[1]
            assert hash(pair[0]) == hash(pair[1])
            expected = {pair[0]}
            assert pair[1] in expected
            assert len(set(pair)) == 1
        result = container.model_validate({"items": [payload, payload]})
        expected = TypeAdapter(set[native]).validate_python([payload, payload])
        assert len(result.items) == len(expected) == 1
        assert [x.model_dump(mode="json") for x in result.items] == [x.model_dump(mode="json") for x in expected]
        with pytest.raises(ValidationError):
            item.model_validate({})
        with pytest.raises(ValidationError):
            native.model_validate({})


@pytest.mark.parametrize("implementation", ["OpaqueModel", "ModelWithMethods", "DecoratedModel"])
@pytest.mark.parametrize("conversion", [False, True])
def test_explicit_set_parser_extension(tmp_path: Path, implementation: str, conversion: bool) -> None:
    """Keep actual external parser model implementations and custom methods opaque."""
    from datamodel_code_generator.model.pydantic_v2 import DataModelField, DataTypeManager, RootModel
    from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
    from tests.data.python.unique_model_sets import opaque_generator

    parser = JsonSchemaParser(
        (JSON_SCHEMA_DATA_PATH / "explicit_frozen_sets/integer.json").resolve(),
        data_model_type=getattr(opaque_generator, implementation),
        data_model_root_type=RootModel,
        data_model_field_type=DataModelField,
        data_type_manager_type=DataTypeManager,
        enable_faux_immutability=True,
        use_unique_items_as_set=conversion,
        formatters=[Formatter.BUILTIN],
    )
    code = parser.parse()
    assert isinstance(code, str)
    assert_output(code, EXPECTED_JSON_SCHEMA_PATH / "explicit_frozen_sets" / f"{implementation}.py")
    output = tmp_path / "model.py"
    output.write_text(code, encoding="utf-8")
    with _generated_model(output, "opaque_set_output", "Container") as container:
        item = sys.modules[container.__module__].Item
        first, second = item(value=1), item(value=1)
        assert first == second
        assert "__hash__ = object.__hash__" in code
        assert first.model_dump() == second.model_dump() == {"value": 1}


def test_explicit_set_unresolved_reference() -> None:
    """An incomplete third-party reference cannot prove a native frozen hash."""
    from collections import defaultdict

    from datamodel_code_generator.model._set_item import SetItemValidator
    from datamodel_code_generator.model.pydantic_v2 import BaseModel, DataModelField, DataTypeManager
    from datamodel_code_generator.reference import Reference

    data_type = DataTypeManager().data_type
    model = BaseModel(
        reference=Reference(path="Item", name="Item"),
        fields=[DataModelField(name="value", data_type=data_type(reference=Reference(path="missing", name="Missing")))],
        extra_template_data=defaultdict(dict, {"Item": {"config": {"frozen": True}}}),
    )
    assert not SetItemValidator().has_native_pydantic_hash(model)
