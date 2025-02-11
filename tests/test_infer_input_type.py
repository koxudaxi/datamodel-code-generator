from __future__ import annotations

from pathlib import Path

from datamodel_code_generator import InputFileType, infer_input_type

DATA_PATH: Path = Path(__file__).parent / "data"


def test_infer_input_type() -> None:
    def assert_infer_input_type(file: Path, raw_data_type: InputFileType) -> None:
        __tracebackhide__ = True
        if file.is_dir():
            return
        if file.suffix not in {".yaml", ".json"}:
            return
        result = infer_input_type(file.read_text())
        assert result == raw_data_type, f"{file} was the wrong type!"

    for file in (DATA_PATH / "json").rglob("*"):
        if str(file).endswith("broken.json"):
            continue
        assert_infer_input_type(file, InputFileType.Json)
    for file in (DATA_PATH / "jsonschema").rglob("*"):
        if str(file).endswith((
            "external_child.json",
            "external_child.yaml",
            "extra_data_msgspec.json",
        )):
            continue
        assert_infer_input_type(file, InputFileType.JsonSchema)
    for file in (DATA_PATH / "openapi").rglob("*"):
        if "all_of_with_relative_ref" in str(file):
            continue
        if "reference_same_hierarchy_directory" in str(file):
            continue
        if str(file).endswith((
            "aliases.json",
            "extra_data.json",
            "extra_data_msgspec.json",
            "invalid.yaml",
            "list.json",
            "empty_data.json",
            "root_model.yaml",
            "json_pointer.yaml",
            "const.json",
            "array_called_fields_with_oneOf_items.yaml",
        )):
            continue

        if str(file).endswith("not.json"):
            assert_infer_input_type(file, InputFileType.Json)
            continue
        assert_infer_input_type(file, InputFileType.OpenAPI)
