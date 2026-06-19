"""Tests for preset documentation generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import black
import pytest
from packaging import version

from datamodel_code_generator.enums import ExtraFields
from datamodel_code_generator.preset import (
    PresetConfig,
    PresetConfigItem,
    get_latest_preset_name,
    get_preset_infos,
    render_presets,
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


def test_preset_metadata_renderers() -> None:
    """Preset metadata renderers expose the committed preset reference."""
    assert_output(render_presets("markdown"), EXPECTED_PRESET_DOCS_PATH / "presets_markdown.txt")
    assert_output(render_presets("json"), EXPECTED_PRESET_DOCS_PATH / "presets_json.txt")
    assert_output(
        f"{get_latest_preset_name()}\n{get_preset_infos()[0].name.value}\n",
        EXPECTED_PRESET_DOCS_PATH / "preset_names.txt",
    )


def test_preset_config_supports_enum_backed_string_options() -> None:
    """Preset config keeps string-backed enum options typed after validation."""
    enum_item = PresetConfig(extra_fields=ExtraFields.Forbid).items()[0]
    string_item = PresetConfig(extra_fields="allow").items()[0]
    output = "\n".join((
        _render_preset_config_item(enum_item),
        _render_preset_config_item(string_item),
        "",
    ))

    assert_output(output, EXPECTED_PRESET_DOCS_PATH / "preset_config_enum_values.txt")


def _render_preset_config_item(item: PresetConfigItem) -> str:
    match item.value, item.applied_value:
        case ExtraFields(), ExtraFields():
            return (
                f"{item.field_name}: "
                f"value={item.value.value}, "
                f"applied={item.applied_value.value}, "
                f"pyproject={item.pyproject_value}"
            )
    msg = f"Expected extra_fields preset config item, got {item!r}"  # pragma: no cover
    raise TypeError(msg)  # pragma: no cover
