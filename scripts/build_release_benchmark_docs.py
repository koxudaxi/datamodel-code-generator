"""Build the release benchmark documentation page.

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.release_benchmark_errors import summarize_benchmark_error
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from release_benchmark_errors import summarize_benchmark_error

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "docs" / "data" / "release-benchmarks.json"
NOTES_PATH = ROOT / "docs" / "data" / "release-benchmark-notes.json"
DOCS_PATH = ROOT / "docs" / "performance-benchmarks.md"

STATUS_OK = "ok"
EMPTY_CELL = "-"
MILLISECONDS_PER_SECOND = 1000
WHOLE_MS_THRESHOLD = 100
TENTH_MS_THRESHOLD = 10
SAME_SPEED_TOLERANCE = 0.005
FORMATTER_ORDER = ("default", "builtin", "ruff")
CASE_ORDER = ("small", "large")


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
class BenchmarkNote:
    """One human-authored release benchmark note."""

    version: str
    summary: str
    details: str
    input_type: str
    case: str


@dataclass(frozen=True, slots=True)
class BenchmarkData:
    """Release benchmark dataset loaded from JSON."""

    schema_version: int
    metadata: dict[str, Any]
    entries: tuple[BenchmarkEntry, ...]
    notes: tuple[BenchmarkNote, ...]


@dataclass(frozen=True, slots=True)
class GeneratedDoc:
    """Generated file content."""

    path: Path
    content: str


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


def _note_from_raw(raw: object, *, index: int) -> BenchmarkNote:
    if not isinstance(raw, dict):
        msg = f"Benchmark note #{index} must be an object"
        raise TypeError(msg)
    if not (version := _string(raw.get("version")).strip()):
        msg = f"Benchmark note #{index} is missing version"
        raise ValueError(msg)
    if not (summary := _string(raw.get("summary")).strip()):
        msg = f"Benchmark note #{index} is missing summary"
        raise ValueError(msg)
    return BenchmarkNote(
        version=version,
        summary=summary,
        details=_string(raw.get("details")).strip(),
        input_type=_string(raw.get("input_type")).strip(),
        case=_string(raw.get("case")).strip(),
    )


def load_benchmark_notes(path: Path | None = NOTES_PATH) -> tuple[BenchmarkNote, ...]:
    """Load optional human-authored release benchmark notes."""
    if path is None or not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Benchmark notes in {path} must be a JSON object"
        raise TypeError(msg)
    raw_notes = payload.get("notes", [])
    if not isinstance(raw_notes, list):
        msg = f"Benchmark notes in {path} must contain a notes list"
        raise TypeError(msg)
    return tuple(_note_from_raw(raw, index=index) for index, raw in enumerate(raw_notes, start=1))


def load_benchmark_data(path: Path = DATA_PATH, *, notes_path: Path | None = NOTES_PATH) -> BenchmarkData:
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
        notes=load_benchmark_notes(notes_path),
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


def _release_dates(data: BenchmarkData) -> dict[str, str]:
    if not isinstance(raw_dates := data.metadata.get("release_dates"), dict):
        return {}
    return {
        version: uploaded_at
        for version, uploaded_at in raw_dates.items()
        if isinstance(version, str) and isinstance(uploaded_at, str)
    }


def _parse_utc_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _release_date_cell(release_dates: dict[str, str], version: str) -> str:
    if not (uploaded_at := release_dates.get(version, "")):
        return EMPTY_CELL
    if parsed := _parse_utc_datetime(uploaded_at):
        return parsed.strftime("%Y-%m-%d %H:%M UTC")
    return uploaded_at


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


def _note_applies(note: BenchmarkNote, *, input_type: str, case: str) -> bool:
    if note.input_type and note.input_type != input_type:
        return False
    return not note.case or note.case == case


def _notes_by_version(
    notes: tuple[BenchmarkNote, ...],
    *,
    input_type: str,
    case: str,
) -> dict[str, tuple[BenchmarkNote, ...]]:
    notes_by_version: dict[str, list[BenchmarkNote]] = {}
    for note in notes:
        if _note_applies(note, input_type=input_type, case=case):
            notes_by_version.setdefault(note.version, []).append(note)
    return {version: tuple(version_notes) for version, version_notes in notes_by_version.items()}


def _visible_notes(data: BenchmarkData) -> tuple[BenchmarkNote, ...]:
    notes = tuple(
        note
        for note in data.notes
        if any(
            entry.version == note.version and _note_applies(note, input_type=entry.input_type, case=entry.case)
            for entry in data.entries
        )
    )
    return tuple(sorted(notes, key=lambda note: (*_version_sort_key(note.version), note.input_type, note.case)))


def _version_cell(version: str, notes_by_version: dict[str, tuple[BenchmarkNote, ...]]) -> str:
    if notes := notes_by_version.get(version):
        title = html.escape(" ".join(note.summary for note in notes), quote=True)
        label = html.escape(version)
        return f'<span class="release-benchmark-version-note" title="{title}">{label} *</span>'
    return version


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


def _render_chart_tabs(entries: tuple[BenchmarkEntry, ...]) -> str:
    blocks: list[str] = []
    for input_type, case in _scenarios(entries):
        label = _scenario_label(input_type, case)
        blocks.extend((
            f'=== "{label}"',
            "",
            _indent_block(
                "\n".join((
                    (
                        f'<span class="release-benchmark-chart" data-release-benchmark-chart '
                        f'data-input-type="{input_type}" data-case="{case}" '
                        f'aria-label="{label} release benchmark trend">'
                    ),
                    '  <canvas role="img" aria-label="Median generation time by release version"></canvas>',
                    '  <span class="release-benchmark-chart__legend" aria-hidden="true"></span>',
                    '  <span class="release-benchmark-chart__status" role="status">Loading benchmark chart...</span>',
                    '  <span class="release-benchmark-chart__tooltip" role="status" hidden></span>',
                    "  <noscript>See the historical results table below for benchmark data.</noscript>",
                    "</span>",
                ))
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


def _render_scenario_history_table(
    entries: tuple[BenchmarkEntry, ...],
    *,
    input_type: str,
    case: str,
    release_dates: dict[str, str],
    notes_by_version: dict[str, tuple[BenchmarkNote, ...]] | None = None,
) -> str:
    notes_by_version = notes_by_version or {}
    headers = ("Version", "Released", *(_formatter_label(formatter) for formatter in FORMATTER_ORDER))
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    scenario_entries = tuple(entry for entry in entries if entry.input_type == input_type and entry.case == case)
    for version in sorted({entry.version for entry in scenario_entries}, key=_version_sort_key, reverse=True):
        formatter_entries = {entry.formatter: entry for entry in scenario_entries if entry.version == version}
        baseline = formatter_entries.get("default")
        values = [
            _version_cell(version, notes_by_version),
            _release_date_cell(release_dates, version),
            *(_formatter_history_cell(formatter_entries.get(formatter), baseline) for formatter in FORMATTER_ORDER),
        ]
        lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    return "\n".join(lines)


def _render_scenario_history_tabs(
    entries: tuple[BenchmarkEntry, ...],
    *,
    release_dates: dict[str, str],
    notes: tuple[BenchmarkNote, ...] = (),
) -> str:
    blocks: list[str] = []
    for input_type, case in _scenarios(entries):
        blocks.extend((
            f'=== "{_scenario_label(input_type, case)}"',
            "",
            _indent_block(
                _render_scenario_history_table(
                    entries,
                    input_type=input_type,
                    case=case,
                    release_dates=release_dates,
                    notes_by_version=_notes_by_version(notes, input_type=input_type, case=case),
                )
            ),
            "",
        ))
    return "\n".join(blocks).rstrip()


def _note_scope_label(note: BenchmarkNote) -> str:
    match note.input_type, note.case:
        case "", "":
            return ""
        case input_type, "":
            return _input_label(input_type)
        case "", case_name:
            return case_name.title()
        case input_type, case_name:
            return _scenario_label(input_type, case_name)
        case _:
            return ""


def _render_benchmark_notes(data: BenchmarkData) -> str:
    notes = _visible_notes(data)
    if not notes:
        return ""
    lines = [
        "## Benchmark Notes",
        "",
        "Version markers in the charts and historical tables point to these benchmark interpretation notes.",
        "",
    ]
    for note in notes:
        body = note.summary
        if note.details:
            body = f"{body} {note.details}"
        scope = f" ({scope_label})" if (scope_label := _note_scope_label(note)) else ""
        lines.append(f"- `{note.version}`{scope}: {_markdown_cell(body)}")
    return "\n".join(lines)


def _metadata_value(data: BenchmarkData, key: str) -> str:
    return _string(data.metadata.get(key)).strip() or EMPTY_CELL


def _metadata_int(data: BenchmarkData, key: str) -> int | None:
    value = _metadata_value(data, key)
    return int(value) if value.isdecimal() else None


def _format_count(value: int | None) -> str:
    if value is None:
        return EMPTY_CELL
    return f"{value:,}"


def _python_versions(data: BenchmarkData) -> list[str]:
    versions = sorted({entry.python_version for entry in data.entries if entry.python_version})
    if versions:
        return versions
    if metadata_version := _metadata_value(data, "python_version"):
        return [] if metadata_version == EMPTY_CELL else [metadata_version]
    return []


def _python_versions_label(data: BenchmarkData) -> str:
    if versions := _python_versions(data):
        return ", ".join(f"`{version}`" for version in versions)
    return EMPTY_CELL


def _compatibility_backfill_note(data: BenchmarkData) -> str:
    note = _metadata_value(data, "compatibility_backfill")
    if note == EMPTY_CELL:
        return ""
    return note


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
        f"- Primary Python version: `{_metadata_value(data, 'python_version')}`",
        f"- Entry Python versions: {_python_versions_label(data)}",
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
                "`docs/data/release-benchmarks.json` and Markdown artifact."
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
            "Formatter lines are included for context; missing or unsupported formatter results are skipped. "
            "Marked versions have benchmark notes below."
        ),
        "",
    ])
    if backfill_note := _compatibility_backfill_note(data):
        lines.extend([
            f"Compatibility backfill: {backfill_note}",
            "",
        ])
    lines.extend([
        _render_chart_tabs(data.entries),
        "",
    ])
    if notes_block := _render_benchmark_notes(data):
        lines.extend([
            notes_block,
            "",
        ])
    lines.extend([
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
            "Rows are release versions, newest first. Released is the PyPI upload timestamp in UTC. Formatter "
            "cells show median generation time; non-default cells include the speed relative to Default when both "
            "results are available. Version cells marked with `*` have benchmark notes above."
        ),
        "",
        _render_scenario_history_tabs(data.entries, release_dates=_release_dates(data), notes=_visible_notes(data)),
        "",
    ])
    return "\n".join(lines)


def _generated_docs(data_path: Path, docs_path: Path, notes_path: Path | None) -> tuple[GeneratedDoc, ...]:
    data = load_benchmark_data(data_path, notes_path=notes_path)
    return (GeneratedDoc(docs_path, render_release_benchmark_markdown(data).rstrip() + "\n"),)


def _doc_is_current(doc: GeneratedDoc) -> bool:
    return doc.path.exists() and doc.path.read_text(encoding="utf-8") == doc.content


def build_docs(
    *,
    check: bool,
    data_path: Path = DATA_PATH,
    notes_path: Path | None = NOTES_PATH,
    docs_path: Path = DOCS_PATH,
) -> int:
    """Generate or check release benchmark documentation outputs."""
    docs = _generated_docs(data_path, docs_path, notes_path)
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
    parser = argparse.ArgumentParser(description="Build release benchmark documentation")
    parser.add_argument("--check", action="store_true", help="Check whether generated benchmark docs are up to date")
    parser.add_argument("--data", type=Path, default=DATA_PATH, help="Benchmark JSON data path")
    parser.add_argument("--notes", type=Path, default=NOTES_PATH, help="Benchmark notes JSON data path")
    parser.add_argument("--docs", type=Path, default=DOCS_PATH, help="Markdown output path")
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    args = parse_args()
    return build_docs(check=args.check, data_path=args.data, notes_path=args.notes, docs_path=args.docs)


if __name__ == "__main__":
    sys.exit(main())
