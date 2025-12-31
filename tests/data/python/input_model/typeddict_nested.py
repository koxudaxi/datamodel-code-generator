"""TypedDict with nested types for --input-model-ref-strategy tests."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from typing_extensions import TypedDict


class Role(Enum):
    """Enum that should be reused with reuse-foreign strategy."""

    ADMIN = "admin"
    USER = "user"


class Profile(TypedDict):
    """Nested TypedDict that should be regenerated with reuse-foreign strategy."""

    bio: str
    website: str


class Member(TypedDict):
    """Main TypedDict with mixed reference types."""

    name: str
    role: Role
    profile: Optional[Profile]
