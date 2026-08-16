from math import inf
def outer() -> object:
    inf = 1

    class Nested:
        value = inf
        inf = 2

    return Nested
