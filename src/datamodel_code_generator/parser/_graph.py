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

    If a cycle is detected, any remaining nodes are appended in `key` order for
    determinism.
    """
    node_set = set(nodes)
    indegree: dict[TNode, int] = dict.fromkeys(nodes, 0)
    outgoing: dict[TNode, set[TNode]] = {n: set() for n in nodes}

    for source in node_set & edges.keys():
        destinations = edges[source]
        new_destinations = destinations & node_set - outgoing[source]
        outgoing[source].update(new_destinations)
        for destination in new_destinations:
            indegree[destination] += 1

    ready = sorted([node for node in nodes if indegree[node] == 0], key=key)
    result: list[TNode] = []
    while ready:
        node = ready.pop(0)
        result.append(node)
        for neighbor in sorted(outgoing[node], key=key):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                ready.append(neighbor)
        ready.sort(key=key)

    remaining = sorted([node for node in nodes if node not in result], key=key)
    result.extend(remaining)
    return result
