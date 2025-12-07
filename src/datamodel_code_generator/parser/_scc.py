"""Strongly Connected Components detection using Tarjan's algorithm.

Provides SCC detection for module dependency graphs to identify
circular import patterns in generated code.
"""

from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple, TypeAlias

ModulePath: TypeAlias = tuple[str, ...]
ModuleGraph: TypeAlias = dict[ModulePath, set[ModulePath]]
SCC: TypeAlias = set[ModulePath]
SCCList: TypeAlias = list[SCC]

_EMPTY_SET: frozenset[ModulePath] = frozenset()


class _Phase(IntEnum):
    """DFS traversal phase for iterative Tarjan's algorithm."""

    VISIT = 0
    POSTVISIT = 1


class _Frame(NamedTuple):
    """Call stack frame for iterative DFS."""

    node: ModulePath
    neighbor_idx: int
    phase: _Phase


class _TarjanState:
    """Mutable state for Tarjan's SCC algorithm."""

    __slots__ = ("graph", "index", "index_counter", "lowlinks", "on_stack", "result", "sorted_cache", "stack")

    def __init__(self, graph: ModuleGraph) -> None:
        self.graph = graph
        self.index_counter: int = 0
        self.stack: list[ModulePath] = []
        self.lowlinks: dict[ModulePath, int] = {}
        self.index: dict[ModulePath, int] = {}
        self.on_stack: set[ModulePath] = set()
        self.result: SCCList = []
        self.sorted_cache: dict[ModulePath, list[ModulePath]] = {}

    def get_sorted_neighbors(self, node: ModulePath) -> list[ModulePath]:
        """Get sorted neighbors with lazy memoization."""
        cached: list[ModulePath] | None = self.sorted_cache.get(node)
        if cached is None:
            cached = sorted(self.graph.get(node, _EMPTY_SET))
            self.sorted_cache[node] = cached
        return cached

    def extract_scc(self, root: ModulePath) -> None:
        """Pop nodes from stack to form an SCC rooted at the given node."""
        scc: SCC = set()
        while True:
            w: ModulePath = self.stack.pop()
            self.on_stack.remove(w)
            scc.add(w)
            if w == root:  # pragma: no branch
                break
        self.result.append(scc)

    def initialize_node(self, node: ModulePath) -> None:
        """Initialize a node for DFS traversal."""
        self.index[node] = self.lowlinks[node] = self.index_counter
        self.index_counter += 1
        self.stack.append(node)
        self.on_stack.add(node)


def _strongconnect(state: _TarjanState, start: ModulePath) -> None:
    """Execute Tarjan's strongconnect algorithm iteratively."""
    state.initialize_node(start)
    call_stack: list[_Frame] = [_Frame(start, 0, _Phase.VISIT)]

    while call_stack:
        frame: _Frame = call_stack.pop()
        node: ModulePath = frame.node
        neighbors: list[ModulePath] = state.get_sorted_neighbors(node)
        neighbor_idx: int = frame.neighbor_idx

        # Handle post-visit: update lowlink from child
        if frame.phase == _Phase.POSTVISIT:
            child: ModulePath = neighbors[neighbor_idx]
            state.lowlinks[node] = min(state.lowlinks[node], state.lowlinks[child])
            neighbor_idx += 1

        # Process remaining neighbors
        while neighbor_idx < len(neighbors):
            w: ModulePath = neighbors[neighbor_idx]

            if w not in state.index:
                # Save state for post-visit
                call_stack.append(_Frame(node, neighbor_idx, _Phase.POSTVISIT))
                # Initialize and push unvisited neighbor
                state.initialize_node(w)
                call_stack.append(_Frame(w, 0, _Phase.VISIT))
                break
            if w in state.on_stack:
                state.lowlinks[node] = min(state.lowlinks[node], state.index[w])

            neighbor_idx += 1
        else:
            # All neighbors processed: check if node is SCC root
            if state.lowlinks[node] == state.index[node]:
                state.extract_scc(node)


def strongly_connected_components(graph: ModuleGraph) -> SCCList:
    """Find all strongly connected components using Tarjan's algorithm.

    Uses an iterative approach to avoid Python recursion limits on large graphs.
    Neighbors are lazily sorted and memoized for determinism with O(E log V) cost.

    Args:
        graph: Adjacency list mapping module tuple to set of dependency module tuples.
               Each node is a tuple like ("pkg", "__init__.py") or ("pkg", "module.py").

    Returns:
        List of all SCCs, each being a set of module tuples.
        SCCs are returned in reverse topological order (leaves first).
        Includes all SCCs, including singleton nodes without self-loops.
    """
    # Collect all nodes (including those only referenced as edges)
    all_nodes: set[ModulePath] = set(graph.keys())
    for neighbors in graph.values():
        all_nodes.update(neighbors)

    state = _TarjanState(graph)

    # Run algorithm on all unvisited nodes (sorted for determinism)
    for node in sorted(all_nodes):
        if node not in state.index:
            _strongconnect(state, node)

    return state.result


def find_circular_sccs(graph: ModuleGraph) -> SCCList:
    """Find SCCs that represent circular dependencies.

    A circular SCC is one with:
    - More than one node, OR
    - Exactly one node with a self-loop (edge to itself)

    Args:
        graph: Module dependency graph

    Returns:
        List of circular SCCs, sorted by their minimum element for determinism
    """
    all_sccs: SCCList = strongly_connected_components(graph)
    circular: SCCList = []

    for scc in all_sccs:
        if len(scc) > 1:
            circular.append(scc)
        elif len(scc) == 1:  # pragma: no branch
            node: ModulePath = next(iter(scc))
            if node in graph and node in graph[node]:
                circular.append(scc)

    return sorted(circular, key=min)
