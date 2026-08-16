from math import inf, nan
class PriorBinding:
    inf = 1
    value = inf


class LaterBinding:
    value = nan
    nan = 1


class MethodLookup:
    inf = 1

    def value(self) -> float:
        return inf


local_values = [nan for nan in range(1)]
global_values = [inf for _ in range(1)]
