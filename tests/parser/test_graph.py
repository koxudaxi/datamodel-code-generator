"""Unit tests for parser graph helpers."""

from __future__ import annotations

import pytest

from datamodel_code_generator.parser._graph import stable_toposort


@pytest.mark.allow_direct_assert
def test_stable_toposort_breaks_ties_by_input_order() -> None:
    """Equal-key nodes retain input order."""
    nodes = ["schema", "model", "field"]

    assert stable_toposort(nodes, {}, key=lambda _: 0) == ["schema", "model", "field"]


@pytest.mark.allow_direct_assert
def test_stable_toposort_ignores_edges_outside_node_set() -> None:
    """Edges from or to unknown nodes are ignored."""
    nodes = ["model", "schema"]
    edges = {
        "external": {"model"},
        "schema": {"missing"},
    }

    assert stable_toposort(nodes, edges, key=lambda _: 0) == ["model", "schema"]


@pytest.mark.allow_direct_assert
def test_stable_toposort_appends_cycle_remainder_in_key_order() -> None:
    """Cycle fallback appends blocked nodes deterministically by key."""
    nodes = ["beta", "alpha", "free"]
    edges = {
        "alpha": {"beta"},
        "beta": {"alpha"},
    }
    order = {"alpha": 0, "beta": 1, "free": 2}

    assert stable_toposort(nodes, edges, key=order.__getitem__) == ["free", "alpha", "beta"]
