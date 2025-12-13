"""Graph utilities used by parsers.

This module intentionally contains only generic graph algorithms (no DataModel
or schema-specific logic), so it can be reused across parsers without creating
dependency cycles.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from typing import TypeVar

TNode = TypeVar("TNode", bound=Hashable)


def stable_toposort(
    nodes: list[TNode],
    edges: dict[TNode, set[TNode]],
    *,
    key: Callable[[TNode], int],
) -> list[TNode]:
    """Stable topological sort; breaks ties by `key`.

    The `edges` mapping is an adjacency list where `edges[u]` contains all `v`
    such that `u -> v` (i.e., `u` must come before `v`).

    If a cycle is detected, this function falls back to `sorted(nodes, key=key)`
    for determinism.
    """
    node_set = set(nodes)
    indegree: dict[TNode, int] = dict.fromkeys(nodes, 0)
    outgoing: dict[TNode, set[TNode]] = {n: set() for n in nodes}

    for src, dests in edges.items():
        if src not in node_set:
            continue
        for dst in dests:
            if dst not in node_set or dst in outgoing[src]:
                continue
            outgoing[src].add(dst)
            indegree[dst] += 1

    ready = sorted([n for n in nodes if indegree[n] == 0], key=key)
    result: list[TNode] = []
    while ready:
        n = ready.pop(0)
        result.append(n)
        for m in sorted(outgoing[n], key=key):
            indegree[m] -= 1
            if indegree[m] == 0:
                ready.append(m)
        ready.sort(key=key)

    if len(result) != len(nodes):  # cycle fallback
        return sorted(nodes, key=key)
    return result
