"""Independent native float contract for one proven decimal-multiple lowering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field, TypeAdapter, ValidationError

if TYPE_CHECKING:
    from .models import SchemaCase

NATIVE_FLOAT_CONTRACT = json.loads(
    (Path(__file__).parents[2] / "data" / "payloads" / "native_float_multiple_contract.json").read_text()
)
NATIVE_FLOAT_ADAPTER = TypeAdapter(Annotated[float, Field(multiple_of=float(NATIVE_FLOAT_CONTRACT["native_multiple"]))])


def native_float_multiple_errors(case: SchemaCase, payload: Any) -> list[dict[str, Any]] | None:
    """Return expected native errors, or None when the case has no native contract."""
    if case.id != NATIVE_FLOAT_CONTRACT["case_id"]:
        return None
    field = NATIVE_FLOAT_CONTRACT["field"]
    if case.source_schema.get("properties", {}).get(field) != NATIVE_FLOAT_CONTRACT["source_fragment"]:
        msg = "Native float contract does not match the original source fragment"
        raise ValueError(msg)
    if field not in payload:
        return []
    try:
        NATIVE_FLOAT_ADAPTER.validate_python(payload[field])
    except ValidationError as exc:
        errors = exc.errors(include_url=False)
        for error in errors:
            if error["type"] != "multiple_of":
                msg = "Native float contract encountered an unrelated validation error"
                raise ValueError(msg) from exc
            error["loc"] = (field, *error["loc"])
        return errors
    return []


def pydantic_payload_result(adapter: TypeAdapter[Any], payload: Any) -> tuple[Any, list[dict[str, Any]]]:
    """Collect a native/generated runtime result or its complete validation errors."""
    try:
        return adapter.validate_python(payload), []
    except ValidationError as exc:
        return None, exc.errors(include_url=False)
