"""Distinguish packaged templates from opaque user templates for set conversion."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import Error, InputFileType, generate
from datamodel_code_generator.__main__ import Exit
from datamodel_code_generator.model.base import TEMPLATE_DIR
from tests.conftest import assert_output
from tests.main.conftest import (
    DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _default_formatter_generate_options,
    _generated_model,
    run_main_with_args,
)
from tests.main.jsonschema.conftest import EXPECTED_JSON_SCHEMA_PATH

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("entrypoint", ["cli", "api"])
@pytest.mark.parametrize(
    "case", json.loads((DATA_PATH / "payloads/unique_model_sets/template_sources.json").read_text())
)
def test_unique_model_set_template_sources(
    tmp_path: Path, output_file: Path, capsys: pytest.CaptureFixture[str], entrypoint: str, case: dict
) -> None:
    """Keep correct custom hashing while validating canonical packaged template aliases."""
    source = JSON_SCHEMA_DATA_PATH / "unique_model_sets/object.json"
    expected = EXPECTED_JSON_SCHEMA_PATH / "unique_model_sets"
    frozen = case["frozen"]
    match case["mode"]:
        case "default":
            directory = None
        case "builtin":
            directory = TEMPLATE_DIR
        case "custom":
            directory = DATA_PATH / "templates_unique_model_sets"
        case "partial":
            directory = DATA_PATH / "templates_unique_model_sets_partial"
        case "builtin_symlink" | "custom_symlink":
            directory = tmp_path / "templates"
            directory.symlink_to(
                TEMPLATE_DIR if case["mode"] == "builtin_symlink" else DATA_PATH / "templates_unique_model_sets",
                target_is_directory=True,
            )
        case _:
            directory = tmp_path / "missing-templates"
    if entrypoint == "cli":
        run_main_with_args(
            [
                "--input",
                str(source),
                "--input-file-type",
                "jsonschema",
                "--output",
                str(output_file),
                "--disable-timestamp",
                "--use-unique-items-as-set",
                *(["--enable-faux-immutability"] if frozen else []),
                *(["--custom-template-dir", str(directory)] if directory else []),
            ],
            expected_exit=Exit.OK if frozen else Exit.ERROR,
        )
        error = capsys.readouterr().err
    else:
        options = _default_formatter_generate_options({
            "input_file_type": InputFileType.JsonSchema,
            "output": output_file,
            "disable_timestamp": True,
            "use_unique_items_as_set": True,
            "enable_faux_immutability": frozen,
            "custom_template_dir": directory,
        })
        if frozen:
            generate(source, **options)
        else:
            with pytest.raises(Error) as caught:
                generate(source, **options)
            error = f"{caught.value}\n"
    if not frozen:
        assert_output(error, expected / "object_PydanticV2BaseModel_False.txt")
        assert_output(f"{output_file.exists()}\n", expected / "missing_output.txt")
        return
    assert_output(
        output_file.read_text(encoding="utf-8"),
        expected
        / ("template_custom.py" if case["mode"].startswith("custom") else "object_PydanticV2BaseModel_True.py"),
    )
    with (
        _generated_model(
            DATA_PATH / "python/unique_model_sets/native_frozen.py", "native_frozen_set", "Container"
        ) as native,
        _generated_model(output_file, "generated_frozen_set", "Container") as generated,
    ):
        for container in (native, generated):
            item = sys.modules[container.__module__].Item
            first, second = item(value=1), item(value=1)
            singleton = {first}
            instance = container.model_validate_json(
                (DATA_PATH / "payloads/unique_model_sets/template_values.json").read_text()
            )
            assert_output(
                json.dumps(
                    {
                        "equal": first == second,
                        "equal_hash": hash(first) == hash(second),
                        "deduplicated_size": len({first, second}),
                        "membership": second in singleton,
                        "container_size": len(instance.items),
                    },
                    indent=2,
                )
                + "\n",
                expected / "template_runtime.txt",
            )
