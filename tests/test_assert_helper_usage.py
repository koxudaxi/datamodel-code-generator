"""Tests that e2e test modules use shared assertion helpers."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.conftest import assert_httpx_get_kwargs

TESTS_ROOT = Path(__file__).parent
E2E_TEST_PATHS = (
    Path("main/graphql/test_annotated.py"),
    Path("main/graphql/test_main_graphql.py"),
    Path("main/jsonschema/test_main_jsonschema.py"),
    Path("main/openapi/test_main_openapi.py"),
    Path("main/test_main_csv.py"),
    Path("main/test_exec_validation.py"),
    Path("main/test_main_general.py"),
    Path("main/test_main_json.py"),
    Path("main/test_main_watch.py"),
    Path("main/test_main_yaml.py"),
    Path("test_main_kr.py"),
)


@dataclass(frozen=True)
class DirectAssert:
    """A direct assert statement in an e2e test module."""

    path: Path
    function_name: str | None
    lineno: int
    statement: str


def _allows_direct_assert(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        ast.unparse(decorator).startswith("pytest.mark.allow_direct_assert") for decorator in function.decorator_list
    )


def _statement(node: ast.Assert, source: str) -> str:
    statement = ast.get_source_segment(source, node) or ast.unparse(node)
    return " ".join(statement.split())


class _DirectAssertVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.asserts: list[ast.Assert] = []

    def visit_Assert(self, node: ast.Assert) -> None:
        self.asserts.append(node)

    def visit_FunctionDef(self, _node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, _node: ast.AsyncFunctionDef) -> None:
        return


def _collect_function_asserts(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Assert]:
    visitor = _DirectAssertVisitor()
    for statement in function.body:
        visitor.visit(statement)
    return visitor.asserts


def _collect_direct_asserts(path: Path) -> list[DirectAssert]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    direct_asserts: list[DirectAssert] = []

    for function in [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        if _allows_direct_assert(function):
            continue
        direct_asserts.extend(
            DirectAssert(
                path=path.relative_to(TESTS_ROOT),
                function_name=function.name,
                lineno=node.lineno,
                statement=_statement(node, source),
            )
            for node in _collect_function_asserts(function)
        )

    return direct_asserts


def test_e2e_modules_use_shared_assertion_helpers() -> None:
    """Direct asserts in e2e modules must be explicitly marked as exceptions."""
    direct_asserts = [
        direct_assert
        for relative_path in E2E_TEST_PATHS
        for direct_assert in _collect_direct_asserts(TESTS_ROOT / relative_path)
    ]

    if direct_asserts:  # pragma: no cover
        details = "\n".join(
            f"  tests/{direct_assert.path}:{direct_assert.lineno} "
            f"({direct_assert.function_name}): {direct_assert.statement}"
            for direct_assert in direct_asserts
        )
        pytest.fail(
            "Direct assert statements in e2e modules must either use shared assertion helpers "
            "or be marked with @pytest.mark.allow_direct_assert.\n"
            f"{details}",
            pytrace=False,
        )


def test_e2e_modules_use_shared_assertion_helpers_reports_unmarked_assert(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unmarked direct asserts in guarded files are reported as test failures."""
    test_file = tmp_path / "test_example.py"
    test_file.write_text("def test_example():\n    assert False\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "TESTS_ROOT", tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "E2E_TEST_PATHS", (Path("test_example.py"),))

    with pytest.raises(pytest.fail.Exception, match="Direct assert statements"):
        test_e2e_modules_use_shared_assertion_helpers()


def test_collect_function_asserts_ignores_nested_async_helpers() -> None:
    """Nested async helpers are reported on their own function, not the outer test."""
    module = ast.parse(
        """
def test_example():
    async def assert_later():
        assert False
"""
    )
    function = next(node for node in ast.walk(module) if isinstance(node, ast.FunctionDef))

    assert _collect_function_asserts(function) == []


def test_assert_httpx_get_kwargs_accepts_expected_urls_with_explicit_call_count(mocker: pytest.MockerFixture) -> None:
    """Explicit call_count works with multi-URL httpx.get assertions."""
    mock_get = mocker.Mock()
    mock_get(
        "https://example.com/person.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )
    mock_get(
        "https://example.com/address.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )

    assert_httpx_get_kwargs(
        mock_get,
        expected_urls=["https://example.com/person.json", "https://example.com/address.json"],
        call_count=2,
    )


def test_assert_httpx_get_kwargs_accepts_called_true(mocker: pytest.MockerFixture) -> None:
    """called=True asserts that at least one URL request was made."""
    mock_get = mocker.Mock()
    mock_get(
        "https://example.com/person.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )

    assert_httpx_get_kwargs(mock_get, called=True)


def test_assert_httpx_get_kwargs_validates_params_contains_for_every_call(mocker: pytest.MockerFixture) -> None:
    """Subset query parameter checks apply to all recorded URL requests."""
    mock_get = mocker.Mock()
    mock_get(
        "https://example.com/person.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=[("version", "v2"), ("format", "json")],
        timeout=30.0,
    )
    mock_get(
        "https://example.com/address.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=[("version", "v2"), ("format", "yaml")],
        timeout=30.0,
    )

    assert_httpx_get_kwargs(
        mock_get,
        expected_urls=["https://example.com/person.json", "https://example.com/address.json"],
        params_contains={"version": "v2"},
    )


def test_assert_httpx_get_kwargs_reports_params_contains_mismatch_per_call(mocker: pytest.MockerFixture) -> None:
    """Subset query parameter failures identify the request that mismatched."""
    mock_get = mocker.Mock()
    mock_get(
        "https://example.com/person.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=[("version", "v2")],
        timeout=30.0,
    )
    mock_get(
        "https://example.com/address.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=[("version", "v1")],
        timeout=30.0,
    )

    with pytest.raises(AssertionError, match="call 2"):
        assert_httpx_get_kwargs(mock_get, params_contains={"version": "v2"})
