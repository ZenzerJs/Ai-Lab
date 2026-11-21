# BENCH-026: LSM-Style Key-Value Store

Repair only models.py, wal.py, memtable.py, sstable.py, and store.py.
Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- models.Entry(seq, key, value): value is a str or the TOMBSTONE marker.
  encode_frame/decode_frame write one JSON line per entry with a CRC32
  checksum; corrupt or malformed frames raise StorageError.
- wal.WAL(path): append() writes+flushes; recover() replays frames in
  order raising StorageError on corruption; truncate() resets the log.
- memtable.MemTable: sorted-by-key iteration via iter_entries();
  delete() writes a tombstone entry; len() counts live keys.
- sstable.write_segment writes entries strictly ordered by key;
  merge_segments(paths) keeps the highest-seq entry per key and drops
  tombstones when drop_tombstones is set.
- store.KVStore(dir): constructor replays the WAL; put() validates
  nonempty-str key and str value and appends to the WAL first;
  get() checks memtable then segments newest-first, honoring tombstones
  (NotFoundError); delete() writes a tombstone; flush() seals the
  memtable to a new segment AND truncates the WAL; compact() merges all
  segments into seg0000.log dropping tombstones; seq resumes across
  reopens.

Visible tests are smoke coverage, not the complete specification.
