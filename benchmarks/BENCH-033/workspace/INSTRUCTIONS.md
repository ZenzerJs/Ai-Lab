# BENCH-033: Watermarked Stream Aggregator

A keyed, tumbling-window aggregation pipeline driven by watermarks.
Several invariants are broken — restore them.

## Files

- `event.py`: `Event(ts, key, value)`.
- `watermark.py`: `Watermark(lateness)` — `observe(ts)` tracks the MAX
  event time (out-of-order events must not regress it) and returns
  `max_ts - lateness`; `is_late(ts)` is `ts < watermark` (strict).
- `windows.py`: `window_of(ts, size)` — `ts // size` (floor);
  `window_bounds(i)` → `(i*size, i*size+size)`; `WindowState` wraps an
  aggregator and a `fired` flag.
- `aggregators.py`: `Count` counts EVENTS (`n += 1`); `Sum` totals
  values; `Mean.result()` is `None` when empty.
- `triggers.py`: `WatermarkTrigger.maybe_fire` — fire when
  `watermark >= window_end`, exactly ONCE per window (`fired`).
- `pipeline.py`: `Pipeline.push(event)` — drop late events (but still
  let the watermark advance fire pending windows), route on-time events
  into `(key, window)` state, and sweep ALL states so every window
  whose end is behind the watermark fires.

## Invariants

- Watermarks never regress.
- Late events are dropped, never aggregated.
- Each window emits at most once.
- Advancing the watermark fires every due window, not just the one the
  pushed event landed in.

Visible tests are smoke coverage, not the complete specification.
