"""Tests for release benchmark documentation generation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from scripts import build_release_benchmark_docs, select_release_benchmark_versions, update_release_benchmark_history
from scripts.collect_release_benchmarks import _failure_status, _install_spec, _run_subprocess
from scripts.release_benchmark_errors import sanitize_benchmark_error, summarize_benchmark_error
from tests.conftest import assert_output

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_release_benchmark_docs.py"
FIXTURE_DATA = ROOT / "tests" / "data" / "release_benchmarks" / "sample.json"
FIXTURE_DIR = ROOT / "tests" / "data" / "release_benchmarks"
FIXTURE_NOTES = FIXTURE_DIR / "notes.json"
EXPECTED_RELEASE_BENCHMARK_DOCS_PATH = ROOT / "tests" / "data" / "expected" / "release_benchmark_docs"


def _completed_process_output(result: subprocess.CompletedProcess[str]) -> str:
    """Format a subprocess result for stable external-file comparison."""
    return f"returncode: {result.returncode}\nstdout:\n{result.stdout}stderr:\n{result.stderr}"


def _completed_process_output_with_tmp(result: subprocess.CompletedProcess[str], tmp_path: Path) -> str:
    """Format subprocess output with a stable temporary path placeholder."""
    output = _completed_process_output(result).replace(str(tmp_path), "<tmp>")
    return output.replace("<tmp>\\", "<tmp>/")


def _raise_for_failed_process(result: subprocess.CompletedProcess[str]) -> None:
    """Surface subprocess failures before tests read expected output files."""
    if result.returncode == 0:
        return
    raise AssertionError(_completed_process_output(result))


def test_build_release_benchmark_docs_check_is_up_to_date() -> None:
    """Check that committed release benchmark docs match the committed JSON dataset."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    _raise_for_failed_process(result)
    assert_output(
        _completed_process_output(result),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "build_release_benchmark_docs_check.txt",
    )


def test_release_benchmark_renderers_use_fixture_data() -> None:
    """Render Markdown from an external benchmark data fixture."""
    data = build_release_benchmark_docs.load_benchmark_data(FIXTURE_DATA, notes_path=FIXTURE_NOTES)

    assert_output(
        "\n--- markdown ---\n" + build_release_benchmark_docs.render_release_benchmark_markdown(data),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "release_benchmark_rendered.txt",
    )


def test_release_benchmark_docs_cli_writes_expected_outputs(tmp_path: Path) -> None:
    """The CLI can render fixture-backed Markdown to a caller-selected path."""
    docs_path = tmp_path / "performance-benchmarks.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--data",
            str(FIXTURE_DATA),
            "--notes",
            str(FIXTURE_NOTES),
            "--docs",
            str(docs_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    _raise_for_failed_process(result)
    assert_output(
        _completed_process_output(result) + "docs:\n" + docs_path.read_text(encoding="utf-8"),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "release_benchmark_cli_outputs.txt",
    )


def test_release_benchmark_docs_escape_hostile_text(tmp_path: Path) -> None:
    """Hostile note and metadata text is rendered as text, not Markdown or HTML."""
    data_path = tmp_path / "hostile-release-benchmarks.json"
    notes_path = tmp_path / "hostile-release-benchmark-notes.json"
    data_path.write_text(
        json.dumps({
            "schema_version": 1,
            "metadata": {
                "generated_at": "2026-06-23T00:00:00Z",
                "workflow": "Release Benchmarks",
                "python_version": "3.14.2",
                "runs_per_case": "1",
                "selection_strategy": "explicit",
                "download_source": "fixture",
                "download_window_days": "1",
                "download_window_total": "1",
                "pypistats_last_month": "1",
                "compatibility_backfill": "<img src=x onerror=alert(1)>",
                "release_dates": {"0.64.1": "2026-06-19T00:00:00Z"},
            },
            "entries": [
                {
                    "version": "0.64.1",
                    "python_version": "3.14.2",
                    "os": "ubuntu-24.04",
                    "input_type": "openapi",
                    "case": "small",
                    "formatter": "default",
                    "runs": 1,
                    "median_ms": 12.3,
                    "min_ms": 12.0,
                    "max_ms": 12.8,
                    "stdev_ms": 0.4,
                    "status": "ok",
                    "command": "python -m datamodel_code_generator",
                    "error": "",
                }
            ],
        })
        + "\n",
        encoding="utf-8",
    )
    notes_path.write_text(
        json.dumps({
            "notes": [
                {
                    "version": "0.64.1",
                    "summary": '<img src=x onerror="alert(1)"> | note',
                    "details": "<script>alert(1)</script>",
                    "input_type": "openapi",
                    "case": "small",
                }
            ]
        })
        + "\n",
        encoding="utf-8",
    )

    data = build_release_benchmark_docs.load_benchmark_data(data_path, notes_path=notes_path)

    assert_output(
        build_release_benchmark_docs.render_release_benchmark_markdown(data),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "release_benchmark_escaped_hostile_text.txt",
    )


def test_collect_release_benchmark_cli_validation() -> None:
    """The collector rejects invalid numeric options before benchmarking."""
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "collect_release_benchmarks.py"),
            "--versions",
            "0.64.1",
            "--runs",
            "0",
            "--warmups",
            "-1",
            "--timeout",
            "0",
            "--install-retries",
            "0",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert_output(
        _completed_process_output(result),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "collect_release_benchmarks_invalid_args.txt",
    )


def test_collect_release_benchmark_failure_helpers() -> None:
    """Timeouts and old formatter argument errors are classified predictably."""
    timeout_result = _run_subprocess(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        timeout=1,
    )
    output = "\n".join((
        f"timeout_returncode: {timeout_result.returncode}",
        f"timeout_stderr: {timeout_result.stderr}",
        f"ruff_unrecognized: {_failure_status('ruff', 'error: unrecognized arguments: ruff-format')}",
        "",
    ))

    assert_output(output, EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "collect_release_benchmarks_failures.txt")


def test_collect_release_benchmark_install_specs() -> None:
    """Release versions use PyPI pins and main uses the GitHub branch ref."""
    output = "\n".join((
        f"release: {_install_spec('v0.65.0')}",
        f"main: {_install_spec('main')}",
        "",
    ))

    assert_output(output, EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "collect_release_benchmark_install_specs.txt")


def test_release_benchmark_error_helpers_redact_public_output() -> None:
    """Benchmark errors redact volatile temp paths and summarize noisy failures."""
    path_error = (
        'Traceback (most recent call last): File "/tmp/dcg-release-bench-abc123/venv/lib/python3.14/'
        'site-packages/datamodel_code_generator/__main__.py", line 1, in <module>'
    )
    output = "\n".join((
        f"sanitized: {sanitize_benchmark_error(path_error)}",
        "unsupported: "
        + summarize_benchmark_error(
            status="unsupported",
            formatter="builtin",
            error="error: argument --formatters: invalid choice: 'builtin'",
        ),
        "install: "
        + summarize_benchmark_error(
            status="failed",
            formatter="default",
            error="Using Python 3.14.2 environment at: /tmp/dcg-release-bench-abc123/venv Failed to build typed-ast",
        ),
        "traceback: " + summarize_benchmark_error(status="failed", formatter="ruff", error=path_error),
        "",
    ))

    assert_output(output, EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "release_benchmark_error_helpers.txt")


def test_select_release_benchmark_versions_cli_writes_usage_based_selection(tmp_path: Path) -> None:
    """The selector uses version download data and writes a deterministic selection artifact."""
    output_path = tmp_path / "release-benchmark-selection.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "select_release_benchmark_versions.py"),
            "--pypi-json",
            str(FIXTURE_DIR / "pypi_project.json"),
            "--clickpy-json",
            str(FIXTURE_DIR / "clickpy_versions.json"),
            "--pypistats-recent-json",
            str(FIXTURE_DIR / "pypistats_recent.json"),
            "--pypistats-overall-json",
            str(FIXTURE_DIR / "pypistats_overall.json"),
            "--history-days",
            "365",
            "--limit",
            "4",
            "--now",
            "2026-06-22T00:00:00Z",
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    _raise_for_failed_process(result)
    assert_output(
        _completed_process_output(result) + "selection:\n" + output_path.read_text(encoding="utf-8"),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "select_release_benchmark_versions_cli_outputs.txt",
    )


def test_merge_release_benchmarks_cli_writes_expected_payload(tmp_path: Path) -> None:
    """The merge CLI combines selection metadata and per-version fragments."""
    selection_path = tmp_path / "release-benchmark-selection.json"
    selector_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "select_release_benchmark_versions.py"),
            "--pypi-json",
            str(FIXTURE_DIR / "pypi_project.json"),
            "--clickpy-json",
            str(FIXTURE_DIR / "clickpy_versions.json"),
            "--pypistats-recent-json",
            str(FIXTURE_DIR / "pypistats_recent.json"),
            "--pypistats-overall-json",
            str(FIXTURE_DIR / "pypistats_overall.json"),
            "--history-days",
            "365",
            "--limit",
            "4",
            "--now",
            "2026-06-22T00:00:00Z",
            "--output",
            str(selection_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    _raise_for_failed_process(selector_result)

    output_path = tmp_path / "release-benchmarks.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "merge_release_benchmarks.py"),
            str(FIXTURE_DIR / "release_fragment_0641.json"),
            "--selection",
            str(selection_path),
            "--generated-at",
            "2026-06-22T00:00:00Z",
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        env={**os.environ, "OS": "ubuntu-24.04", "BENCHMARK_PYTHON_VERSION": "3.14.2"},
        capture_output=True,
        text=True,
        check=False,
    )

    _raise_for_failed_process(result)
    assert_output(
        _completed_process_output_with_tmp(result, tmp_path) + "merged:\n" + output_path.read_text(encoding="utf-8"),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "merge_release_benchmarks_cli_outputs.txt",
    )


def test_update_release_benchmark_history_writes_expected_payload(tmp_path: Path) -> None:
    """The release benchmark history updater merges a workflow artifact into committed data."""
    base_path = tmp_path / "base.json"
    base_payload = FIXTURE_DATA.read_text(encoding="utf-8")
    base_payload = base_payload.replace(
        '"workflow": "Release Benchmarks",',
        '"workflow": "Release Benchmarks",\n    "selection_strategy": "clickpy_downloads",',
    )
    base_path.write_text(base_payload, encoding="utf-8")
    selection_path = tmp_path / "release-benchmark-selection.json"
    selection_path.write_text(
        '{"releases": [{"version": "0.64.1", "uploaded_at": "2026-06-19T00:00:00Z"}]}\n',
        encoding="utf-8",
    )
    output_path = tmp_path / "release-benchmarks.json"
    stderr = StringIO()

    with redirect_stderr(stderr):
        returncode = update_release_benchmark_history.main([
            "--base-data",
            str(base_path),
            "--incoming-data",
            str(FIXTURE_DIR / "incoming_history_0641.json"),
            "--selection",
            str(selection_path),
            "--generated-at",
            "2026-06-23T00:00:00Z",
            "--output",
            str(output_path),
        ])

    stderr_output = stderr.getvalue().replace(str(tmp_path), "<tmp>").replace("<tmp>\\", "<tmp>/")
    assert_output(
        f"returncode: {returncode}\nstderr:\n{stderr_output}merged:\n" + output_path.read_text(encoding="utf-8"),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "update_release_benchmark_history_outputs.txt",
    )


def test_update_release_benchmark_history_empty_base_uses_incoming_metadata(tmp_path: Path) -> None:
    """A first committed benchmark history can be created from the incoming artifact alone."""
    output_path = tmp_path / "release-benchmarks.json"
    update_release_benchmark_history.merge_release_benchmark_history(
        base_data_path=tmp_path / "missing-base.json",
        incoming_data_path=FIXTURE_DIR / "incoming_history_0641.json",
        output_path=output_path,
        selection_path=FIXTURE_DIR / "pypi_project.json",
        generated_at="2026-06-23T01:00:00Z",
    )

    assert_output(
        output_path.read_text(encoding="utf-8"),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "update_release_benchmark_history_empty_base.txt",
    )


def _release_benchmark_history_error(
    path: Path,
    output_path: Path,
    *,
    incoming_data_path: Path = FIXTURE_DIR / "incoming_history_0641.json",
) -> str:
    try:
        update_release_benchmark_history.merge_release_benchmark_history(
            base_data_path=path,
            incoming_data_path=incoming_data_path,
            output_path=output_path,
        )
    except (FileNotFoundError, TypeError, ValueError) as exc:
        return f"{path.name}: {type(exc).__name__}: {exc}"
    return f"{path.name}: no error"


def _release_benchmark_selection_error(path: Path) -> str:
    try:
        result = update_release_benchmark_history._release_dates_from_selection(path)
    except ValueError as exc:
        return f"{path.name}: ValueError: {exc}"
    return f"{path.name}: {result}"


def _release_benchmark_metadata_error(path: Path, metadata: dict[str, object] | None = None) -> str:
    payload = metadata or {"workflow": "<script>"}
    try:
        result = update_release_benchmark_history.safe_incoming_metadata(payload, path=path)
    except ValueError as exc:
        return f"{path.name}: ValueError: {exc}"
    return f"{path.name}: {result}"


def test_update_release_benchmark_history_helper_edges(tmp_path: Path) -> None:
    """Small merge helpers keep metadata edge cases deterministic."""
    invalid_payload = tmp_path / "invalid-payload.json"
    invalid_payload.write_text("[]", encoding="utf-8")
    invalid_entries = tmp_path / "invalid-entries.json"
    invalid_entries.write_text('{"schema_version": 1, "metadata": {}, "entries": {}}', encoding="utf-8")
    invalid_selection = tmp_path / "invalid-selection.json"
    invalid_selection.write_text("[]", encoding="utf-8")
    sparse_selection = tmp_path / "sparse-selection.json"
    sparse_selection.write_text(
        '{"releases": [null, {"version": "", "uploaded_at": "2026-06-19T00:00:00Z"}]}',
        encoding="utf-8",
    )
    valid_selection = tmp_path / "valid-selection.json"
    valid_selection.write_text(
        '{"releases": [{"version": "0.64.1", "uploaded_at": "2026-06-19T00:00:00Z"}]}',
        encoding="utf-8",
    )
    unsafe_selection = tmp_path / "unsafe-selection.json"
    unsafe_selection.write_text(
        '{"releases": [{"version": "0.64.1", "uploaded_at": "2026-06-19T00:00:00Z<script>"}]}',
        encoding="utf-8",
    )
    unsafe_version_selection = tmp_path / "unsafe-version-selection.json"
    unsafe_version_selection.write_text(
        '{"releases": [{"version": "0.64.1<script>", "uploaded_at": "2026-06-19T00:00:00Z"}]}',
        encoding="utf-8",
    )
    unsafe_entry = tmp_path / "unsafe-entry.json"
    unsafe_entry.write_text(
        json.dumps({
            "schema_version": 1,
            "metadata": {},
            "entries": [
                {
                    "version": '0.64.1"><script>',
                    "input_type": "jsonschema",
                    "case": "small",
                    "formatter": "default",
                }
            ],
        }),
        encoding="utf-8",
    )
    non_object_entry = tmp_path / "non-object-entry.json"
    non_object_entry.write_text('{"schema_version": 1, "metadata": {}, "entries": [null]}', encoding="utf-8")
    missing_entry = tmp_path / "missing-entry.json"
    missing_entry.write_text(
        json.dumps({
            "schema_version": 1,
            "metadata": {},
            "entries": [{"input_type": "jsonschema", "case": "small", "formatter": "default"}],
        }),
        encoding="utf-8",
    )
    minimal_entry = tmp_path / "minimal-entry.json"
    minimal_entry.write_text(
        json.dumps({
            "schema_version": 1,
            "metadata": {},
            "entries": [{"version": "0.64.1", "input_type": "jsonschema", "case": "small", "formatter": "default"}],
        }),
        encoding="utf-8",
    )
    unsafe_optional_entry = tmp_path / "unsafe-optional-entry.json"
    unsafe_optional_entry.write_text(
        json.dumps({
            "schema_version": 1,
            "metadata": {},
            "entries": [
                {
                    "version": "0.64.1",
                    "input_type": "jsonschema",
                    "case": "small",
                    "formatter": "default",
                    "status": "<script>",
                }
            ],
        }),
        encoding="utf-8",
    )
    unsafe_metadata = tmp_path / "unsafe-metadata.json"

    lines = [
        "generated-at-present: "
        + str(
            bool(
                update_release_benchmark_history._merged_metadata(
                    {},
                    {},
                    [],
                    selection_path=None,
                    generated_at="",
                ).get("generated_at")
            )
        ),
        "metadata-empty: " + str(update_release_benchmark_history._metadata({"metadata": []})),
        "int-string-int: " + update_release_benchmark_history._int_string(123),
        "int-string-str: " + update_release_benchmark_history._int_string("456"),
        "int-string-empty: " + update_release_benchmark_history._int_string("mixed"),
        "version-sort-suffix: " + str(update_release_benchmark_history.version_sort_key("v1.2.3+local")),
        "version-sort-empty-token: " + str(update_release_benchmark_history.version_sort_key("v1..2")),
        "runs-fallback: " + update_release_benchmark_history._runs_per_case([], "fallback"),
        "strategy-empty: "
        + update_release_benchmark_history._selection_strategy({}, {"selection_strategy": "explicit"}),
        "strategy-explicit: "
        + update_release_benchmark_history._selection_strategy(
            {"selection_strategy": "clickpy_downloads"},
            {"selection_strategy": "explicit"},
        ),
        "strategy-same: "
        + update_release_benchmark_history._selection_strategy(
            {"selection_strategy": "clickpy_downloads"},
            {"selection_strategy": "clickpy_downloads"},
        ),
        "strategy-base: " + update_release_benchmark_history._selection_strategy({"selection_strategy": "manual"}, {}),
        "strategy-combined: "
        + update_release_benchmark_history._selection_strategy(
            {"selection_strategy": "manual"},
            {"selection_strategy": "backfill"},
        ),
        "invalid-selection: " + str(update_release_benchmark_history._release_dates_from_selection(invalid_selection)),
        "sparse-selection: " + str(update_release_benchmark_history._release_dates_from_selection(sparse_selection)),
        "valid-selection-helper: " + _release_benchmark_selection_error(valid_selection),
        "unsafe-selection: " + _release_benchmark_selection_error(unsafe_selection),
        "unsafe-version-selection: " + _release_benchmark_selection_error(unsafe_version_selection),
        "missing-selection: "
        + str(update_release_benchmark_history._release_dates_from_selection(tmp_path / "missing-selection.json")),
        "unsafe-metadata: " + _release_benchmark_metadata_error(unsafe_metadata),
        "safe-metadata: "
        + _release_benchmark_metadata_error(
            unsafe_metadata,
            {"workflow": "Release Benchmarks", "selected_versions": "0.64.1,main"},
        ),
        "missing-incoming: "
        + _release_benchmark_history_error(
            FIXTURE_DATA,
            tmp_path / "unused.json",
            incoming_data_path=tmp_path / "missing-incoming.json",
        ),
        "blank-metadata: "
        + str(update_release_benchmark_history.safe_incoming_metadata({"workflow": "   "}, path=unsafe_metadata)),
        "empty-release-date-version: "
        + str(update_release_benchmark_history._merged_release_dates({"release_dates": {"": ""}}, {}, None)),
        "merged-release-dates-preserve: "
        + str(
            update_release_benchmark_history._merged_release_dates(
                {"release_dates": {"0.64.1": "2026-06-19T00:00:00Z"}},
                {"release_dates": {"0.64.1": ""}},
                None,
            )
        ),
    ]
    lines.extend(
        _release_benchmark_history_error(path, tmp_path / "unused.json")
        for path in (
            invalid_payload,
            invalid_entries,
            non_object_entry,
            unsafe_entry,
            missing_entry,
            minimal_entry,
            unsafe_optional_entry,
        )
    )

    output = "\n".join(lines).replace(str(tmp_path), "<tmp>").replace("<tmp>\\", "<tmp>/")
    assert_output(
        output + "\n",
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "update_release_benchmark_history_edges.txt",
    )


def test_select_release_benchmark_versions_skips_unsafe_external_versions() -> None:
    """Malformed external version labels are ignored instead of aborting selection."""
    releases = select_release_benchmark_versions._release_versions({
        "releases": {
            "0.64.1<script>": [{"upload_time_iso_8601": "2026-06-19T00:00:00Z"}],
            "0.64.1": [{"upload_time_iso_8601": "2026-06-19T00:00:00Z"}],
        }
    })
    usage = select_release_benchmark_versions._version_usage({
        "data": [
            {"version": "0.64.1<script>", "downloads": 100, "first_seen": "2026-06-19", "last_seen": "2026-06-20"},
            {"version": "0.64.1", "downloads": 10, "first_seen": "2026-06-19", "last_seen": "2026-06-20"},
        ]
    })
    selected = select_release_benchmark_versions._selected_explicit_releases(
        {release.version: release for release in releases},
        {item.version: item for item in usage},
        "0.64.1<script>,0.64.1,main",
        limit=3,
    )
    output = "\n".join((
        "releases: " + ",".join(release.version for release in releases),
        "usage: " + ",".join(item.version for item in usage),
        "selected: " + ",".join(release.version for release in selected),
        "",
    ))

    assert_output(
        output,
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "select_release_benchmark_versions_invalid_external.txt",
    )
