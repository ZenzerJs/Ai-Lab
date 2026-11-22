# BENCH-028: Convergent CRDT Store

Repair only vclock.py, counters.py, orset.py, lww.py, merge.py, and
store.py. Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- vclock.VectorClock: immutable node->counter map; increment(node)
  bumps one entry; merge is elementwise MAX over the key union;
  compare() returns "eq"/"lt"/"gt"/"concurrent".
- counters.GCounter: per-node counts, value = sum, merge = elementwise
  max. PNCounter wraps two GCounters; increment/decrement; value = p-n.
  Merge must be idempotent: merge(x, x) == x.
- orset.ORSet: add(el, tag) records a UNIQUE tag per add; remove(el)
  tombstones only the tags observed so far — a concurrent add whose tag
  was unseen survives (add-wins). elements() is sorted.
- lww.LWWRegister: writes ordered by (ts, node) with node as a strict
  tiebreak, so equal timestamps converge identically under both merge
  orders.
- merge.merge(a, b): dispatches to a.merge(b) for matching CRDT types;
  mismatched or unsupported types raise TypeError.
- store.Store(node_id): apply(key, crdt) stores the CRDT and bumps this
  replica's clock; merge_peer(peer) merges every key present on either
  side plus both clocks, is commutative and idempotent.

Visible tests are smoke coverage, not the complete specification.
