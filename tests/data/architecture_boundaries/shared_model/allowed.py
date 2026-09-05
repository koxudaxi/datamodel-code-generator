import sys


def rebuild_namespace(model_type: type[object]) -> dict[str, object]:
    return vars(sys.modules[model_type.__module__])
