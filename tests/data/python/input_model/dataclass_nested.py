"""Dataclass with mixed nested types for --input-model-ref-strategy tests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Priority(Enum):
    """Enum that should be reused with reuse-foreign strategy."""

    LOW = "low"
    HIGH = "high"


@dataclass
class Tag:
    """Nested dataclass that should be regenerated with reuse-foreign strategy."""

    name: str
    value: str


@dataclass
class Task:
    """Main dataclass with mixed reference types."""

    title: str
    priority: Priority
    tag: Optional[Tag] = None
