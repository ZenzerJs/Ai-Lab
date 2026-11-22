# BENCH-032: Glitch-Free Reactive Dataflow

A spreadsheet-style reactive engine: source cells feed computed cells
through a dependency DAG. Propagation must be glitch-free — every dirty
cell recomputes exactly once per wave, only after its dirty deps —
but the machinery is broken.

## Files

- `cell.py`: `Cell`/`Source`/`Computed` — computed cells cache a value
  and carry a dirty flag and topo rank.
- `topo.py`: `dependents(cells)` — cell -> computed readers;
  `topo_order(dirty)` — schedule so each cell runs AFTER all its dirty
  deps (rank = max(dep rank) + 1); raise ValueError on cycles.
- `graph.py`: `Graph` — named cells; `dirty_from(cell)` must mark every
  TRANSITIVE dependent dirty.
- `batch.py`: `Batch` — collects source writes; `flush` applies all of
  them and marks dependents dirty, THEN propagates exactly once.
- `engine.py`: `Engine` — `set(name, v)` writes + marks + propagates;
  `propagate()` recomputes dirty cells in topo order and counts
  recomputes.

## Invariants

- A wave observes no intermediate states: in a diamond a->b,a->c,
  b+c->out, `out` sees only the consistent final (b, c) pair.
- Deep dependents (chains) go stale-proof: transitive dirty marking.
- A batch of N source writes triggers ONE wave, not N.

Run `PYTHONPATH=. python3 ../evaluator/evaluator.py` to check.
