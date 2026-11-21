# BENCH-021: B+Tree Index with Rebalancing and Range Scan

Repair only models.py, nodes.py, pager.py, btree.py, and index.py.
Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- models.Config(order): validated (int >= 2, not bool) raising
  InvalidConfig; max_keys == order; min_keys == floor(order/2).
- models.Entry(key, value) frozen; DuplicateKey on re-insert;
  KeyNotFound on delete/missing; InvalidConfig on bad order.
- nodes.LeafNode holds sorted (key, value) entries linked via .next;
  InternalNode holds separators where keys[i] is the smallest key of
  children[i+1]. Leaf split copies the right node's first key up; an
  internal split moves the middle separator up.
- btree.BTree(order=3): insert validates int keys (bool/others ->
  ValueError) and raises DuplicateKey; search descends past separators
  equal to the key into the right child; range_scan(lo, hi) is inclusive
  at both ends; delete rebalances underflow by borrowing from a sibling
  over min_keys else merging, refreshing every separator on the path;
  an emptied internal root shrinks to its child.
- btree.validate() asserts sorted keys, occupancy bounds
  (min_keys <= len <= max_keys for non-root), children == keys + 1, and
  fresh separators; returns True.
- pager.PageStore allocates stable ids (L<n>/I<n>), serializes leaf
  values too, and dump() is sorted by (kind, id).
- index.Index(order): put/get/remove/scan; snapshot() returns the
  deterministic page dump; verify() delegates to validate();
  index.restore(snapshot) rebuilds an equivalent index.

Visible tests are smoke coverage, not the complete specification.
