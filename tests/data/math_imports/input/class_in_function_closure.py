def outer() -> object:
    inf = 1

    class Nested:
        value = inf

    return Nested
