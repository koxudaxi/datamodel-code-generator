"""Tests that e2e test modules use shared assertion helpers."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

from tests.conftest import (
    HttpxGetMockFactory,
    MockHttpxResponse,
    assert_httpx_get_kwargs,
    create_httpx_get_mock,
)
from tests.main.conftest import assert_generated_model_json_invalid, assert_generated_model_json_validation

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pytest_mock import MockerFixture

TESTS_ROOT = Path(__file__).parent
DIRECT_ASSERT_EXEMPT_FILES_INI = "assert_helper_direct_assert_exempt_files"
DIRECT_ASSERT_FAILURE_MESSAGE = (
    "Direct assert statements in guarded test modules require explicit permission.\n"
    "HTTP, external-request, or similar mock assertions may be unavoidable, but generation tests should generally "
    "be e2e tests that compare generated output through the shared assert helpers.\n"
    "Use @pytest.mark.allow_direct_assert for a narrow exception, or add intentional legacy/unit files to "
    f"{DIRECT_ASSERT_EXEMPT_FILES_INI}."
)


@dataclass(frozen=True)
class DirectAssert:
    """A direct assert statement in a guarded test module."""

    path: Path
    function_name: str | None
    lineno: int
    statement: str


def _allows_direct_assert(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        ast.unparse(decorator).split("(", 1)[0] == "pytest.mark.allow_direct_assert"
        for decorator in function.decorator_list
    )


def _is_test_file(path: Path, tests_root: Path) -> bool:
    relative_path = path.relative_to(tests_root)
    is_test_file = False
    match relative_path.parts:
        case ("data", *_):
            pass
        case (*_, file_name) if path.suffix == ".py" and (
            file_name.startswith("test_") or file_name.endswith("_test.py")
        ):
            is_test_file = True
        case _:
            pass
    return is_test_file


def _normalize_exempt_file(raw_path: str) -> Path:
    path = Path(raw_path.strip())
    normalized_path = path
    match path.parts:
        case ("tests", *parts):
            normalized_path = Path(*parts)
        case _:
            pass
    return normalized_path


def _configured_exempt_files(config: pytest.Config) -> frozenset[Path]:
    return frozenset(
        normalized_path
        for raw_path in config.getini(DIRECT_ASSERT_EXEMPT_FILES_INI)
        if raw_path.strip() and (normalized_path := _normalize_exempt_file(raw_path))
    )


def _iter_guarded_test_files(tests_root: Path, exempt_files: Iterable[Path]) -> Iterable[Path]:
    exempt_file_set = frozenset(exempt_files)
    for path in sorted(tests_root.rglob("*.py")):
        if not _is_test_file(path, tests_root):
            continue
        if path.relative_to(tests_root) in exempt_file_set:
            continue
        yield path


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

    def visit_ClassDef(self, _node: ast.ClassDef) -> None:
        return


def _collect_function_asserts(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Assert]:
    visitor = _DirectAssertVisitor()
    for statement in function.body:
        visitor.visit(statement)
    return visitor.asserts


def _collect_direct_asserts(path: Path, tests_root: Path = TESTS_ROOT) -> list[DirectAssert]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    direct_asserts: list[DirectAssert] = []

    direct_asserts.extend(
        DirectAssert(
            path=path.relative_to(tests_root),
            function_name="<module>",
            lineno=node.lineno,
            statement=_statement(node, source),
        )
        for node in tree.body
        if isinstance(node, ast.Assert)
    )

    for function in [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        if _allows_direct_assert(function):
            continue
        direct_asserts.extend(
            DirectAssert(
                path=path.relative_to(tests_root),
                function_name=function.name,
                lineno=node.lineno,
                statement=_statement(node, source),
            )
            for node in _collect_function_asserts(function)
        )

    return direct_asserts


def _collect_guarded_direct_asserts(tests_root: Path, exempt_files: Iterable[Path]) -> list[DirectAssert]:
    return [
        direct_assert
        for path in _iter_guarded_test_files(tests_root, exempt_files)
        if (path_direct_asserts := _collect_direct_asserts(path, tests_root))
        for direct_assert in path_direct_asserts
    ]


def _format_direct_assert_failure(direct_asserts: Iterable[DirectAssert]) -> str:
    details = "\n".join(
        f"  tests/{direct_assert.path}:{direct_assert.lineno} "
        f"({direct_assert.function_name}): {direct_assert.statement}"
        for direct_assert in direct_asserts
    )
    return f"{DIRECT_ASSERT_FAILURE_MESSAGE}\n{details}"


def test_modules_use_shared_assertion_helpers(pytestconfig: pytest.Config) -> None:
    """Direct asserts in guarded test modules must be explicitly marked as exceptions."""
    direct_asserts = _collect_guarded_direct_asserts(TESTS_ROOT, _configured_exempt_files(pytestconfig))

    if not direct_asserts:
        return

    pytest.fail(_format_direct_assert_failure(direct_asserts), pytrace=False)  # pragma: no cover


def test_configured_exempt_files_exist(pytestconfig: pytest.Config) -> None:
    """Configured direct-assert exemptions must point to existing test files."""
    if not (
        missing := sorted(path for path in _configured_exempt_files(pytestconfig) if not (TESTS_ROOT / path).is_file())
    ):
        return

    pytest.fail(  # pragma: no cover
        "assert_helper_direct_assert_exempt_files contains missing files:\n"
        + "\n".join(f"  - tests/{path}" for path in missing),
        pytrace=False,
    )


class _MissingExemptConfig:
    def getini(self, name: str) -> list[str]:
        if name == DIRECT_ASSERT_EXEMPT_FILES_INI:
            return ["missing.py"]
        raise KeyError(name)  # pragma: no cover


def test_configured_exempt_files_exist_reports_missing_file() -> None:
    """Missing configured direct-assert exemptions are reported clearly."""
    with pytest.raises(pytest.fail.Exception, match=r"tests/missing\.py"):
        test_configured_exempt_files_exist(_MissingExemptConfig())  # type: ignore[arg-type]


def test_modules_use_shared_assertion_helpers_reports_unmarked_assert(
    tmp_path: Path,
) -> None:
    """Unmarked direct asserts in guarded files are reported as test failures."""
    test_file = tmp_path / "test_example.py"
    test_file.write_text("def test_example():\n    assert False\n", encoding="utf-8")
    direct_asserts = _collect_guarded_direct_asserts(tmp_path, ())

    with pytest.raises(pytest.fail.Exception, match="shared assert helpers"):
        pytest.fail(_format_direct_assert_failure(direct_asserts), pytrace=False)


def test_iter_guarded_test_files_uses_all_test_files_by_default(tmp_path: Path) -> None:
    """All pytest-style test files under tests/ are guarded unless configured otherwise."""
    (tmp_path / "test_root.py").write_text("", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "example_test.py").write_text("", encoding="utf-8")
    (tmp_path / "nested" / "helper.py").write_text("", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "test_fixture.py").write_text("", encoding="utf-8")

    assert [path.relative_to(tmp_path) for path in _iter_guarded_test_files(tmp_path, ())] == [
        Path("nested/example_test.py"),
        Path("test_root.py"),
    ]


def test_iter_guarded_test_files_skips_configured_exempt_files(tmp_path: Path) -> None:
    """Configured file exceptions are skipped by the guard."""
    (tmp_path / "test_guarded.py").write_text("", encoding="utf-8")
    (tmp_path / "test_exempt.py").write_text("", encoding="utf-8")

    assert [path.relative_to(tmp_path) for path in _iter_guarded_test_files(tmp_path, (Path("test_exempt.py"),))] == [
        Path("test_guarded.py")
    ]


@pytest.mark.parametrize(
    ("raw_path", "expected"),
    [
        ("test_unit.py", Path("test_unit.py")),
        ("tests/test_unit.py", Path("test_unit.py")),
        ("tests/main/test_unit.py", Path("main/test_unit.py")),
    ],
)
def test_normalize_exempt_file_accepts_tests_prefix(raw_path: str, expected: Path) -> None:
    """Config paths may be relative to tests/ or include the tests/ prefix."""
    assert _normalize_exempt_file(raw_path) == expected


def test_collect_direct_asserts_reports_module_level_assert(tmp_path: Path) -> None:
    """Module-level direct asserts are reported by the guard."""
    test_file = tmp_path / "test_example.py"
    test_file.write_text("assert False\n", encoding="utf-8")

    assert _collect_direct_asserts(test_file, tmp_path) == [
        DirectAssert(Path("test_example.py"), "<module>", 1, "assert False")
    ]


def test_collect_function_asserts_ignores_nested_async_helpers() -> None:
    """Nested async helpers are reported on their own function, not the outer test."""
    module = ast.parse(
        """
def test_example():
    async def assert_later():
        assert False
"""
    )
    outer_function = next(node for node in ast.walk(module) if isinstance(node, ast.FunctionDef))
    inner_function = next(node for node in ast.walk(module) if isinstance(node, ast.AsyncFunctionDef))

    assert _collect_function_asserts(outer_function) == []
    assert len(_collect_function_asserts(inner_function)) == 1


def test_collect_function_asserts_ignores_nested_classes() -> None:
    """Nested classes are reported on their own methods, not the outer test."""
    module = ast.parse(
        """
def test_example():
    class AssertsLater:
        def assert_later(self):
            assert False
"""
    )
    outer_function = next(node for node in ast.walk(module) if isinstance(node, ast.FunctionDef))
    inner_method = next(
        node for node in ast.walk(module) if isinstance(node, ast.FunctionDef) and node.name == "assert_later"
    )

    assert _collect_function_asserts(outer_function) == []
    assert len(_collect_function_asserts(inner_method)) == 1


def test_assert_httpx_get_kwargs_accepts_expected_urls_with_explicit_call_count(mocker: MockerFixture) -> None:
    """Explicit call_count works with multi-URL httpx.get assertions."""
    mock_get = create_httpx_get_mock(mocker)
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


def test_assert_httpx_get_kwargs_accepts_called_true(mocker: MockerFixture) -> None:
    """called=True asserts that at least one URL request was made."""
    mock_get = create_httpx_get_mock(mocker)
    mock_get(
        "https://example.com/person.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )

    assert_httpx_get_kwargs(mock_get, called=True)


def test_assert_httpx_get_kwargs_validates_call_options_for_every_call(mocker: MockerFixture) -> None:
    """HTTP option checks apply to all recorded URL requests."""
    mock_get = create_httpx_get_mock(mocker)
    expected_headers = [("Authorization", "Bearer token")]
    expected_params = [("version", "v2")]
    mock_get(
        "https://example.com/person.json",
        headers=expected_headers,
        verify=False,
        follow_redirects=True,
        params=expected_params,
        timeout=60.0,
    )
    mock_get(
        "https://example.com/address.json",
        headers=expected_headers,
        verify=False,
        follow_redirects=True,
        params=expected_params,
        timeout=60.0,
    )

    assert_httpx_get_kwargs(
        mock_get,
        headers=expected_headers,
        params=expected_params,
        verify=False,
        timeout=60.0,
    )


def test_assert_httpx_get_kwargs_reports_call_option_mismatch_per_call(mocker: MockerFixture) -> None:
    """HTTP option failures catch mismatches before the last URL request."""
    mock_get = create_httpx_get_mock(mocker)
    mock_get(
        "https://example.com/person.json",
        headers=[("Authorization", "Bearer old")],
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )
    mock_get(
        "https://example.com/address.json",
        headers=[("Authorization", "Bearer token")],
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )

    with pytest.raises(AssertionError):
        assert_httpx_get_kwargs(mock_get, headers=[("Authorization", "Bearer token")])


def test_assert_httpx_get_kwargs_validates_params_contains_for_every_call(mocker: MockerFixture) -> None:
    """Subset query parameter checks apply to all recorded URL requests."""
    mock_get = create_httpx_get_mock(mocker)
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


def test_assert_httpx_get_kwargs_reports_params_contains_mismatch_per_call(mocker: MockerFixture) -> None:
    """Subset query parameter failures identify the request that mismatched."""
    mock_get = create_httpx_get_mock(mocker)
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


def test_mock_httpx_get_returns_response_for_registered_url(mock_httpx_get: HttpxGetMockFactory) -> None:
    """URL-bound HTTP mocks return fixture content for the registered URL."""
    import httpx

    mock_httpx_get(MockHttpxResponse("https://example.com/schema.json", '{"type": "object"}'))

    response = httpx.get("https://example.com/schema.json")

    assert response.text == '{"type": "object"}'


def test_mock_httpx_get_rejects_unregistered_url(mock_httpx_get: HttpxGetMockFactory) -> None:
    """URL-bound HTTP mocks fail when code fetches an unexpected URL."""
    import httpx

    mock_httpx_get(MockHttpxResponse("https://example.com/schema.json", '{"type": "object"}'))

    with pytest.raises(pytest.fail.Exception, match=r"Unexpected httpx\.get URL"):
        httpx.get("https://example.com/other.json")


def test_assert_generated_model_json_validation_without_attribute_check(tmp_path: Path) -> None:
    """Generated-model validation helper supports tests that only check rejection type."""
    output_path = tmp_path / "generated_model.py"
    output_path.write_text(
        "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    name: str\n",
        encoding="utf-8",
    )

    assert_generated_model_json_validation(
        output_path,
        module_name="generated_model_without_attribute_check",
        model_name="Model",
        valid_json='{"name": "x"}',
        invalid_json='{"name": 1}',
        expected_error_type="string_type",
    )


def test_generated_model_json_helpers_restore_existing_module(tmp_path: Path) -> None:
    """Generated-model validation helpers restore an existing sys.modules entry."""
    output_path = tmp_path / "generated_model.py"
    output_path.write_text(
        "from pydantic import BaseModel\n\nclass Model(BaseModel):\n    value: int\n",
        encoding="utf-8",
    )
    module_name = "preexisting_generated_model"
    previous_module = ModuleType(module_name)
    sys.modules[module_name] = previous_module

    try:
        assert_generated_model_json_validation(
            output_path,
            module_name=module_name,
            model_name="Model",
            valid_json='{"value": 1}',
            invalid_json='{"value": "bad"}',
            expected_error_type="int_parsing",
        )
        assert sys.modules[module_name] is previous_module

        assert_generated_model_json_invalid(
            output_path,
            module_name=module_name,
            model_name="Model",
            invalid_json='{"value": "bad"}',
            expected_error_type="int_parsing",
        )
        assert sys.modules[module_name] is previous_module
    finally:
        sys.modules.pop(module_name, None)
