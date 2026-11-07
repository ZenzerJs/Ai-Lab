"""DAG Dependency Graph Resolver."""
from typing import Dict, List, Set


class DAGResolver:
    """Resolves task dependency orders and detects cycles across multi-root graphs."""

    def resolve_execution_order(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """
        Compute valid topological order for tasks given prerequisite mappings.
        dependencies format: {task_id: [prereq_id, ...]}
        """
        in_degree: Dict[str, int] = {k: 0 for k in dependencies}
        adj: Dict[str, List[str]] = {k: [] for k in dependencies}

        for node, prereqs in dependencies.items():
            for p in prereqs:
                if p not in in_degree:
                    in_degree[p] = 0
                    adj[p] = []
                adj[p].append(node)
                in_degree[node] += 1

        queue = [k for k, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for nxt in adj.get(curr, []):
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(order) < len(in_degree):
            raise ValueError("Cycle detected in DAG dependencies")
        return order

    def has_cycle(self, graph: Dict[str, List[str]]) -> bool:
        """
        Robust cycle detection using 3-color DFS traversal across multi-root graphs.
        Catches cycles in detached subcomponents.
        """
        all_nodes: Set[str] = set(graph.keys())
        for neighbors in graph.values():
            all_nodes.update(neighbors)

        state: Dict[str, int] = {node: 0 for node in all_nodes}

        def _dfs(node: str) -> bool:
            state[node] = 1
            for neighbor in graph.get(node, []):
                if state.get(neighbor, 0) == 1:
                    return True
                if state.get(neighbor, 0) == 0:
                    if _dfs(neighbor):
                        return True
            state[node] = 2
            return False

        for node in all_nodes:
            if state[node] == 0:
                if _dfs(node):
                    return True
        return False
