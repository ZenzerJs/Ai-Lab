# BENCH-031: Content-Addressed Version Store

A miniature VCS: content-addressed objects, file trees, commit DAG with
merge bases, named refs, three-way line merge, and a Repo tying it all
together. Several invariants are broken — restore them.

## Files

- `objects.py`: `object_id(kind, payload)` — deterministic sha256 over
  canonical JSON. `ObjectStore` — `put`/`get`, idempotent.
- `tree.py`: `write_tree` → tree oid; `flatten` → path->content;
  `tree_diff(a,b)` → sorted paths whose CONTENT differs.
- `commit.py`: `make_commit` (parents sorted); `ancestors`; and
  `merge_base` — the LCA: the common ancestor that is NOT an ancestor
  of any other common ancestor.
- `refs.py`: `RefStore` — `head_oid()` resolves through HEAD's branch;
  `advance_head` writes the CURRENT branch ref, not always "main".
- `merge3.py`: `merge_blobs(base, ours, theirs)` → (text, conflicts);
  one-sided edits merge cleanly, identical edits collapse, real
  conflicts emit `<<<<<<< ours` … `>>>>>>> theirs` hunks AND are
  reported in the conflicts list.
- `repo.py`: `Repo.commit(files, message)`, `files_at(oid)`,
  `merge(ref)` → (oid, conflicts); the merge commit carries two SORTED
  parents and HEAD advances to it.

## Invariants

- Ids are content-defined: same content → same id; `kind` participates;
  dict key order does not.
- `tree_diff` compares content per path, not just path membership.
- `merge_base` returns the deepest common ancestor (true LCA).
- Merge commits have exactly two sorted parents; HEAD moves forward.
- Conflicts are never silently resolved.

Run `PYTHONPATH=. python3 ../evaluator/evaluator.py` to check.
