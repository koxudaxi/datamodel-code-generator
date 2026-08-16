def outer() -> object:
    inf = 1

    class Nested:
        global inf
        value = inf
        inf = 2

    return Nested
