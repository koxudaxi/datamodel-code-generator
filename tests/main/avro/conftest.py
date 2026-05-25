"""Shared fixtures for Avro tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import create_assert_file_content
from tests.main.conftest import EXPECTED_AVRO_PATH

assert_file_content = create_assert_file_content(EXPECTED_AVRO_PATH)

AVRO_SNIPPETS: dict[str, tuple[str, ...]] = {
    "constructs": (
        "from datetime import date, time, timedelta",
        "from decimal import Decimal",
        "from uuid import UUID",
        "class Status(",
        "ACTIVE = 'ACTIVE'",
        "INACTIVE = 'INACTIVE'",
        "class Duration(RootModel[timedelta]):",
        "class Address(BaseModel):",
        "street: str",
        "zip: str | None = None",
        "class MD5(RootModel[conbytes(min_length=16, max_length=16)]):",
        "class TraceId(RootModel[UUID]):",
        "class TaxDecimal(RootModel[Decimal]):",
        "class User(BaseModel):",
        "id: UUID",
        "Stable identifier",
        "active: bool = True",
        "age: int = 0",
        "visits: int",
        "score: float",
        "rating: float",
        "payload: bytes",
        "status: Status = 'ACTIVE'",
        "tags: list[str] = []",
        "attributes: dict[str, str] = {}",
        "address: Address",
        "previous: User | None = None",
        "hash: MD5",
        "traceId: TraceId",
        "price: Decimal",
        "tax: TaxDecimal",
        "flexibleAmount: Decimal",
        "birthDate: date",
        "startTime: time",
        "endTime: time",
        "createdAt: AwareDatetime",
        "updatedAt: AwareDatetime",
        "processedAt: AwareDatetime",
        "localCreatedAt: NaiveDatetime",
        "localUpdatedAt: NaiveDatetime",
        "localProcessedAt: NaiveDatetime",
        "duration: Duration",
        "choice: str | int | None = None",
        "rawDecimalText: str",
        "User.model_rebuild()",
    ),
    "namespace_collisions": (
        "class ComExampleBillingAddress(BaseModel):",
        "line1: str",
        "class ComExampleShippingAddress(BaseModel):",
        "line1: str",
        "class Envelope(BaseModel):",
        "billing: ComExampleBillingAddress",
        "shipping: ComExampleShippingAddress",
    ),
    "official_long_list": (
        "class LongList(BaseModel):",
        "value: int",
        "next: LongList | None = None",
        "LongList.model_rebuild()",
    ),
}


def assert_avro_snippets(
    generated_output: Path,
    expected_name: str | Path | None = None,
    encoding: str = "utf-8",
    transform: object = None,
) -> None:
    """Assert generated output contains important Avro snippets."""
    assert transform is None
    assert isinstance(expected_name, str)
    snippets = AVRO_SNIPPETS[Path(expected_name).stem]
    content = generated_output.read_text(encoding=encoding)
    missing = [snippet for snippet in snippets if snippet not in content]
    if missing:  # pragma: no cover
        pytest.fail(f"Missing snippets from {generated_output}: {missing}\n\n{content}")
