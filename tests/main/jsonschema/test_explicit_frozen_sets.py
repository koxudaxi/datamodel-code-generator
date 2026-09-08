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
    output = tmp_path / "model.py"
    (tmp_path / "pyproject.toml").write_text('[tool.isort]\nknown_first_party = ["tests"]\n')
    options = {"enable_faux_immutability": True, **case["options"]}
    extra_data = case.get("extra_data") or ("validators" if case.get("validators") else None)
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
            str(JSON_SCHEMA_DATA_PATH / "explicit_frozen_sets" / f"{case['name']}.json"),
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
        if extra_data:
            args.extend([
                "--extra-template-data",
                str(DATA_PATH / "payloads/explicit_frozen_sets" / f"{extra_data}.json"),
            ])
        for key, value in options.items():
            if value:
                args.append("--" + key.replace("_", "-"))
                if not isinstance(value, bool):
                    args.append(value)
        run_main_with_args(args)
    else:
        if extra_data:
            options["extra_template_data"] = defaultdict(
                dict, json.loads((DATA_PATH / "payloads/explicit_frozen_sets" / f"{extra_data}.json").read_text())
            )
        generate(
            JSON_SCHEMA_DATA_PATH / "explicit_frozen_sets" / f"{case['name']}.json",
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
        payload = {"value": case["payload"], **case.get("extra_payload", {})}
        first, second = item.model_validate(payload), item.model_validate(payload)
        runtime = {"equal": first == second}
        if not case["safe"]:
            runtime.update(
                identity_hash="__hash__ = object.__hash__" in code,
                equal_dump=first.model_dump(mode="json") == second.model_dump(mode="json"),
            )
            assert_output(
                json.dumps(runtime, indent=2) + "\n",
                EXPECTED_JSON_SCHEMA_PATH / "explicit_frozen_sets/opaque.runtime.txt",
            )
            return
        originals = [MODELS[case["name"]].model_validate(payload), MODELS[case["name"]].model_validate(payload)]
        runtime.update(
            field_order=list(item.model_fields) == list(MODELS[case["name"]].model_fields),
            native_dump=first.model_dump(mode="json") == originals[0].model_dump(mode="json"),
        )
        result = container.model_validate({"items": [payload, payload]})
        expected = TypeAdapter(set[type(originals[0])]).validate_python([payload, payload])
        runtime.update(
            pairs=[
                {
                    "equal": pair[0] == pair[1],
                    "equal_hash": hash(pair[0]) == hash(pair[1]),
                    "membership": pair[1] in set(pair[:1]),
                    "size": len(set(pair)),
                }
                for pair in ([first, second], originals)
            ],
            generated_size=len(result.items),
            native_size=len(expected),
            container_dump=[x.model_dump(mode="json") for x in result.items]
            == [x.model_dump(mode="json") for x in expected],
        )
        assert_output(
            json.dumps(runtime, indent=2) + "\n",
            EXPECTED_JSON_SCHEMA_PATH / "explicit_frozen_sets/safe.runtime.txt",
        )
        with pytest.raises(ValidationError):
            item.model_validate({})
        with pytest.raises(ValidationError):
            MODELS[case["name"]].model_validate({})


@pytest.mark.parametrize(
    "implementation", ["OpaqueModel", "ModelWithMethods", "DecoratedModel", "IncompleteReferenceModel"]
)
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
    assert_output(code, EXPECTED_JSON_SCHEMA_PATH / "explicit_frozen_sets" / f"{implementation}.py")
    output = tmp_path / "model.py"
    output.write_text(code, encoding="utf-8")
    with _generated_model(output, "opaque_set_output", "Container") as container:
        item = sys.modules[container.__module__].Item
        first, second = item(value=1), item(value=1)
        runtime = {
            "equal": first == second,
            "identity_hash": "__hash__ = object.__hash__" in code,
            "equal_dump": first.model_dump() == second.model_dump() == {"value": 1},
        }
        assert_output(
            json.dumps(runtime, indent=2) + "\n",
            EXPECTED_JSON_SCHEMA_PATH / "explicit_frozen_sets/opaque.runtime.txt",
        )


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize("backend", ["dataclasses.dataclass", "typing.TypedDict", "msgspec.Struct"])
def test_explicit_non_pydantic_set_imports(tmp_path: Path, entrypoint: str, backend: str) -> None:
    """Non-Pydantic explicit sets retain bytes without loading Pydantic hash analysis."""
    import subprocess

    from datamodel_code_generator import DataModelType

    source = JSON_SCHEMA_DATA_PATH / "explicit_frozen_sets/integer.json"
    output = tmp_path / "model.py"
    if entrypoint == "cli":
        run_main_with_args([
            "--input",
            str(source),
            "--input-file-type",
            "jsonschema",
            "--output-model-type",
            backend,
            "--output",
            str(output),
            "--disable-timestamp",
            "--formatters",
            "builtin",
        ])
    else:
        generate(
            source,
            config=GenerateConfig(
                input_file_type=InputFileType.JsonSchema,
                output_model_type=DataModelType(backend),
                output=output,
                disable_timestamp=True,
                formatters=[Formatter.BUILTIN],
            ),
        )
    expected = EXPECTED_JSON_SCHEMA_PATH / "explicit_frozen_sets" / f"backend_{backend}.py"
    assert_output(output.read_text(encoding="utf-8"), expected)
    record = tmp_path / "imports.json"
    subprocess.run(
        [
            sys.executable,
            str(DATA_PATH / "python/unique_model_sets/backend_probe.py"),
            entrypoint,
            backend,
            str(source),
            str(output),
            str(record),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert_output(output.read_text(encoding="utf-8"), expected)
    imported = json.loads(record.read_text(encoding="utf-8"))["modules"]
    runtime = {"hash_analysis_imported": "datamodel_code_generator.model._set_item" in imported}
    if entrypoint == "cli":
        runtime["pydantic_backend_imported"] = any(
            name.startswith("datamodel_code_generator.model.pydantic_v2") for name in imported
        )
    assert_output(
        json.dumps(runtime, indent=2) + "\n",
        EXPECTED_JSON_SCHEMA_PATH / "explicit_frozen_sets" / f"{entrypoint}.imports.txt",
    )
