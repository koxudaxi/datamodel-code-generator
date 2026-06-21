"""Build the release benchmark documentation page and SVG chart.

Usage:
    python scripts/build_release_benchmark_docs.py
    python scripts/build_release_benchmark_docs.py --check
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.release_benchmark_errors import summarize_benchmark_error
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from release_benchmark_errors import summarize_benchmark_error

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "docs" / "data" / "release-benchmarks.json"
DOCS_PATH = ROOT / "docs" / "performance-benchmarks.md"
SVG_PATH = ROOT / "docs" / "assets" / "benchmarks" / "release-benchmarks.svg"

SVG_WIDTH = 980
SVG_HEIGHT = 640
PLOT_LEFT = 86
PLOT_TOP = 116
PLOT_WIDTH = 760
PLOT_HEIGHT = 360
GRID_LINES = 4
VERSION_TICK_COUNT = 10
POINT_RADIUS = 3
STATUS_OK = "ok"
EMPTY_CELL = "-"
MILLISECONDS_PER_SECOND = 1000
WHOLE_MS_THRESHOLD = 100
TENTH_MS_THRESHOLD = 10
SAME_SPEED_TOLERANCE = 0.005
FORMATTER_ORDER = ("default", "builtin", "ruff")
CASE_ORDER = ("small", "large")
SERIES_COLORS = (
    "#6b7280",
    "#2563eb",
    "#16a34a",
    "#9333ea",
    "#ea580c",
    "#0891b2",
    "#be123c",
    "#4d7c0f",
)


@dataclass(frozen=True, slots=True)
class BenchmarkEntry:
    """One release benchmark result row."""

    version: str
    python_version: str
    os: str
    input_type: str
    case: str
    formatter: str
    runs: int
    median_ms: float | None
    min_ms: float | None
    max_ms: float | None
    stdev_ms: float | None
    status: str
    command: str
    error: str


@dataclass(frozen=True, slots=True)
class BenchmarkData:
    """Release benchmark dataset loaded from JSON."""

    schema_version: int
    metadata: dict[str, Any]
    entries: tuple[BenchmarkEntry, ...]


@dataclass(frozen=True, slots=True)
class GeneratedDoc:
    """Generated file content."""

    path: Path
    content: str


@dataclass(frozen=True, slots=True)
class SvgTextStyle:
    """SVG text rendering attributes."""

    size: int = 12
    anchor: str = "start"
    weight: str = "400"


DEFAULT_TEXT_STYLE = SvgTextStyle()
TITLE_TEXT_STYLE = SvgTextStyle(size=22, weight="700")
EMPTY_TITLE_TEXT_STYLE = SvgTextStyle(size=22, anchor="middle")
EMPTY_NOTE_TEXT_STYLE = SvgTextStyle(size=14, anchor="middle")
MUTED_TEXT_STYLE = SvgTextStyle(size=13)
TICK_TEXT_STYLE = SvgTextStyle(size=11)
Y_AXIS_TICK_TEXT_STYLE = SvgTextStyle(size=11, anchor="end")
X_AXIS_TICK_TEXT_STYLE = SvgTextStyle(size=11, anchor="middle")


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _integer(value: object, *, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return default


def _float(value: object) -> float | None:
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _entry_from_raw(raw: object, *, index: int) -> BenchmarkEntry:
    if not isinstance(raw, dict):
        msg = f"Benchmark entry #{index} must be an object"
        raise TypeError(msg)
    if not (version := _string(raw.get("version")).strip()):
        msg = f"Benchmark entry #{index} is missing version"
        raise ValueError(msg)
    if not (input_type := _string(raw.get("input_type")).strip()):
        msg = f"Benchmark entry #{index} is missing input_type"
        raise ValueError(msg)
    if not (formatter := _string(raw.get("formatter")).strip()):
        msg = f"Benchmark entry #{index} is missing formatter"
        raise ValueError(msg)

    status = _string(raw.get("status")).strip() or STATUS_OK
    return BenchmarkEntry(
        version=version,
        python_version=_string(raw.get("python_version")).strip(),
        os=_string(raw.get("os")).strip(),
        input_type=input_type,
        case=_string(raw.get("case")).strip() or "default",
        formatter=formatter,
        runs=_integer(raw.get("runs")),
        median_ms=_float(raw.get("median_ms")),
        min_ms=_float(raw.get("min_ms")),
        max_ms=_float(raw.get("max_ms")),
        stdev_ms=_float(raw.get("stdev_ms")),
        status=status,
        command=_string(raw.get("command")).strip(),
        error=_string(raw.get("error")).strip(),
    )


def load_benchmark_data(path: Path = DATA_PATH) -> BenchmarkData:
    """Load release benchmark JSON data."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Benchmark data in {path} must be a JSON object"
        raise TypeError(msg)
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        msg = f"Benchmark data in {path} must contain an entries list"
        raise TypeError(msg)
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return BenchmarkData(
        schema_version=_integer(payload.get("schema_version"), default=1),
        metadata=metadata,
        entries=tuple(_entry_from_raw(raw, index=index) for index, raw in enumerate(raw_entries, start=1)),
    )


def _version_sort_key(version: str) -> tuple[int, int, int, int, str]:
    numbers: list[int] = []
    suffix_parts: list[str] = []
    for token in re.split(r"[.\-+_]", version.removeprefix("v")):
        if token.isdecimal():
            numbers.append(int(token))
        elif token:
            suffix_parts.append(token)
    numbers.extend([0] * 4)
    return numbers[0], numbers[1], numbers[2], numbers[3], ".".join(suffix_parts)


def _sorted_entries(entries: tuple[BenchmarkEntry, ...]) -> list[BenchmarkEntry]:
    return sorted(
        entries,
        key=lambda entry: (
            _version_sort_key(entry.version),
            entry.input_type,
            entry.case,
            entry.formatter,
        ),
    )


def _formatter_sort_key(formatter: str) -> tuple[int, str]:
    if formatter in FORMATTER_ORDER:
        return FORMATTER_ORDER.index(formatter), formatter
    return len(FORMATTER_ORDER), formatter


def _case_sort_key(case: str) -> tuple[int, str]:
    if case in CASE_ORDER:
        return CASE_ORDER.index(case), case
    return len(CASE_ORDER), case


def _scenario_sort_key(entry: BenchmarkEntry) -> tuple[str, str]:
    return entry.input_type, entry.case


def _scenario_label(input_type: str, case: str) -> str:
    return f"{case.title()} / {_input_label(input_type)}"


def _input_label(input_type: str) -> str:
    label = input_type
    match input_type:
        case "openapi":
            label = "OpenAPI"
        case "jsonschema":
            label = "JSON Schema"
        case _:
            pass
    return label


def _formatter_label(formatter: str) -> str:
    label = formatter
    match formatter:
        case "default":
            label = "Default"
        case "builtin":
            label = "Built-in"
        case "ruff":
            label = "Ruff"
        case _:
            pass
    return label


def _status_label(entry: BenchmarkEntry) -> str:
    prefix = entry.status or "Unknown"
    match entry.status:
        case "ok":
            prefix = "OK"
        case "unsupported":
            prefix = "Unsupported"
        case "failed":
            prefix = "Failed"
        case _:
            pass
    if entry.status == STATUS_OK:
        return prefix
    if not entry.error:
        return prefix
    note = summarize_benchmark_error(status=entry.status, formatter=entry.formatter, error=entry.error)
    return f"{prefix}: {note}"


def _format_ms(value: float | None) -> str:
    if value is None:
        return EMPTY_CELL
    formatted = f"{value:.2f}ms"
    match value:
        case value if value >= MILLISECONDS_PER_SECOND:
            formatted = f"{value / MILLISECONDS_PER_SECOND:.2f}s"
        case value if value >= WHOLE_MS_THRESHOLD:
            formatted = f"{value:.0f}ms"
        case value if value >= TENTH_MS_THRESHOLD:
            formatted = f"{value:.1f}ms"
        case _:
            pass
    return formatted


def _latest_version(entries: tuple[BenchmarkEntry, ...]) -> str:
    versions = sorted({entry.version for entry in entries}, key=_version_sort_key)
    return versions[-1] if versions else ""


def _entries_by_scenario_and_formatter(
    entries: tuple[BenchmarkEntry, ...],
) -> dict[tuple[str, str], dict[str, BenchmarkEntry]]:
    grouped: dict[tuple[str, str], dict[str, BenchmarkEntry]] = {}
    for entry in _sorted_entries(entries):
        grouped.setdefault((entry.input_type, entry.case), {})[entry.formatter] = entry
    return grouped


def _cases(entries: tuple[BenchmarkEntry, ...]) -> list[str]:
    return sorted({entry.case for entry in entries}, key=_case_sort_key)


def _ratio_label(ratio: float) -> str:
    if abs(ratio - 1) <= SAME_SPEED_TOLERANCE:
        return "same speed"
    if ratio > 1:
        return f"{ratio:.2f}x faster"
    return f"{1 / ratio:.2f}x slower"


def _speed_label(entry: BenchmarkEntry, baseline: BenchmarkEntry | None) -> str:
    if (
        baseline is None
        or baseline.median_ms is None
        or entry.median_ms is None
        or baseline.median_ms <= 0
        or entry.median_ms <= 0
    ):
        return ""
    return _ratio_label(baseline.median_ms / entry.median_ms)


def _relative_speed_cell(entry: BenchmarkEntry, baseline: BenchmarkEntry | None) -> str:
    if entry.status != STATUS_OK:
        return EMPTY_CELL
    if entry.formatter == "default":
        return "baseline"
    return _speed_label(entry, baseline) or EMPTY_CELL


def _range_cell(entry: BenchmarkEntry) -> str:
    if entry.status != STATUS_OK:
        return EMPTY_CELL
    return f"{_format_ms(entry.min_ms)}-{_format_ms(entry.max_ms)}"


def _markdown_cell(value: object) -> str:
    text = str(value).replace("\n", "<br>")
    return text.replace("|", "\\|")


def _render_case_results_table(entries: tuple[BenchmarkEntry, ...], *, case: str, include_version: bool) -> str:
    headers = (
        ("Version", "Input", "Formatter", "Median", "vs Default", "Status")
        if include_version
        else ("Input", "Formatter", "Median", "vs Default", "Range", "Status")
    )
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    case_entries = tuple(entry for entry in entries if entry.case == case)
    for version in sorted({entry.version for entry in case_entries}, key=_version_sort_key):
        version_entries = tuple(entry for entry in case_entries if entry.version == version)
        for (input_type, _case), formatter_entries in _entries_by_scenario_and_formatter(version_entries).items():
            baseline = formatter_entries.get("default")
            for formatter in sorted(formatter_entries, key=_formatter_sort_key):
                entry = formatter_entries[formatter]
                values = [
                    _input_label(input_type),
                    _formatter_label(entry.formatter),
                    _format_ms(entry.median_ms),
                    _relative_speed_cell(entry, baseline),
                    _status_label(entry),
                ]
                if include_version:
                    values.insert(0, version)
                else:
                    values.insert(4, _range_cell(entry))
                lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    return "\n".join(lines)


def _indent_block(text: str) -> str:
    return "\n".join(f"    {line}" if line else "" for line in text.splitlines())


def _render_case_tabs(entries: tuple[BenchmarkEntry, ...], *, include_version: bool) -> str:
    blocks: list[str] = []
    for case in _cases(entries):
        blocks.extend((
            f'=== "{case.title()}"',
            "",
            _indent_block(_render_case_results_table(entries, case=case, include_version=include_version)),
            "",
        ))
    return "\n".join(blocks).rstrip()


def _scenarios(entries: tuple[BenchmarkEntry, ...]) -> list[tuple[str, str]]:
    return sorted(
        {(entry.input_type, entry.case) for entry in entries},
        key=lambda scenario: (_case_sort_key(scenario[1]), scenario[0]),
    )


def _scenario_svg_filename(input_type: str, case: str, *, index: int) -> str:
    if index == 0:
        return "release-benchmarks.svg"
    return f"release-benchmarks-{case}-{input_type}.svg"


def _scenario_svg_path(svg_path: Path, input_type: str, case: str, *, index: int) -> Path:
    return svg_path.with_name(_scenario_svg_filename(input_type, case, index=index))


def _scenario_svg_relative_path(input_type: str, case: str, *, index: int) -> str:
    return f"assets/benchmarks/{_scenario_svg_filename(input_type, case, index=index)}"


def _render_chart_tabs(entries: tuple[BenchmarkEntry, ...]) -> str:
    blocks: list[str] = []
    for index, (input_type, case) in enumerate(_scenarios(entries)):
        label = _scenario_label(input_type, case)
        blocks.extend((
            f'=== "{label}"',
            "",
            _indent_block(
                f"![{label} release benchmark trend]({_scenario_svg_relative_path(input_type, case, index=index)})"
                "{ align=center }"
            ),
            "",
        ))
    return "\n".join(blocks).rstrip()


def _formatter_history_cell(entry: BenchmarkEntry | None, baseline: BenchmarkEntry | None) -> str:
    if entry is None:
        return EMPTY_CELL
    if entry.status != STATUS_OK:
        return _status_label(entry)
    if entry.formatter == "default":
        return _format_ms(entry.median_ms)
    if speed := _speed_label(entry, baseline):
        return f"{_format_ms(entry.median_ms)} ({speed})"
    return _format_ms(entry.median_ms)


def _render_scenario_history_table(entries: tuple[BenchmarkEntry, ...], *, input_type: str, case: str) -> str:
    headers = ("Version", *(_formatter_label(formatter) for formatter in FORMATTER_ORDER))
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    scenario_entries = tuple(entry for entry in entries if entry.input_type == input_type and entry.case == case)
    for version in sorted({entry.version for entry in scenario_entries}, key=_version_sort_key):
        formatter_entries = {entry.formatter: entry for entry in scenario_entries if entry.version == version}
        baseline = formatter_entries.get("default")
        values = [
            version,
            *(_formatter_history_cell(formatter_entries.get(formatter), baseline) for formatter in FORMATTER_ORDER),
        ]
        lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    return "\n".join(lines)


def _render_scenario_history_tabs(entries: tuple[BenchmarkEntry, ...]) -> str:
    blocks: list[str] = []
    for input_type, case in _scenarios(entries):
        blocks.extend((
            f'=== "{_scenario_label(input_type, case)}"',
            "",
            _indent_block(_render_scenario_history_table(entries, input_type=input_type, case=case)),
            "",
        ))
    return "\n".join(blocks).rstrip()


def _metadata_value(data: BenchmarkData, key: str) -> str:
    return _string(data.metadata.get(key)).strip() or EMPTY_CELL


def _metadata_int(data: BenchmarkData, key: str) -> int | None:
    value = _metadata_value(data, key)
    return int(value) if value.isdecimal() else None


def _format_count(value: int | None) -> str:
    if value is None:
        return EMPTY_CELL
    return f"{value:,}"


def _selected_version_count(data: BenchmarkData) -> int:
    selected_versions = _metadata_value(data, "selected_versions")
    if selected_versions == EMPTY_CELL:
        return len({entry.version for entry in data.entries})
    return len([version for version in selected_versions.split(",") if version])


def _collection_metadata_lines(data: BenchmarkData) -> list[str]:
    return [
        "## Collection Policy",
        "",
        "- The benchmark workflow runs on `ubuntu-24.04`.",
        "- The Python version is the workflow input, defaulting to the latest configured CI Python.",
        "- Release packages are installed from PyPI in isolated virtual environments.",
        "- Input coverage currently focuses on OpenAPI and JSON Schema.",
        "- Historical backfills are produced by the `Release Benchmarks` workflow and committed after review.",
        "",
        "## Latest Dataset",
        "",
        f"- Schema version: `{data.schema_version}`",
        f"- Generated at: `{_metadata_value(data, 'generated_at')}`",
        f"- Source workflow: `{_metadata_value(data, 'workflow')}`",
        f"- Benchmark runs per case: `{_metadata_value(data, 'runs_per_case')}`",
        f"- Version selection: `{_metadata_value(data, 'selection_strategy')}`",
        f"- Selected versions: `{_selected_version_count(data)}`",
        f"- Download source: `{_metadata_value(data, 'download_source')}`",
        f"- Download window: `{_metadata_value(data, 'download_window_days')}` days",
        f"- Downloads in window: `{_format_count(_metadata_int(data, 'download_window_total'))}`",
        f"- PyPIStats last month: `{_format_count(_metadata_int(data, 'pypistats_last_month'))}`",
        "",
    ]


def render_release_benchmark_markdown(data: BenchmarkData) -> str:
    """Render the release benchmark documentation page."""
    lines = [
        "# Performance Benchmarks",
        "",
        "<!-- Generated by scripts/build_release_benchmark_docs.py. Do not edit manually. -->",
        "",
        (
            "This page tracks datamodel-code-generator release benchmark results collected on GitHub Actions. "
            "The data covers only datamodel-code-generator releases and uses Ubuntu runners so release-to-release "
            "changes can be compared without mixing in third-party generator results. Automatic backfills select "
            "versions from PyPI download-by-version data when that public dataset is available."
        ),
        "",
    ]

    if not data.entries:
        lines.extend([
            "## Historical Trends",
            "",
            "No release benchmark data has been committed yet.",
            "",
            (
                "After this workflow is available on `main`, run it with `workflow_dispatch` and commit the generated "
                "`docs/data/release-benchmarks.json`, Markdown, and SVG artifacts."
            ),
            "",
            *_collection_metadata_lines(data),
        ])
        return "\n".join(lines)

    latest_version = _latest_version(data.entries)
    latest_entries = tuple(entry for entry in data.entries if entry.version == latest_version)
    lines.extend([
        "## Historical Trends",
        "",
        (
            "Each chart plots median generation time by release version for one benchmark scenario. "
            "Formatter lines are included for context; missing or unsupported formatter results are skipped."
        ),
        "",
        _render_chart_tabs(data.entries),
        "",
        *_collection_metadata_lines(data),
        "## Latest Release Summary",
        "",
        (
            "Results below are medians. Built-in and Ruff ratios are relative to the Default formatter "
            "for the same scenario."
        ),
        "",
        f"### {latest_version}",
        "",
        _render_case_tabs(latest_entries, include_version=False),
        "",
        "## Historical Results",
        "",
        (
            "Rows are release versions. Formatter cells show median generation time; non-default cells include "
            "the speed relative to Default when both results are available."
        ),
        "",
        _render_scenario_history_tabs(data.entries),
        "",
    ])
    return "\n".join(lines)


def _svg_text(x: float, y: float, text: str, style: SvgTextStyle = DEFAULT_TEXT_STYLE) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{style.size}" text-anchor="{style.anchor}" '
        f'font-weight="{style.weight}">{html.escape(text)}</text>'
    )


def _scale(value: float, *, source_min: float, source_max: float, target_min: float, target_max: float) -> float:
    if source_max == source_min:
        return (target_min + target_max) / 2
    ratio = (value - source_min) / (source_max - source_min)
    return target_min + ratio * (target_max - target_min)


def _chart_entries(entries: tuple[BenchmarkEntry, ...], *, input_type: str, case: str) -> list[BenchmarkEntry]:
    return [
        entry
        for entry in _sorted_entries(entries)
        if (
            entry.input_type == input_type
            and entry.case == case
            and entry.status == STATUS_OK
            and entry.median_ms is not None
        )
    ]


def _render_empty_svg() -> str:
    body = "\n".join((
        _svg_text(
            SVG_WIDTH / 2,
            SVG_HEIGHT / 2 - 10,
            "No release benchmark data committed yet",
            EMPTY_TITLE_TEXT_STYLE,
        ),
        _svg_text(
            SVG_WIDTH / 2,
            SVG_HEIGHT / 2 + 20,
            "Run the Release Benchmarks workflow to generate the initial historical dataset.",
            EMPTY_NOTE_TEXT_STYLE,
        ),
    ))
    return _wrap_svg(
        body,
        desc="No datamodel-code-generator release benchmark data has been committed yet.",
    )


def _wrap_svg(body: str, *, desc: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" \
viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">datamodel-code-generator release benchmarks</title>
  <desc id="desc">{html.escape(desc)}</desc>
  <style>
    text {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", \
sans-serif; fill: #111827; }}
    .muted {{ fill: #6b7280; }}
    .axis {{ stroke: #374151; stroke-width: 1.2; }}
    .grid {{ stroke: #d1d5db; stroke-width: 1; stroke-dasharray: 4 5; }}
    .panel {{ fill: #ffffff; stroke: #e5e7eb; stroke-width: 1; }}
  </style>
  <rect width="100%" height="100%" fill="#ffffff"/>
  <rect class="panel" x="20" y="20" width="{SVG_WIDTH - 40}" height="{SVG_HEIGHT - 40}" rx="8"/>
{body}
</svg>
"""


def _line_points(entries: list[BenchmarkEntry], *, formatter: str, versions: list[str], y_max: float) -> list[str]:
    by_version = {entry.version: entry for entry in entries if entry.formatter == formatter}
    points: list[str] = []
    for index, version in enumerate(versions):
        entry = by_version.get(version)
        if entry is None or entry.median_ms is None:
            continue
        x = _scale(
            index,
            source_min=0,
            source_max=max(len(versions) - 1, 1),
            target_min=PLOT_LEFT,
            target_max=PLOT_LEFT + PLOT_WIDTH,
        )
        y = _scale(
            entry.median_ms,
            source_min=0,
            source_max=y_max,
            target_min=PLOT_TOP + PLOT_HEIGHT,
            target_max=PLOT_TOP,
        )
        points.append(f"{x:.1f},{y:.1f}")
    return points


def _version_tick_indexes(version_count: int) -> list[int]:
    if version_count <= 1:
        return [0]
    step = max(1, round(version_count / VERSION_TICK_COUNT))
    indexes = list(range(0, version_count, step))
    if indexes[-1] != version_count - 1:
        indexes.append(version_count - 1)
    return indexes


def render_release_benchmark_svg(data: BenchmarkData, *, input_type: str = "", case: str = "") -> str:
    """Render a static SVG historical trend chart for one benchmark scenario."""
    if not input_type or not case:
        scenarios = _scenarios(data.entries)
        if not scenarios:
            return _render_empty_svg()
        input_type, case = scenarios[0]

    entries = _chart_entries(data.entries, input_type=input_type, case=case)
    if not entries:
        return _render_empty_svg()

    scenario_label = _scenario_label(input_type, case)
    versions = sorted(
        {entry.version for entry in data.entries if entry.input_type == input_type and entry.case == case},
        key=_version_sort_key,
    )
    max_ms = max(entry.median_ms or 0 for entry in entries)
    y_max = max_ms * 1.15 if max_ms else 1
    body: list[str] = [
        _svg_text(44, 48, f"datamodel-code-generator release trend: {scenario_label}", TITLE_TEXT_STYLE),
        _svg_text(44, 74, "Median generation time by release version. Lower is faster.", MUTED_TEXT_STYLE),
    ]

    for index in range(GRID_LINES + 1):
        value = y_max * index / GRID_LINES
        y = _scale(value, source_min=0, source_max=y_max, target_min=PLOT_TOP + PLOT_HEIGHT, target_max=PLOT_TOP)
        body.extend((
            f'<line class="grid" x1="{PLOT_LEFT}" y1="{y:.1f}" x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{y:.1f}"/>',
            _svg_text(PLOT_LEFT - 12, y + 4, _format_ms(value), Y_AXIS_TICK_TEXT_STYLE),
        ))

    body.extend((
        f'<line class="axis" x1="{PLOT_LEFT}" y1="{PLOT_TOP}" x2="{PLOT_LEFT}" y2="{PLOT_TOP + PLOT_HEIGHT}"/>',
        (
            f'<line class="axis" x1="{PLOT_LEFT}" y1="{PLOT_TOP + PLOT_HEIGHT}" '
            f'x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{PLOT_TOP + PLOT_HEIGHT}"/>'
        ),
    ))

    for index in _version_tick_indexes(len(versions)):
        version = versions[index]
        x = _scale(
            index,
            source_min=0,
            source_max=max(len(versions) - 1, 1),
            target_min=PLOT_LEFT,
            target_max=PLOT_LEFT + PLOT_WIDTH,
        )
        body.extend((
            f'<line class="grid" x1="{x:.1f}" y1="{PLOT_TOP}" x2="{x:.1f}" y2="{PLOT_TOP + PLOT_HEIGHT}"/>',
            _svg_text(x, PLOT_TOP + PLOT_HEIGHT + 24, version, X_AXIS_TICK_TEXT_STYLE),
        ))

    legend_x = PLOT_LEFT
    for index, formatter in enumerate(FORMATTER_ORDER):
        color = SERIES_COLORS[index % len(SERIES_COLORS)]
        x = legend_x + index * 132
        body.extend((
            f'<line x1="{x}" y1="92" x2="{x + 24}" y2="92" stroke="{color}" stroke-width="2.6"/>',
            f'<circle cx="{x + 12}" cy="92" r="{POINT_RADIUS}" fill="{color}"/>',
            _svg_text(x + 32, 96, _formatter_label(formatter), TICK_TEXT_STYLE),
        ))

    for index, formatter in enumerate(FORMATTER_ORDER):
        points = _line_points(entries, formatter=formatter, versions=versions, y_max=y_max)
        if not points:
            continue
        color = SERIES_COLORS[index % len(SERIES_COLORS)]
        body.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.4" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for point in points:
            x, y = point.split(",", maxsplit=1)
            body.append(f'<circle cx="{x}" cy="{y}" r="{POINT_RADIUS}" fill="{color}"/>')

    body.extend((
        _svg_text(PLOT_LEFT + PLOT_WIDTH / 2, PLOT_TOP + PLOT_HEIGHT + 54, "Release version", X_AXIS_TICK_TEXT_STYLE),
        _svg_text(44, PLOT_TOP - 16, "Median", TICK_TEXT_STYLE),
    ))

    return _wrap_svg(
        "\n".join(body),
        desc=f"Historical median generation time by release version for {scenario_label}.",
    )


def _generated_docs(data_path: Path, docs_path: Path, svg_path: Path) -> tuple[GeneratedDoc, ...]:
    data = load_benchmark_data(data_path)
    docs = [GeneratedDoc(docs_path, render_release_benchmark_markdown(data).rstrip() + "\n")]
    for index, (input_type, case) in enumerate(_scenarios(data.entries)):
        docs.append(
            GeneratedDoc(
                _scenario_svg_path(svg_path, input_type, case, index=index),
                render_release_benchmark_svg(data, input_type=input_type, case=case),
            )
        )
    if len(docs) == 1:
        docs.append(GeneratedDoc(svg_path, render_release_benchmark_svg(data)))
    return tuple(docs)


def _doc_is_current(doc: GeneratedDoc) -> bool:
    return doc.path.exists() and doc.path.read_text(encoding="utf-8") == doc.content


def build_docs(
    *,
    check: bool,
    data_path: Path = DATA_PATH,
    docs_path: Path = DOCS_PATH,
    svg_path: Path = SVG_PATH,
) -> int:
    """Generate or check release benchmark documentation outputs."""
    docs = _generated_docs(data_path, docs_path, svg_path)
    if check:
        if not (out_of_date := tuple(doc.path for doc in docs if not _doc_is_current(doc))):
            print("Release benchmark docs are up to date.")
            return 0
        for path in out_of_date:
            print(f"Release benchmark docs are out of date: {path.relative_to(ROOT)}", file=sys.stderr)
        print("Run 'python scripts/build_release_benchmark_docs.py' to update.", file=sys.stderr)
        return 1

    for doc in docs:
        doc.path.parent.mkdir(parents=True, exist_ok=True)
        doc.path.write_text(doc.content, encoding="utf-8")
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Build release benchmark documentation and SVG chart")
    parser.add_argument("--check", action="store_true", help="Check whether generated benchmark docs are up to date")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="Benchmark JSON data path")
    parser.add_argument("--docs", type=Path, default=DOCS_PATH, help="Markdown output path")
    parser.add_argument("--svg", type=Path, default=SVG_PATH, help="SVG chart output path")
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    args = parse_args()
    return build_docs(check=args.check, data_path=args.data, docs_path=args.docs, svg_path=args.svg)


if __name__ == "__main__":
    sys.exit(main())
