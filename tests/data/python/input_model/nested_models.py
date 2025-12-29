"""Models with mixed types for --input-model-ref-strategy tests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Status(Enum):
    """Enum that should be reused with reuse-foreign strategy."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class Metadata:
    """Dataclass that should be reused with reuse-foreign strategy."""

    key: str
    value: str


class Address(BaseModel):
    """Nested BaseModel that should be regenerated with reuse-foreign strategy."""

    street: str
    city: str


class User(BaseModel):
    """Main model with mixed reference types."""

    name: str
    status: Status
    metadata: Optional[Metadata] = None
    address: Optional[Address] = None
