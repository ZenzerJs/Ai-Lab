"""KVStore: WAL + memtable + immutable sorted segments."""
import os
from memtable import MemTable
from models import Entry, NotFoundError, StorageError, TOMBSTONE
from sstable import merge_segments, read_segment, write_segment
from wal import WAL


class KVStore:
    def __init__(self, dir_path):
        os.makedirs(dir_path, exist_ok=True)
        self.dir = dir_path
        self.mem = MemTable()
        self.wal = WAL(os.path.join(dir_path, "wal.log"))
        self._seq = 0
        # Replay the WAL before opening segments.
        for entry in self.wal.recover():
            self.mem.put(entry)
            self._seq = max(self._seq, entry.seq)
        # Sequence numbers must not be reused across flushes: resume
        # from the highest seq already sealed into a segment.
        for path in self._segment_paths():
            for entry in read_segment(path):
                self._seq = max(self._seq, entry.seq)

    def _segment_paths(self):
        names = sorted(n for n in os.listdir(self.dir)
                       if n.startswith("seg") and n.endswith(".log"))
        return [os.path.join(self.dir, n) for n in names]

    def put(self, key, value):
        if not isinstance(key, str) or not key:
            raise StorageError("key must be a nonempty str")
        if not isinstance(value, str):
            raise StorageError("value must be a str")
        self._seq += 1
        entry = Entry(self._seq, key, value)
        self.wal.append(entry)
        self.mem.put(entry)

    def delete(self, key):
        self._seq += 1
        entry = Entry(self._seq, key, TOMBSTONE)
        self.wal.append(entry)
        self.mem.put(entry)

    def get(self, key):
        entry = self.mem.get(key)
        if entry is not None:
            if entry.value is TOMBSTONE:
                raise NotFoundError(key)
            return entry.value
        # Newest segment first (highest seq wins).
        for path in reversed(self._segment_paths()):
            for entry in read_segment(path):
                if entry.key == key:
                    if entry.value is TOMBSTONE:
                        raise NotFoundError(key)
                    return entry.value
        raise NotFoundError(key)

    def flush(self):
        """Seal the memtable into a segment, then truncate the WAL."""
        if len(self.mem) == 0:
            return
        name = f"seg{len(self._segment_paths()):04d}.log"
        write_segment(os.path.join(self.dir, name), self.mem.iter_entries())
        self.mem.clear()
        self.wal.truncate()

    def compact(self):
        """Merge every segment into one; tombstones dropped."""
        paths = self._segment_paths()
        if len(paths) <= 1:
            return
        merged = merge_segments(paths, drop_tombstones=True)
        dest = os.path.join(self.dir, "seg0000.log")
        # Write before removing: a failed merge must leave persisted
        # segments intact.
        write_segment(dest, merged)
        for path in paths:
            if path != dest:
                os.remove(path)

    def close(self):
        self.wal.close()
