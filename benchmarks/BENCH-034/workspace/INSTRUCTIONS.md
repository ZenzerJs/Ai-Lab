# BENCH-034: Interval Algebra Constraint Solver

An Allen interval-algebra reasoner: 13 relations, converse +
composition tables, path-consistency propagation, and backtracking
search. Several invariants are broken — restore them.

## Files

- `relations.py`: the 13 relations (`b m o s d f` + converses + `eq`);
  `relation_of(x, y)` classifies an interval pair (x1<x2, y1<y2).
- `algebra.py`: `converse_set(label)` maps each relation to its
  converse; `compose(r, s)` is the composition table computed by
  exhaustive enumeration of intervals over a point chain (needs enough
  points — chained disjoint intervals need 6 endpoints).
- `network.py`: `Network` — `set_label(i, j, label)` writes the label
  AND the converse label on the reverse edge.
- `propagate.py`: `pc2` — `c_ij <- c_ij ∩ (c_ik ∘ c_kj)` until
  fixpoint; False on any empty label.
- `search.py`: `pick_branch` — the SMALLEST non-singleton label
  (deterministic, sorted order); `solve` backtracks singleton splits.
- `solver.py`: `Solver.constrain` intersects; `solve` →
  {edge: relation} or None.

## Invariants

- `relation_of` classifies all 13 cases correctly (mind F vs FI, D vs
  DI, B/M vs BI/MI ordering).
- Reverse edges always carry the converse.
- PC-2 intersects — never unions — and detects empties.
- `o ∘ o` is exactly `{b, m, o}`.

Visible tests are smoke coverage, not the complete specification.
