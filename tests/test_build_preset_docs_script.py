"""Tests for preset documentation generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import black
import pytest
from packaging import version

from datamodel_code_generator.enums import DataModelType, InputFileType
from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.preset import (
    PresetContext,
    PresetError,
    get_latest_preset_name,
    get_preset_infos,
    preset_config_updates,
    render_presets,
    resolve_preset,
)
from tests.conftest import assert_output

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_preset_docs.py"
EXPECTED_PRESET_DOCS_PATH = Path(__file__).resolve().parent / "data" / "expected" / "preset_docs"
BLACK_LT_233 = version.parse("23.3.0") > version.parse(black.__version__)


@pytest.mark.skipif(BLACK_LT_233, reason="Installed black doesn't support the Python 3.12 quick-start target")
def test_build_preset_docs_check_is_up_to_date() -> None:
    """Generated preset docs and quick-start examples are committed."""
    subprocess.run([sys.executable, str(SCRIPT), "--check"], check=True)


def test_build_preset_docs_json_format() -> None:
    """The docs script can print preset metadata as JSON."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert_output(result.stdout, EXPECTED_PRESET_DOCS_PATH / "presets_json.txt")


def test_build_preset_docs_check_help_mentions_all_generated_targets() -> None:
    """The --check help text covers all generated preset docs outputs."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert_output(result.stdout, EXPECTED_PRESET_DOCS_PATH / "build_preset_docs_help.txt")


def test_build_preset_docs_quick_start_generation_timeout_has_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout errors include the command that failed."""
    from scripts import build_preset_docs

    def timeout_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=kwargs["timeout"],
            output="stdout\n",
            stderr="stderr\n",
        )

    monkeypatch.setattr(build_preset_docs.subprocess, "run", timeout_run)

    with pytest.raises(RuntimeError, match=r"Timed out after .* datamodel_code_generator"):
        build_preset_docs._generate_quick_start_model("standard-20260617")


def test_preset_metadata_renderers() -> None:
    """Preset metadata renderers expose the committed preset reference."""
    assert_output(render_presets("markdown"), EXPECTED_PRESET_DOCS_PATH / "presets_markdown.txt")
    assert_output(render_presets("json"), EXPECTED_PRESET_DOCS_PATH / "presets_json.txt")
    assert_output(
        f"{get_latest_preset_name()}\n{get_preset_infos()[0].name.value}\n",
        EXPECTED_PRESET_DOCS_PATH / "preset_names.txt",
    )


def test_standard_preset_resolver_output_specific_configs() -> None:
    """The standard preset resolves output-specific option groups."""
    msgspec_config = resolve_preset(
        "standard-20260617",
        PresetContext(
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.MsgspecStruct,
            target_python_version=PythonVersion.PY_310,
        ),
    )
    typed_dict_config = resolve_preset(
        "standard-20260617",
        PresetContext(
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.TypingTypedDict,
            target_python_version=PythonVersion.PY_310,
        ),
    )
    py311_config = resolve_preset(
        "standard-20260617",
        PresetContext(
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=PythonVersion.PY_311,
        ),
    )

    assert_output(
        (
            json_dumps({
                "msgspec": preset_config_updates(msgspec_config),
                "typed_dict": preset_config_updates(typed_dict_config),
                "py311": preset_config_updates(py311_config),
            })
        ),
        EXPECTED_PRESET_DOCS_PATH / "standard_preset_patches.txt",
    )

    with pytest.raises(PresetError, match="Unknown preset"):
        resolve_preset(
            "unknown",
            PresetContext(
                input_file_type=InputFileType.JsonSchema,
                output_model_type=DataModelType.PydanticV2BaseModel,
                target_python_version=PythonVersion.PY_310,
            ),
        )


def json_dumps(value: object) -> str:
    """Serialize expected fixture payloads consistently."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"
