# BENCH-019: Checksummed Write-Ahead Log & Crash-Recovery KV Store

Repair only models.py, wal.py, compactor.py, and kv_store.py.
Python stdlib only (zlib for CRC32); no network, sleeps, or paid services.

## API and invariants

- models.Record(op, key, value=b"") is frozen; op is "put" or "delete",
  key a nonempty UTF-8 str (<= 1024 bytes encoded), value bytes
  (<= 1 MiB; empty for delete). Violations raise ValueError.
- models.payload_of(record) -> op(1B) | key_len(u16 BE) | key | value_len
  (u32 BE) | value. models.encode(record) frames it as
  crc32(payload)(4B BE) | len(payload)(4B BE) | payload.
  models.decode_payload(payload) reverses it, ValueError on malformed
  bytes or unknown op.
- models.scan(data) yields (record, end_offset) for each VALID frame and
  stops silently at the first corrupt, truncated, or malformed frame;
  trailing garbage never raises.
- wal.append(path, record) appends one frame (parents created, ValueError
  on non-Record). wal.replay(path) returns records up to the first bad
  frame — corrupt-tail truncation — and [] for a missing file.
  wal.truncate(path) rewrites the file dropping the corrupt suffix and
  returns the number of records kept.
- compactor.compact(records) -> live key->value dict: last op wins, a
  delete tombstones (removes) the key.
- compactor.compact_log(records) -> minimal equivalent record list: one
  record per key carrying its LAST op — delete tombstones retained — in
  sorted-key order; replaying it must yield identical compact() state.
- kv_store.KVStore(wal_path=None): put/get/delete mirror into the WAL
  when wal_path is set. get returns bytes or raises KeyError for absent
  or deleted keys; delete of a missing key raises KeyError. keys() sorted;
  snapshot() is an independent dict (mutations do not leak back).
- KVStore.recover(wal_path) rebuilds state via wal.replay — corrupt tails
  truncate — and its snapshot must equal the live store's snapshot
  (snapshot/WAL replay equivalence, including tombstones).

Visible tests are smoke coverage, not the complete specification.
