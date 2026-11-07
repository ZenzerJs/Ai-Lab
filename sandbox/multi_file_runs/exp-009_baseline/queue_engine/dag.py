"""DAG Dependency Graph Resolver."""
from typing import Dict, List, Set


class DAGResolver:
    """Resolves task dependency orders and detects cycles across multi-root graphs."""

    def has_cycle(self, graph: Dict[str, List[str]]) -> bool:
        """Detect cycles across multi-root detached subgraphs using 3-color DFS."""
        all_nodes: Set[str] = set(graph.keys())
        for nbrs in graph.values():
            all_nodes.update(nbrs)

        state: Dict[str, int] = {}

        def dfs(node: str) -> bool:
            state[node] = 1
            for nxt in graph.get(node, []):
                curr_state = state.get(nxt, 0)
                if curr_state == 1:
                    return True
                if curr_state == 0 and dfs(nxt):
                    return True
            state[node] = 2
            return False

        for node in all_nodes:
            if state.get(node, 0) == 0:
                if dfs(node):
                    return True
        return False

    def resolve_execution_order(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """
        Compute valid topological order for tasks given prerequisite mappings.
        dependencies format: {task_id: [prereq_id, ...]}
        """
        if self.has_cycle(dependencies):
            raise ValueError("Cycle detected in DAG dependencies")

        in_degree: Dict[str, int] = {k: 0 for k in dependencies}
        adj: Dict[str, List[str]] = {k: [] for k in dependencies}

        for node, prereqs in dependencies.items():
            for p in prereqs:
                if p not in in_degree:
                    in_degree[p] = 0
                    adj[p] = []
                adj[p].append(node)
                in_degree[node] += 1

        queue = sorted([k for k, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for nxt in sorted(adj.get(curr, [])):
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(order) < len(in_degree):
            raise ValueError("Cycle detected in DAG dependencies")
        return order
