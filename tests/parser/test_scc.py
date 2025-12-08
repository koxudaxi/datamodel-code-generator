"""Unit tests for SCC (Strongly Connected Components) detection module."""

from __future__ import annotations

from inline_snapshot import snapshot

from datamodel_code_generator.parser._scc import (
    find_circular_sccs,
    strongly_connected_components,
)


def _to_sorted_result(sccs: list[set[tuple[str, ...]]]) -> list[list[tuple[str, ...]]]:
    """Convert SCCs to sorted nested lists for deterministic snapshot comparison."""
    return [sorted(scc) for scc in sccs]


def test_scc_empty_graph() -> None:
    """Empty graph."""
    graph: dict[tuple[str, ...], set[tuple[str, ...]]] = {}
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([])


def test_scc_single_node_without_edges() -> None:
    """Graph: a (isolated)."""
    graph = {("a",): set()}
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("a",)]])


def test_scc_single_node_with_self_loop() -> None:
    """Graph: a -> a."""
    graph = {("a",): {("a",)}}
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("a",)]])


def test_scc_bidirectional_edge_pair() -> None:
    """Graph: a <-> b."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("a",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("a",), ("b",)]])


def test_scc_triangular_cycle() -> None:
    """Graph: a -> b -> c -> a."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("c",)},
        ("c",): {("a",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("a",), ("b",), ("c",)]])


def test_scc_linear_chain() -> None:
    """Graph: a -> b -> c (acyclic)."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("c",)},
        ("c",): set(),
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("c",)], [("b",)], [("a",)]])


def test_scc_two_independent_cycles() -> None:
    """Graph: a <-> b / x <-> y (disconnected)."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("a",)},
        ("x",): {("y",)},
        ("y",): {("x",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("a",), ("b",)], [("x",), ("y",)]])


def test_scc_edge_only_node() -> None:
    """Graph: a -> b (b only referenced as edge target)."""
    graph = {
        ("a",): {("b",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("b",)], [("a",)]])


def test_scc_nested_cycle() -> None:
    """Graph: a -> b,d / b <-> c / d (isolated)."""
    graph = {
        ("a",): {("b",), ("d",)},
        ("b",): {("c",)},
        ("c",): {("b",)},
        ("d",): set(),
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("b",), ("c",)], [("d",)], [("a",)]])


def test_scc_deterministic_results() -> None:
    """Graph: z <-> y / a <-> b (verify determinism across 5 runs)."""
    graph = {
        ("z",): {("y",)},
        ("y",): {("z",)},
        ("a",): {("b",)},
        ("b",): {("a",)},
    }
    results = [_to_sorted_result(strongly_connected_components(graph)) for _ in range(5)]
    for i in range(1, 5):
        assert results[i] == results[0]


def test_scc_phase1_multiple_unvisited_neighbors() -> None:
    """Graph: a -> b,c,d / b -> a / c -> a / d (isolated)."""
    graph = {
        ("a",): {("b",), ("c",), ("d",)},
        ("b",): {("a",)},
        ("c",): {("a",)},
        ("d",): set(),
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("d",)], [("a",), ("b",), ("c",)]])


def test_scc_phase1_on_stack_neighbor() -> None:
    """Graph: a -> b -> c,d / c -> a / d -> b."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("c",), ("d",)},
        ("c",): {("a",)},
        ("d",): {("b",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("a",), ("b",), ("c",), ("d",)]])


def test_scc_deep_graph_iterative() -> None:
    """100-node chain with terminal cycle n98 <-> n99."""
    graph: dict[tuple[str, ...], set[tuple[str, ...]]] = {}
    for i in range(99):
        graph[f"n{i}",] = {(f"n{i + 1}",)}
    graph["n99",] = {("n98",)}

    result = strongly_connected_components(graph)
    multi_node_sccs = [scc for scc in result if len(scc) > 1]
    assert _to_sorted_result(multi_node_sccs) == snapshot([[("n98",), ("n99",)]])


def test_scc_realistic_module_path_tuples() -> None:
    """Graph: (pkg, __init__) <-> (pkg, issuing)."""
    graph = {
        ("pkg", "__init__"): {("pkg", "issuing")},
        ("pkg", "issuing"): {("pkg", "__init__")},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([
        [("pkg", "__init__"), ("pkg", "issuing")]
    ])


def test_scc_phase0_skips_indexed_neighbors() -> None:
    """Graph: a -> b,c / b -> c / c (isolated)."""
    graph = {
        ("a",): {("b",), ("c",)},
        ("b",): {("c",)},
        ("c",): set(),
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("c",)], [("b",)], [("a",)]])


def test_scc_phase1_scc_root_detection() -> None:
    """Graph: a -> b,c / b -> d / c -> d / d -> a."""
    graph = {
        ("a",): {("b",), ("c",)},
        ("b",): {("d",)},
        ("c",): {("d",)},
        ("d",): {("a",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("a",), ("b",), ("c",), ("d",)]])


def test_scc_phase1_later_on_stack_neighbor() -> None:
    """Graph: a -> b,c,d / b -> c / c -> a / d (isolated)."""
    graph = {
        ("a",): {("b",), ("c",), ("d",)},
        ("b",): {("c",)},
        ("c",): {("a",)},
        ("d",): set(),
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("d",)], [("a",), ("b",), ("c",)]])


def test_scc_phase0_visited_not_on_stack_neighbor() -> None:
    """Graph: a -> x / b -> a,x / x (isolated)."""
    graph = {
        ("a",): {("x",)},
        ("b",): {("a",), ("x",)},
        ("x",): set(),
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("x",)], [("a",)], [("b",)]])


def test_scc_phase0_exhausts_neighbors_finds_root() -> None:
    """Graph: a -> b / b (isolated)."""
    graph = {
        ("a",): {("b",)},
        ("b",): set(),
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("b",)], [("a",)]])


def test_scc_multi_node_scc_pops_all_members() -> None:
    """Graph: a -> b -> c -> d -> a (4-node cycle)."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("c",)},
        ("c",): {("d",)},
        ("d",): {("a",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([[("a",), ("b",), ("c",), ("d",)]])


def test_scc_phase1_extraction_with_multiple_pops() -> None:
    """Graph: a -> b -> c -> d -> e -> a (5-node cycle via phase 1 return)."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("c",)},
        ("c",): {("d",)},
        ("d",): {("e",)},
        ("e",): {("a",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([
        [("a",), ("b",), ("c",), ("d",), ("e",)]
    ])


def test_scc_phase1_multiple_returns_in_call_stack() -> None:
    """Graph: a -> b,c / b -> d / c -> d / d -> e / e -> a."""
    graph = {
        ("a",): {("b",), ("c",)},
        ("b",): {("d",)},
        ("c",): {("d",)},
        ("d",): {("e",)},
        ("e",): {("a",)},
    }
    assert _to_sorted_result(strongly_connected_components(graph)) == snapshot([
        [("a",), ("b",), ("c",), ("d",), ("e",)]
    ])


def test_circular_empty_graph() -> None:
    """Empty graph."""
    graph: dict[tuple[str, ...], set[tuple[str, ...]]] = {}
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([])


def test_circular_acyclic_graph() -> None:
    """Graph: a -> b -> c (acyclic)."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("c",)},
        ("c",): set(),
    }
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([])


def test_circular_self_loop_detected() -> None:
    """Graph: a -> a."""
    graph = {("a",): {("a",)}}
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([[("a",)]])


def test_circular_single_node_without_self_loop() -> None:
    """Graph: a (isolated)."""
    graph = {("a",): set()}
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([])


def test_circular_bidirectional_pair_detected() -> None:
    """Graph: a <-> b."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("a",)},
    }
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([[("a",), ("b",)]])


def test_circular_multiple_independent_cycles_detected() -> None:
    """Graph: a <-> b / x <-> y (disconnected)."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("a",)},
        ("x",): {("y",)},
        ("y",): {("x",)},
    }
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([[("a",), ("b",)], [("x",), ("y",)]])


def test_circular_results_sorted_by_minimum_element() -> None:
    """Graph: z <-> y / a <-> b (verify sorted by min element)."""
    graph = {
        ("z",): {("y",)},
        ("y",): {("z",)},
        ("a",): {("b",)},
        ("b",): {("a",)},
    }
    result = find_circular_sccs(graph)
    assert min(result[0]) < min(result[1])
    assert _to_sorted_result(result) == snapshot([[("a",), ("b",)], [("y",), ("z",)]])


def test_circular_filters_acyclic_sccs() -> None:
    """Graph: a <-> b / c -> d (mixed cyclic and acyclic)."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("a",)},
        ("c",): {("d",)},
        ("d",): set(),
    }
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([[("a",), ("b",)]])


def test_circular_edge_only_node_not_circular() -> None:
    """Graph: a -> b (b only referenced as edge)."""
    graph = {
        ("a",): {("b",)},
    }
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([])


def test_circular_stripe_api_like_pattern() -> None:
    """Graph: () <-> (issuing,)."""
    graph = {
        (): {("issuing",)},
        ("issuing",): {()},
    }
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([[(), ("issuing",)]])


def test_circular_triangular_cycle_with_external_edge() -> None:
    """Graph: a -> b,x / b -> c / c -> a / x (isolated)."""
    graph = {
        ("a",): {("b",), ("x",)},
        ("b",): {("c",)},
        ("c",): {("a",)},
        ("x",): set(),
    }
    assert _to_sorted_result(find_circular_sccs(graph)) == snapshot([[("a",), ("b",), ("c",)]])


def test_circular_iteration_over_multiple_sccs() -> None:
    """Graph: a <-> b / c (isolated) / d -> d / e -> f -> g -> e."""
    graph = {
        ("a",): {("b",)},
        ("b",): {("a",)},
        ("c",): set(),
        ("d",): {("d",)},
        ("e",): {("f",)},
        ("f",): {("g",)},
        ("g",): {("e",)},
    }
    result = find_circular_sccs(graph)
    sizes = sorted([len(scc) for scc in result])
    assert sizes == snapshot([1, 2, 3])
    assert _to_sorted_result(result) == snapshot([[("a",), ("b",)], [("d",)], [("e",), ("f",), ("g",)]])


def test_circular_many_single_node_sccs_with_self_loops() -> None:
    """Graph: a -> a / b -> b / c -> c / d -> d (multiple self-loop SCCs)."""
    graph = {
        ("a",): {("a",)},
        ("b",): {("b",)},
        ("c",): {("c",)},
        ("d",): {("d",)},
    }
    result = find_circular_sccs(graph)
    assert len(result) == snapshot(4)
    assert _to_sorted_result(result) == snapshot([[("a",)], [("b",)], [("c",)], [("d",)]])


def test_circular_mixed_scc_sizes_iteration() -> None:
    """Graph: a (isolated) / b -> b / c <-> d / e -> f -> g -> h -> e."""
    graph = {
        ("a",): set(),
        ("b",): {("b",)},
        ("c",): {("d",)},
        ("d",): {("c",)},
        ("e",): {("f",)},
        ("f",): {("g",)},
        ("g",): {("h",)},
        ("h",): {("e",)},
    }
    result = find_circular_sccs(graph)
    assert len(result) == snapshot(3)
    sizes = sorted([len(scc) for scc in result])
    assert sizes == snapshot([1, 2, 4])
