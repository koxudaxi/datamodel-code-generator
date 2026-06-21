"""Tests for release benchmark documentation generation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts import build_release_benchmark_docs
from scripts.collect_release_benchmarks import _failure_status, _run_subprocess
from scripts.release_benchmark_errors import sanitize_benchmark_error, summarize_benchmark_error
from tests.conftest import assert_output

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_release_benchmark_docs.py"
FIXTURE_DATA = ROOT / "tests" / "data" / "release_benchmarks" / "sample.json"
FIXTURE_DIR = ROOT / "tests" / "data" / "release_benchmarks"
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
    """Render Markdown and SVG from an external benchmark data fixture."""
    data = build_release_benchmark_docs.load_benchmark_data(FIXTURE_DATA)

    assert_output(
        "\n--- markdown ---\n"
        + build_release_benchmark_docs.render_release_benchmark_markdown(data)
        + "\n--- svg ---\n"
        + build_release_benchmark_docs.render_release_benchmark_svg(data),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "release_benchmark_rendered.txt",
    )


def test_release_benchmark_docs_cli_writes_expected_outputs(tmp_path: Path) -> None:
    """The CLI can render fixture-backed Markdown and SVG to caller-selected paths."""
    docs_path = tmp_path / "performance-benchmarks.md"
    svg_path = tmp_path / "release-benchmarks.svg"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--data",
            str(FIXTURE_DATA),
            "--docs",
            str(docs_path),
            "--svg",
            str(svg_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    _raise_for_failed_process(result)
    assert_output(
        _completed_process_output(result)
        + "docs:\n"
        + docs_path.read_text(encoding="utf-8")
        + "svg:\n"
        + svg_path.read_text(encoding="utf-8"),
        EXPECTED_RELEASE_BENCHMARK_DOCS_PATH / "release_benchmark_cli_outputs.txt",
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
