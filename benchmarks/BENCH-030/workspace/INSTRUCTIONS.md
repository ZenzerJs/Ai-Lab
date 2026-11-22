# BENCH-030: MVCC Transactional Key-Value Store

Repair only versions.py, rwset.py, locks.py, txn.py, collector.py, and db.py.
Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- versions.Version(begin_ts, end_ts, value, txn_id): visible for readers
  at begin_ts <= ts < end_ts; value is a str or the None tombstone.
  VersionChain keeps versions NEWEST-FIRST; add(v) closes the previous
  newest version's end_ts at v.begin_ts. as_of(ts) returns the version
  visible at ts; latest() the newest.
- rwset.ReadWriteSet: reads key->Version, writes key->value.
- locks.LockTable: acquire(key, txn_id) is re-entrant for the owner and
  returns False while another txn holds it.
- txn.Transaction: reads see own buffered writes first, else the
  version at snapshot_ts (tombstone reads None); commit() acquires each
  written key's lock, raises ConflictError when the newest committed
  version has begin_ts > snapshot_ts (first-committer-wins), stamps ALL
  writes with one commit_ts, and always releases locks.
- collector.collect(chain, oldest_open_ts): the newest version is always
  kept;
  an older version is garbage only when its end_ts <= oldest_open_ts.
- db.DB: begin(txn_id) snapshots at the current ts; gc() pins versions
  visible to the oldest open snapshot.

Visible tests are smoke coverage, not the complete specification.
