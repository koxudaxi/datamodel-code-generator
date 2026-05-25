"""Shared fixtures for Protocol Buffers tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tests.conftest import create_assert_file_content
from tests.main.conftest import EXPECTED_PROTOBUF_PATH

if TYPE_CHECKING:
    from collections.abc import Callable

assert_file_content = create_assert_file_content(EXPECTED_PROTOBUF_PATH)

PROTOBUF_SNIPPETS: dict[str, tuple[str, ...]] = {
    "complex_proto3": (
        "class ExampleCommonStatus(Enum):",
        "class ExampleCommonAddress(BaseModel):",
        "class ExamplePublicPublicToken(BaseModel):",
        "class ExampleShopV1OrderRole(Enum):",
        "class ExampleShopV1OrderLineItem(BaseModel):",
        "class ExampleShopV1Order(BaseModel):",
        "model_validator",
        "double_value: float | None = 0.0",
        "float_value: float | None = 0.0",
        "int32_value: int | None = 0",
        "int64_value: int | None = 0",
        "uint32_value: conint(ge=0, le=4294967295) | None = 0",
        "uint64_value: conint(ge=0, le=18446744073709551615) | None = 0",
        "sint32_value: int | None = 0",
        "sint64_value: int | None = 0",
        "fixed32_value: conint(ge=0, le=4294967295) | None = 0",
        "fixed64_value: conint(ge=0, le=18446744073709551615) | None = 0",
        "sfixed32_value: int | None = 0",
        "sfixed64_value: int | None = 0",
        "active: bool | None = False",
        "payload: bytes | None = ''",
        "tags: list[str] | None = []",
        "items: dict[str, ExampleShopV1OrderLineItem] | None = Field(",
        "previous_items: list[ExampleShopV1OrderLineItem] | None = Field(",
        "shipping_address: ExampleCommonAddress | None = None",
        "status: ExampleCommonStatus | None = 'STATUS_UNSPECIFIED'",
        "created_at: AwareDatetime | None = None",
        "ttl: timedelta | None = None",
        "metadata: dict[str, Any] | None = None",
        "arbitrary: bool | float | str | dict[str, Any] | list[Any] | None = None",
        "values: list[Any] | None = None",
        "attachment: dict[str, Any] | None = None",
        "update_mask: str | None = None",
        "optional_note: str | None = None",
        "public_token: ExamplePublicPublicToken | None = None",
        "roles: list[ExampleShopV1OrderRole] | None = []",
        "oneof: contact",
        "@model_validator(mode='after')",
        "Only one of",
        "class ExampleShopV1GetOrderRequest(BaseModel):",
        "class ExampleShopV1GetOrderResponse(BaseModel):",
        "order: ExampleShopV1Order | None = None",
    ),
    "proto2": (
        "from math import inf",
        "class ExampleLegacyLegacyStatus(Enum):",
        "class ExampleLegacyLegacyMessageLegacyGroup(BaseModel):",
        "class ExampleLegacyLegacyMessage(BaseModel):",
        "id: str",
        "legacygroup: ExampleLegacyLegacyMessageLegacyGroup | None = None",
        "count: int | None = 7",
        "enabled: bool | None = True",
        "tags: list[str] | None = []",
        "ratio: float | None = inf",
        "status: ExampleLegacyLegacyStatus | None = 'LEGACY_ACTIVE'",
        "title: str | None = 'legacy'",
        "annotated: str | None = 'kept'",
        "annotation_only: str | None = None",
        "escaped: str | None = 'a\"b'",
        "empty_default: str | None = ''",
        "multiline_option: str | None = 'wrapped'",
        "bracket_default: str | None = 'a]b'",
    ),
    "proto3_optional": (
        "class ExamplePresencePresence(BaseModel):",
        "implicit_name: str | None = ''",
        "explicit_name: str | None = None",
        "explicit_count: int | None = None",
    ),
}


def assert_protobuf_snippets(
    output_file: Path,
    expected_name: str | Path | None = None,
    encoding: str = "utf-8",
    transform: Callable[[str], str] | None = None,
) -> None:
    """Assert generated Protocol Buffers output contains expected snippets."""
    assert expected_name is not None
    assert transform is None
    content = output_file.read_text(encoding=encoding)
    key = Path(expected_name).stem
    for snippet in PROTOBUF_SNIPPETS[key]:
        assert snippet in content
    assert "class Model(" not in content
