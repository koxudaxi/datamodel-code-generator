"""Shared fixtures for XML Schema tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.conftest import create_assert_file_content
from tests.main.conftest import EXPECTED_XML_SCHEMA_PATH

if TYPE_CHECKING:
    from collections.abc import Callable

assert_file_content = create_assert_file_content(EXPECTED_XML_SCHEMA_PATH)

XMLSCHEMA_SNIPPETS: dict[str, tuple[str, ...]] = {
    "coverage": (
        "class IncludedCode(RootModel[constr(pattern=r'[A-Z]+', min_length=3, max_length=3)]):",
        "class TokenList(RootModel[list[str]]):",
        "class InlineTokenList(RootModel[list[InlineTokenListEnum]]):",
        "class BooleanFacet(Enum):",
        "class ArrayFacet(RootModel[list[str]]):",
        "class BaseType(BaseModel):",
        "sharedElement: list[SharedElement] | None = Field(None, max_length=2)",
        "left: str | None = None",
        "fromGroup: str | None = None",
        "localNumber: conint(ge=-2147483648, le=2147483647) | None = 1",
        "inlineAttribute: constr(max_length=8) | None = None",
        "globalFlag: Literal[True]",
        "class ExtendedType(BaseType):",
        "extra: list[str] | None = Field(None, max_length=3)",
        "class RestrictedType(BaseModel):",
        "only: str",
        "class FallbackContent(BaseModel):",
        "class Amount(BaseModel):",
        "value: conint(ge=1, le=2147483647)",
        "unit: str | None = None",
        "class TextWithAttrs(BaseModel):",
        "kind: Literal['plain'] = 'plain'",
        "first: ExtendedType",
        "class Second(BaseModel):",
        "inlineChild: constr(min_length=2)",
    ),
    "edge_cases": (
        "class EmptyRestriction(RootModel[str]):",
        "class NotAPythonType(RootModel[str]):",
        "class NoSimpleChild(BaseModel):",
        "value: str",
        "class Loose(BaseModel):",
        "inlineGroupElement: Literal['v'] = Field(",
        "not_a_python_name: str",
        "unboundedItem: list[str] | None = None",
        "badOccurs: list[str]",
        "empty: Any",
        "unknownNamespace: Any",
        "localGrouped: str | None = Field(None, description='Grouped attr')",
        "plain: str",
        "loose: Loose",
    ),
    "single_root_item": (
        "class Item(BaseModel):",
        "name: str",
    ),
    "inline_root": (
        "class InlineRoot(BaseModel):",
        "value: str",
    ),
    "recursive_node": (
        "class Node(BaseModel):",
        "child: Node | None = None",
    ),
    "import_namespace": (
        "class ImportedCode(RootModel[constr(min_length=5, max_length=5)]):",
        "class Code(BaseModel):",
    ),
    "namespace_collisions": (
        "class HttpsExampleComBillingAddress(BaseModel):",
        "class HttpsExampleComCommonBillingCode(RootModel[constr(max_length=4)]):",
        "class HttpsExampleComShippingAddress(BaseModel):",
        "class HttpsExampleComCommonShippingCode(RootModel[constr(min_length=2)]):",
        "class UrnABThing(RootModel[str]):",
        "class UrnABThing2(RootModel[str]):",
        "shipping: HttpsExampleComShippingAddress",
        "billing: HttpsExampleComBillingAddress",
    ),
    "no_namespace_collision": (
        "class HttpsExampleComExternalCode(RootModel[str]):",
        "class NoNamespaceCode(RootModel[str]):",
        "localCode: NoNamespaceCode",
        "externalCode: HttpsExampleComExternalCode",
    ),
    "namespace_fallback": (
        "class LocalThing(BaseModel):",
        "value: str",
        "class Shared(BaseModel):",
        "name: str",
        "class Holder(BaseModel):",
        "Shared_1: Shared = Field(..., alias='Shared')",
    ),
}


def assert_xmlschema_snippets(
    output_file: Path,
    expected_name: str | Path | None = None,
    encoding: str = "utf-8",
    transform: Callable[[str], str] | None = None,
) -> None:
    """Assert generated XML Schema output contains the snippets for a fixture."""
    __tracebackhide__ = True
    if expected_name is None:  # pragma: no cover
        pytest.fail("expected_name is required for XML Schema snippet assertions")
    content = output_file.read_text(encoding=encoding)
    if transform is not None:
        content = transform(content)
    key = Path(expected_name).stem
    expected_snippets = XMLSCHEMA_SNIPPETS.get(key)
    if expected_snippets is None:  # pragma: no cover
        pytest.fail(f"Unknown XML Schema snippet fixture: {expected_name}")
    missing = [snippet for snippet in expected_snippets if snippet not in content]
    if missing:  # pragma: no cover
        pytest.fail("Generated XML Schema output is missing snippets:\n" + "\n\n".join(missing))
