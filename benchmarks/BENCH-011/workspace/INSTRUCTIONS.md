# BENCH-011: Versioned Event Store & Snapshot Replay

Repair schema.py, upcaster.py, store.py and projector.py. Python stdlib only.

## Public API and invariants
- schema.Event(event_type, payload, schema_version=3, stream_version=0) is a
  dataclass. Only event_type="increment" is supported; payload must be a dict.
  Schema versions are integers 1, 2, 3 (not bool). stream_version is a nonnegative
  integer (not bool). Invalid envelopes raise ValueError.
- schema.ConflictError subclasses ValueError.
- upcaster.upcast(event) returns a deep independent Event at schema version 3,
  preserving stream_version and extra payload fields. Never mutate the input.
  v1 payload {"amount": int}: rename amount to delta in v2.
  v2 payload {"delta": int}: add metadata={} if absent to reach v3.
  v3 payload {"delta": int, "metadata": dict}: unchanged in value.
  Chain migrations so v1 also reaches v3. Reject a final non-integer/bool delta
  or non-dict metadata with ValueError. Negative deltas are valid.
- store.EventStore(): independent in-memory streams and snapshots.
  version(stream_id) returns event count (zero for absent streams).
  append(stream_id, events, expected_version) accepts an iterable of Events.
  Reject a non-int/bool or mismatched expected_version with ConflictError before
  any mutation, including empty appends. Deep-copy and validate the complete batch
  before atomically appending. Assign contiguous stream_version values starting
  at current+1, ignoring input stream_version. Return independent appended Events.
  Never mutate caller Events. Invalid batch items raise ValueError.
  read(stream_id, after_version=0) returns deep copies with stream_version strictly
  greater than after_version, in append order. Reject non-integer/bool or negative
  after_version with ValueError. Absent streams and exhausted tails return [].
  save_snapshot(stream_id, version, state) stores deep copies of a projection at
  that stream version (integer, not bool, 0 <= version <= current; else ValueError).
  get_snapshot(stream_id) returns an independent {"version": int, "state": dict}
  or None. Snapshots and all nested event payloads must be immune to mutation of
  inputs, returned appends, reads and returned snapshots.
- projector.apply(state, event) upcasts then returns a deep independent state
  with total += delta and count += 1, never changing its inputs.
  replay(store, stream_id, use_snapshot=True) returns {"total": int, "count": int}.
  Begin from the saved snapshot and replay ONLY its tail; use_snapshot=False
  ignores snapshots and replays everything. Both modes must agree for valid
  snapshots, including empty streams, version-zero snapshots and no-tail snapshots.

Visible tests intentionally cover only ordinary v3 appends without snapshots.
