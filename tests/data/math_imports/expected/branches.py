from math import inf, nan
if condition:
    from math import inf
else:
    from math import nan
conditional = inf
holder.inf += nan


@nan
async def examples(
    first: inf,
    /,
    *args: nan,
    keyword: inf = nan,
    optional: int = None,
    required: int,
    **kwargs: nan,
) -> inf:
    inf: int = nan
    nan: int
    inf += 1
    import package as inf
    from package import nan as inf
    from package import *
    try:
        raise RuntimeError
    except RuntimeError as nan:
        pass
    try:
        raise ValueError
    except ValueError:
        pass
    def inf():
        pass
    class nan:
        pass
    local_lambda = lambda inf: inf
    local_list = [nan for nan in items if nan]
    local_set = {nan for nan in items}
    local_generator = (nan for nan in items)
    local_dict = {nan: inf for nan in items for inf in items}
    return inf


def global_inf() -> float:
    global inf
    return inf


def outer() -> object:
    inf = 1

    def inner() -> int:
        nonlocal inf
        return inf

    return inner


lambda_global = lambda: nan


@inf
class Decorated(inf, metaclass=nan):
    pass


from math import *
star_value = inf
