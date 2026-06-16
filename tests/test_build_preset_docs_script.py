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
    render_presets,
    resolve_preset,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_preset_docs.py"
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

    presets = json.loads(result.stdout)
    assert presets[0]["name"] == "standard-20260617"
    assert presets[0]["requires_target_python_version"] is True


def test_build_preset_docs_check_help_mentions_all_generated_targets() -> None:
    """The --check help text covers all generated preset docs outputs."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "preset docs and preset-powered quick-" in result.stdout
    assert "start examples are up to date" in result.stdout


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
    markdown = render_presets("markdown")
    presets = json.loads(render_presets("json"))

    assert get_latest_preset_name() == "standard-20260617"
    assert get_preset_infos()[0].name.value == "standard-20260617"
    assert "# Presets" in markdown
    assert "`standard-20260617`" in markdown
    assert presets[0]["name"] == "standard-20260617"
    assert presets[0]["option_groups"]


def test_standard_preset_resolver_output_specific_patches() -> None:
    """The standard preset resolves output-specific option groups."""
    msgspec_patch = resolve_preset(
        "standard-20260617",
        PresetContext(
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.MsgspecStruct,
            target_python_version=PythonVersion.PY_310,
        ),
    )
    typed_dict_patch = resolve_preset(
        "standard-20260617",
        PresetContext(
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.TypingTypedDict,
            target_python_version=PythonVersion.PY_310,
        ),
    )
    py311_patch = resolve_preset(
        "standard-20260617",
        PresetContext(
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=PythonVersion.PY_311,
        ),
    )

    assert msgspec_patch.snake_case_field is True
    assert msgspec_patch.use_standard_primitive_types is True
    assert typed_dict_patch.snake_case_field is None
    assert typed_dict_patch.use_frozen_field is True
    assert py311_patch.use_specialized_enum is True

    with pytest.raises(PresetError, match="Unknown preset"):
        resolve_preset(
            "unknown",
            PresetContext(
                input_file_type=InputFileType.JsonSchema,
                output_model_type=DataModelType.PydanticV2BaseModel,
                target_python_version=PythonVersion.PY_310,
            ),
        )
