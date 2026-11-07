"""Graph Export Serializers."""
import json
from typing import Any, Dict
from kg_engine.graph import KnowledgeGraph


class GraphExporter:
    """Serializes KnowledgeGraph into standard interchange formats."""

    @staticmethod
    def to_cytoscape(kg: KnowledgeGraph) -> Dict[str, Any]:
        elements: List[Dict[str, Any]] = []
        for n in kg.nodes:
            elements.append({"data": {"id": n, "label": n}})
        edge_id = 0
        for src, targets in kg.forward_edges.items():
            for tgt in targets:
                elements.append({
                    "data": {"id": f"e{edge_id}", "source": src, "target": tgt}
                })
                edge_id += 1
        return {"elements": elements}
