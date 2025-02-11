import sys
from typing import Any, Dict, Optional

import pydantic.typing


def patched_evaluate_forwardref(
    forward_ref: Any, globalns: Dict[str, Any], localns: Optional[Dict[str, Any]] = None
) -> None:  # pragma: no cover
    try:
        return forward_ref._evaluate(globalns, localns or None, set())  # pragma: no cover  # noqa: SLF001
    except TypeError:
        # Fallback for Python 3.12 compatibility
        return forward_ref._evaluate(globalns, localns or None, set(), recursive_guard=set())  # noqa: SLF001


# Patch only Python3.12
if sys.version_info >= (3, 12):
    pydantic.typing.evaluate_forwardref = patched_evaluate_forwardref  # pyright: ignore [reportAttributeAccessIssue]
