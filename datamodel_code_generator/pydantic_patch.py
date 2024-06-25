import pydantic.typing


def patched_evaluate_forwardref(forward_ref, globalns, localns=None):
    try:
        return forward_ref._evaluate(
            globalns, localns or None, set()
        )  # pragma: no cover
    except TypeError:
        # Fallback for Python 3.12 compatibility
        return forward_ref._evaluate(
            globalns, localns or None, set(), recursive_guard=set()
        )


pydantic.typing.evaluate_forwardref = patched_evaluate_forwardref
