"""Pydantic compatibility patches for Python 3.12+.

Patches pydantic.typing.evaluate_forwardref for forward reference evaluation
compatibility with newer Python versions.
"""

from __future__ import annotations

import sys
from typing import Any


def patched_evaluate_forwardref(
    forward_ref: Any, globalns: dict[str, Any], localns: dict[str, Any] | None = None
) -> None:  # pragma: no cover
    """Evaluate a forward reference with Python 3.12+ compatibility."""
    try:
        return forward_ref._evaluate(globalns, localns or None, set())  # pragma: no cover  # noqa: SLF001
    except TypeError:
        # Fallback for Python 3.12 compatibility
        return forward_ref._evaluate(globalns, localns or None, set(), recursive_guard=set())  # noqa: SLF001


def apply_patch() -> None:
    """Apply the pydantic patch for Python 3.12+ if needed."""
    if sys.version_info >= (3, 12):
        import pydantic.typing  # noqa: PLC0415

        pydantic.typing.evaluate_forwardref = patched_evaluate_forwardref  # pyright: ignore[reportAttributeAccessIssue]
