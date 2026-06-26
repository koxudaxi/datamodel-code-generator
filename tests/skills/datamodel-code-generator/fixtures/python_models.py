"""Python model fixture for agent skill recipe tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SkillInputUser:
    """Simple input model used by --input-model tests."""

    id: int
    name: str
