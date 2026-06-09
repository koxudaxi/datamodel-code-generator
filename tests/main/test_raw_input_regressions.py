"""Regression tests for raw sample-data input handling."""

from __future__ import annotations

import pytest

from datamodel_code_generator import (
    DataModelType,
    Formatter,
    InputFileType,
    InvalidFileFormatError,
    generate,
)


def _generate_raw_model(source: str, input_file_type: InputFileType) -> str:
    result = generate(
        source,
        input_file_type=input_file_type,
        output_model_type=DataModelType.PydanticV2BaseModel,
        disable_timestamp=True,
        formatters=[Formatter.BLACK, Formatter.ISORT],
    )
    assert isinstance(result, str)
    return result


def test_dict_text_input_is_parsed() -> None:
    """Parse dict text input instead of treating it as a raw string sample."""
    code = _generate_raw_model("{'a': 1}", InputFileType.Dict)

    assert "class Model(BaseModel):" in code
    assert "a: int" in code
    assert "RootModel[str]" not in code


def test_csv_duplicate_header_keeps_following_columns() -> None:
    """Use DictReader row values so duplicate headers do not hide later columns."""
    code = _generate_raw_model("a,a,b\n1,2,3\n", InputFileType.CSV)

    assert "a: str" in code
    assert "b: str" in code


def test_csv_missing_trailing_cell_infers_null_column() -> None:
    """Preserve missing trailing cells from the first row."""
    code = _generate_raw_model("a,b,c\n1,2\n", InputFileType.CSV)

    assert "a: str" in code
    assert "b: str" in code
    assert "c: None" in code


def test_yaml_top_level_list_is_supported() -> None:
    """Allow YAML raw sample data to use a top-level list like JSON input."""
    code = _generate_raw_model("- a: 1\n", InputFileType.Yaml)

    assert "class ModelItem(BaseModel):" in code
    assert "a: int" in code
    assert "class Model(RootModel[list[ModelItem]]):" in code


def test_yaml_genson_errors_are_wrapped() -> None:
    """Wrap genson failures for YAML values that cannot become JSON Schema."""
    with pytest.raises(InvalidFileFormatError, match="Invalid file format for yaml"):
        _generate_raw_model("fruits: !!set\n  ? apple\n  ? banana\n", InputFileType.Yaml)
