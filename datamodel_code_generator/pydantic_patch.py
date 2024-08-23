import sys

import pydantic.typing


def patched_evaluate_forwardref(
    forward_ref, globalns, localns=None
):  # pragma: no cover
    try:
        return forward_ref._evaluate(
            globalns, localns or None, set()
        )  # pragma: no cover
    except TypeError:
        # Fallback for Python 3.12 compatibility
        return forward_ref._evaluate(
            globalns, localns or None, set(), recursive_guard=set()
        )


# Patch only Python3.12
if sys.version_info >= (3, 12):
    pydantic.typing.evaluate_forwardref = patched_evaluate_forwardref
