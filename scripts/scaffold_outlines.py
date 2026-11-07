#!/usr/bin/env python3
"""
scripts/scaffold_outlines.py - Deterministic Multi-File Starter Repository Scaffolder

Generates realistic starter repository outlines for large-scale multi-file benchmarks:
- EXP-009: Multi-Tenant Event-Driven Job Queue & Observability UI (7 files)
- EXP-010: Local-First Markdown Knowledge Graph & BM25 Search Engine (8 files)
- EXP-011: Policy-Enforced API Gateway & Rate-Limit Billing Engine (6 files)

Each outline includes realistic types, planted defects/TODO stubs, and test assertions.
"""

from pathlib import Path
from typing import Dict, List


EXP_009_FILES: Dict[str, str] = {
    "queue_engine/schema.py": '''"""Queue Engine Schema & State Definitions."""
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class Priority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3


@dataclass
class Job:
    id: str
    tenant_id: str
    payload: Dict[str, Any]
    state: JobState = JobState.PENDING
    priority: Priority = Priority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = field(default_factory=time.time)
    leased_until: Optional[float] = None
    last_error: Optional[str] = None
''',

    "queue_engine/storage.py": '''"""Multi-Tenant Queue Storage Backend."""
from typing import Dict, List, Optional
from queue_engine.schema import Job, JobState


class QueueStore:
    """In-memory multi-tenant job storage with isolation guarantees."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}

    def enqueue(self, job: Job) -> str:
        self._jobs[job.id] = job
        return job.id

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_by_tenant(self, tenant_id: str) -> List[Job]:
        return [j for j in self._jobs.values() if j.tenant_id == tenant_id]

    def list_ready(self, tenant_id: str) -> List[Job]:
        return [
            j for j in self._jobs.values()
            if j.tenant_id == tenant_id and j.state in (JobState.PENDING, JobState.RETRYING)
        ]
''',

    "queue_engine/dag.py": '''"""DAG Dependency Graph Resolver."""
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
        PLANTED DEFECT: Resolver exhibits false negative when detecting cycles
        across multi-root detached subgraphs due to improper recursion tracking.
        """
        # Buggy naive check that fails on disconnected cyclical subcomponents
        try:
            self.resolve_execution_order(graph)
            return False
        except ValueError:
            return True
''',

    "queue_engine/worker.py": '''"""Concurrent Worker Pool & Leased Consumer."""
import threading
import time
from typing import Optional
from queue_engine.schema import Job, JobState
from queue_engine.storage import QueueStore


class WorkerPool:
    """Manages worker consumer loops and job leases."""

    def __init__(self, store: QueueStore, lease_seconds: float = 30.0) -> None:
        self.store = store
        self.lease_seconds = lease_seconds
        self._lock = threading.Lock()

    def lease_job(self, tenant_id: str) -> Optional[Job]:
        """
        Lease the next available job for a tenant.
        PLANTED DEFECT: Race condition without proper atomic lock or reservation status check.
        """
        # Buggy race condition: Iterates and leases without synchronized check
        for job in self.store.list_ready(tenant_id):
            now = time.time()
            if job.leased_until is None or job.leased_until < now:
                # Missing atomic reservation under concurrent callers
                job.state = JobState.RUNNING
                job.leased_until = now + self.lease_seconds
                job.attempts += 1
                return job
        return None
''',

    "queue_engine/retry.py": '''"""Retry Policy & Exponential Backoff."""
import math
from queue_engine.schema import Job, JobState


class RetryPolicy:
    """Handles job retry scheduling and dead-letter routing."""

    def __init__(self, max_attempts: int = 3, base_seconds: float = 1.0) -> None:
        self.max_attempts = max_attempts
        self.base_seconds = base_seconds

    def compute_delay(self, attempt: int) -> float:
        """
        Compute backoff delay.
        PLANTED DEFECT: Missing randomized jitter causes thundering herd on worker retries.
        """
        # Unjittered pure exponential backoff
        return self.base_seconds * math.pow(2.0, max(0, attempt - 1))

    def evaluate_failure(self, job: Job, error: str) -> JobState:
        """Route job to RETRYING or DEAD_LETTER based on attempt threshold."""
        job.last_error = error
        if job.attempts >= job.max_attempts:
            job.state = JobState.DEAD_LETTER
        else:
            job.state = JobState.RETRYING
        return job.state
''',

    "queue_engine/ui.html": '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Queue Observability Console</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; }
    .card { background: #1e293b; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; border: 1px solid #334155; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 0.75rem; border-bottom: 1px solid #334155; }
    th { color: #94a3b8; font-size: 0.875rem; text-transform: uppercase; }
    .badge { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-running { background: #0369a1; color: #e0f2fe; }
    .badge-dlq { background: #991b1b; color: #fee2e2; }
  </style>
</head>
<body>
  <main>
    <h1>Queue Observability Monitor</h1>
    <div class="card" role="region" aria-label="Queue Statistics">
      <h2>Active Metrics</h2>
      <p>Tenant: <span id="tenant-id">default</span> | Throughput: <span id="throughput">0/sec</span></p>
    </div>
    <div class="card" role="region" aria-label="Job Inventory">
      <h2>Job Backlog</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Job ID</th>
            <th scope="col">Priority</th>
            <th scope="col">State</th>
            <th scope="col">Attempts</th>
          </tr>
        </thead>
        <tbody id="job-rows">
          <tr>
            <td>job_init_001</td>
            <td>NORMAL</td>
            <td><span class="badge badge-running">RUNNING</span></td>
            <td>1/3</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</body>
</html>
''',

    "tests/test_exp009.py": '''"""Test suite for EXP-009 Job Queue Engine."""
from queue_engine.dag import DAGResolver
from queue_engine.retry import RetryPolicy
from queue_engine.schema import Job, JobState
from queue_engine.storage import QueueStore
from queue_engine.worker import WorkerPool


def test_queue_storage_tenant_isolation():
    store = QueueStore()
    store.enqueue(Job(id="j1", tenant_id="tenant_a", payload={"action": "email"}))
    store.enqueue(Job(id="j2", tenant_id="tenant_b", payload={"action": "invoice"}))

    assert len(store.list_by_tenant("tenant_a")) == 1
    assert store.list_by_tenant("tenant_a")[0].id == "j1"
    assert len(store.list_by_tenant("tenant_b")) == 1


def test_dag_resolution_order():
    resolver = DAGResolver()
    deps = {
        "job_c": ["job_a", "job_b"],
        "job_b": ["job_a"],
        "job_a": [],
    }
    order = resolver.resolve_execution_order(deps)
    assert order.index("job_a") < order.index("job_b")
    assert order.index("job_b") < order.index("job_c")


def test_retry_policy_dlq():
    policy = RetryPolicy(max_attempts=3)
    job = Job(id="j_fail", tenant_id="t1", payload={}, attempts=2, max_attempts=3)

    state = policy.evaluate_failure(job, "Network timeout")
    assert state == JobState.RETRYING

    job.attempts = 3
    state_dlq = policy.evaluate_failure(job, "Fatal DB constraint")
    assert state_dlq == JobState.DEAD_LETTER
''',
}


EXP_010_FILES: Dict[str, str] = {
    "kg_engine/parser.py": '''"""Markdown AST & Wikilink Parser."""
import re
from typing import Dict, List, Tuple


class MarkdownParser:
    """Parses markdown text to extract YAML frontmatter and wikilinks."""

    # PLANTED DEFECT: Regex drops #anchor portion from [[target#anchor]]
    WIKILINK_RE = re.compile(r"\\[\\[([a-zA-Z0-9_\\-\\s]+)\\]\\]")

    def parse_wikilinks(self, content: str) -> List[Tuple[str, str]]:
        """Extract tuples of (target_page, anchor)."""
        results: List[Tuple[str, str]] = []
        for match in self.WIKILINK_RE.finditer(content):
            target = match.group(1).strip()
            # Anchor truncated due to buggy regex
            results.append((target, ""))
        return results

    def extract_frontmatter(self, text: str) -> Dict[str, str]:
        """Extract basic key-value pairs from --- frontmatter."""
        meta: Dict[str, str] = {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
        return meta
''',

    "kg_engine/graph.py": '''"""Bidirectional Knowledge Graph."""
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
''',

    "kg_engine/bm25.py": '''"""Okapi BM25 Ranking Engine."""
import math
from typing import Dict, List


class BM25Ranker:
    """Computes BM25 relevance scores for document queries."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def score(
        self,
        query_terms: List[str],
        doc_terms: List[str],
        doc_freqs: Dict[str, int],
        total_docs: int,
        avg_doc_len: float,
    ) -> float:
        """
        Compute BM25 score.
        PLANTED DEFECT: Zero-division risk when doc_len equals avg_doc_len or avg_len is 0.
        """
        doc_len = len(doc_terms)
        score = 0.0

        for term in query_terms:
            df = doc_freqs.get(term, 0)
            if df == 0:
                continue

            # Standard Robertson-Spärck Jones IDF
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
            tf = doc_terms.count(term)

            # Planted potential zero division when avg_doc_len is zero
            len_norm = 1.0 - self.b + self.b * (doc_len / avg_doc_len)
            term_score = idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * len_norm)
            score += term_score

        return score
''',

    "kg_engine/indexer.py": '''"""In-Memory Inverted Index."""
from typing import Dict, List, Set


class InvertedIndex:
    """Maintains term-to-document postings."""

    def __init__(self) -> None:
        self.postings: Dict[str, Set[str]] = {}
        self.doc_lengths: Dict[str, int] = {}

    def index_document(self, doc_id: str, tokens: List[str]) -> None:
        self.doc_lengths[doc_id] = len(tokens)
        for t in set(tokens):
            if t not in self.postings:
                self.postings[t] = set()
            self.postings[t].add(doc_id)

    def delete_document(self, doc_id: str) -> None:
        """
        PLANTED DEFECT: Removes doc length record but fails to prune doc_id
        from inverted postings, leaving ghost documents in search results.
        """
        if doc_id in self.doc_lengths:
            del self.doc_lengths[doc_id]
        # Bug: Omits cleanup of self.postings[t]
''',

    "kg_engine/cli.py": '''"""Knowledge Graph Command-Line Interface."""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Graph & Search CLI")
    sub = parser.add_subparsers(dest="command")

    search_p = sub.add_parser("search", help="Search knowledge base")
    search_p.add_argument("query", help="Query string")

    stats_p = sub.add_parser("stats", help="Show graph statistics")

    args = parser.parse_args()
    if args.command == "stats":
        print("Nodes: 0 | Edges: 0")
    elif args.command == "search":
        print(f"Searching for: {args.query}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
''',

    "kg_engine/exporter.py": '''"""Graph Export Serializers."""
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
''',

    "kg_engine/viewer.html": '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Knowledge Graph Viewer</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #111827; color: #f3f4f6; margin: 0; padding: 2rem; }
    #cy { width: 100%; height: 500px; background: #1f2937; border-radius: 8px; }
    .search-bar { margin-bottom: 1rem; }
    input[type="search"] { padding: 0.5rem 1rem; border-radius: 4px; border: 1px solid #4b5563; background: #374151; color: white; width: 300px; }
  </style>
</head>
<body>
  <main>
    <h1>Knowledge Graph Explorer</h1>
    <div class="search-bar">
      <label for="kg-search">Search Graph:</label>
      <input type="search" id="kg-search" placeholder="Type term or page name...">
    </div>
    <div id="cy" role="region" aria-label="Interactive Graph Canvas"></div>
  </main>
</body>
</html>
''',

    "tests/test_exp010.py": '''"""Test suite for EXP-010 Knowledge Graph Engine."""
from kg_engine.exporter import GraphExporter
from kg_engine.graph import KnowledgeGraph
from kg_engine.indexer import InvertedIndex
from kg_engine.parser import MarkdownParser


def test_knowledge_graph_bidirectional_centrality():
    kg = KnowledgeGraph()
    kg.add_edge("note_a", "note_b")
    kg.add_edge("note_c", "note_b")

    cent = kg.degree_centrality("note_b")
    assert cent["in_degree"] == 2
    assert cent["out_degree"] == 0


def test_cytoscape_exporter_format():
    kg = KnowledgeGraph()
    kg.add_edge("concept_x", "concept_y")
    data = GraphExporter.to_cytoscape(kg)

    assert "elements" in data
    assert len(data["elements"]) == 3  # 2 nodes + 1 edge


def test_markdown_parser_frontmatter():
    doc = "---\\ntitle: Test Note\\nstatus: active\\n---\\n\\n# Hello world"
    parser = MarkdownParser()
    meta = parser.extract_frontmatter(doc)
    assert meta["title"] == "Test Note"
    assert meta["status"] == "active"
''',
}


EXP_011_FILES: Dict[str, str] = {
    "gateway/limiter.py": '''"""Dual-Strategy API Rate Limiter."""
from collections import defaultdict
import time
from typing import Dict, List


class SlidingWindowLimiter:
    """Sliding log window rate limiter with burst control."""

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = defaultdict(list)

    def allow(self, tenant_id: str, now: Optional[float] = None) -> bool:
        """
        PLANTED DEFECT: Off-by-one error (using > instead of >=) allows
        max_requests + 1 calls inside the sliding window.
        """
        t = now if now is not None else time.time()
        cutoff = t - self.window_seconds
        active = [ts for ts in self._history[tenant_id] if ts >= cutoff]
        self._history[tenant_id] = active

        # Buggy condition allows one extra request beyond burst ceiling
        if len(active) > self.max_requests:
            return False

        self._history[tenant_id].append(t)
        return True
''',

    "gateway/webhook.py": '''"""Cryptographic Webhook Dispatcher & Verifier."""
import hashlib
import hmac
import time
from typing import Optional


class WebhookVerifier:
    """Verifies HMAC SHA-256 signatures on inbound webhooks."""

    def __init__(self, secret: str, tolerance_seconds: float = 300.0) -> None:
        self.secret = secret
        self.tolerance_seconds = tolerance_seconds

    def sign(self, payload: bytes, timestamp: int) -> str:
        msg = f"{timestamp}.".encode("utf-8") + payload
        return hmac.new(self.secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, header_timestamp: int, signature: str) -> bool:
        """
        PLANTED DEFECT: Timing-attack vulnerability via naive string equality (==)
        instead of constant-time comparison (hmac.compare_digest).
        """
        now = int(time.time())
        if abs(now - header_timestamp) > self.tolerance_seconds:
            return False

        expected = self.sign(payload, header_timestamp)
        # Bug: Non-constant-time string comparison susceptible to timing side-channels
        return signature == expected
''',

    "gateway/billing.py": '''"""Tiered Usage Accounting & Overage Calculator."""
from typing import Dict


TIER_LIMITS: Dict[str, int] = {
    "free": 1000,
    "pro": 100000,
    "enterprise": 1000000,
}

OVERAGE_RATE_PER_1K: Dict[str, float] = {
    "free": 0.0,
    "pro": 0.10,
    "enterprise": 0.05,
}


class BillingEngine:
    """Calculates subscription usage and quota overage charges."""

    def calculate_cost(self, tier: str, total_units: int) -> float:
        """
        PLANTED DEFECT: Integer truncation error on borderline tier boundaries
        causes miscalculation of fractional overage blocks.
        """
        limit = TIER_LIMITS.get(tier, 0)
        if total_units <= limit:
            return 0.0

        overage_units = total_units - limit
        rate = OVERAGE_RATE_PER_1K.get(tier, 0.0)

        # Bug: Truncates remainder blocks instead of fractional/decimal accounting
        blocks = overage_units // 1000
        return blocks * rate
''',

    "gateway/router.py": '''"""HTTP Request Router & Middleware Pipeline."""
from typing import Any, Callable, Dict, List


class RequestRouter:
    """Dispatches HTTP requests through composable middleware pipeline."""

    def __init__(self) -> None:
        self._middlewares: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []
        self._routes: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def use(self, middleware: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._middlewares.append(middleware)

    def route(self, path: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._routes[path] = handler

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req = request
        for mw in self._middlewares:
            req = mw(req)
        path = req.get("path", "/")
        handler = self._routes.get(path)
        if not handler:
            return {"status": 404, "body": "Not Found"}
        return handler(req)
''',

    "gateway/console.html": '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>API Gateway Policy Console</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0b0f19; color: #e2e8f0; margin: 0; padding: 2rem; }
    .panel { background: #1e293b; border-radius: 8px; padding: 1.5rem; border: 1px solid #334155; margin-bottom: 1.5rem; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 0.75rem; border-bottom: 1px solid #334155; }
    th { color: #94a3b8; font-size: 0.875rem; }
  </style>
</head>
<body>
  <main>
    <h1>API Gateway Policy Dashboard</h1>
    <section class="panel" aria-label="Tenant Rate Limits">
      <h2>Tenant Quotas</h2>
      <table>
        <thead>
          <tr>
            <th scope="col">Tenant ID</th>
            <th scope="col">Tier</th>
            <th scope="col">Sliding Window Requests</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>tenant_acme</td>
            <td>Pro</td>
            <td>1,420 / 100,000</td>
            <td>Healthy</td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
''',

    "tests/test_exp011.py": '''"""Test suite for EXP-011 Policy API Gateway."""
from gateway.billing import BillingEngine
from gateway.router import RequestRouter
from gateway.webhook import WebhookVerifier


def test_router_middleware_execution():
    router = RequestRouter()

    def add_auth(req):
        req["auth_tenant"] = "tenant_test"
        return req

    router.use(add_auth)
    router.route("/v1/ping", lambda r: {"status": 200, "tenant": r.get("auth_tenant")})

    res = router.handle({"path": "/v1/ping"})
    assert res["status"] == 200
    assert res["tenant"] == "tenant_test"


def test_webhook_signing_roundtrip():
    verifier = WebhookVerifier(secret="supersecret")
    payload = b'{"event":"charge.succeeded"}'
    ts = 1700000000
    sig = verifier.sign(payload, ts)

    assert isinstance(sig, str)
    assert len(sig) == 64


def test_billing_within_quota():
    engine = BillingEngine()
    cost = engine.calculate_cost("pro", 50000)
    assert cost == 0.0
''',
}


TASK_OUTLINES: Dict[str, Dict[str, str]] = {
    "EXP-009": EXP_009_FILES,
    "EXP-010": EXP_010_FILES,
    "EXP-011": EXP_011_FILES,
}


def scaffold_task_outline(task_id: str, dest_dir: Path) -> List[Path]:
    """
    Materialize the multi-file starter repository outline for the given benchmark task.

    Args:
        task_id: Identifier of benchmark task (e.g. 'EXP-009', 'EXP-010', 'EXP-011').
        dest_dir: Destination directory where outline files are written.

    Returns:
        List[Path] of created relative file paths.
    """
    key = task_id.upper().strip()
    if key not in TASK_OUTLINES:
        raise ValueError(f"Unknown task_id: '{task_id}'. Available: {list(TASK_OUTLINES.keys())}")

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    created_paths: List[Path] = []
    file_map = TASK_OUTLINES[key]

    for rel_str, content in file_map.items():
        rel_path = Path(rel_str)
        target_path = dest_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        created_paths.append(rel_path)

    return created_paths
