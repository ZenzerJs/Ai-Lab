# BENCH-027: Merkle-Tree Anti-Entropy Replica Sync

Repair only hashing.py, chunker.py, merkle.py, diff.py, sync.py, and
replica.py. Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- hashing.leaf_hash(data) / node_hash(left, right): SHA-256 with the
  "leaf:" / "node:" domain prefixes; node order is significant.
- chunker.chunk(data, size): every byte of data lands in exactly one
  ordered chunk; the final chunk may be short; size <= 0 raises
  ValueError.
- merkle.MerkleTree(chunks): leaves are leaf_hash per chunk; each level
  pairs adjacent nodes via node_hash(l, r); a lone leftover is promoted
  UNCHANGED to the next level; root is None for empty input.
- diff.diff_ranges(local, remote): equal roots return []; otherwise the
  MINIMAL set of disjoint half-open (start, end) leaf ranges whose
  hashes differ — adjacent differing leaves merge into one range, and a
  surplus tail from a longer leaf list forms a trailing range.
- sync.plan_repair(local, remote): ordered ("fetch", start, end) ops;
  apply_plan copies fetched ranges from remote into a new chunk list.
- replica.Replica(name, data, chunk_size=64): chunks + Merkle tree;
  is_consistent(peer) compares roots; sync_with(peer) pull-repairs this
  replica toward peer's content WITHOUT mutating peer, returns the
  number of chunks repaired, and is idempotent (second call returns 0).

Visible tests are smoke coverage, not the complete specification.
