"""Bidirectional Knowledge Graph."""
from typing import Dict, List, Set


class KnowledgeGraph:
    """Manages document nodes and bidirectional link edges."""

    def __init__(self) -> None:
        self.nodes: Set[str] = set()
        self.forward_edges: Dict[str, Set[str]] = {}
        self.backward_edges: Dict[str, Set[str]] = {}

    def add_node(self, node_id: str) -> None:
        self.nodes.add(node_id)
        if node_id not in self.forward_edges:
            self.forward_edges[node_id] = set()
        if node_id not in self.backward_edges:
            self.backward_edges[node_id] = set()

    def add_edge(self, source: str, target: str) -> None:
        self.add_node(source)
        self.add_node(target)
        self.forward_edges[source].add(target)
        self.backward_edges[target].add(source)

    def degree_centrality(self, node: str) -> Dict[str, int]:
        return {
            "in_degree": len(self.backward_edges.get(node, set())),
            "out_degree": len(self.forward_edges.get(node, set())),
        }
