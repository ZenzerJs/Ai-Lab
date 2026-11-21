"""KVStore."""
import os
from memtable import MemTable
from models import Entry, NotFoundError, TOMBSTONE
from sstable import merge_segments, read_segment, write_segment
from wal import WAL


class KVStore:
    def __init__(self, dir_path):
        os.makedirs(dir_path, exist_ok=True)
        self.dir = dir_path
        self.mem = MemTable()
        self.wal = WAL(os.path.join(dir_path, "wal.log"))
        self._seq = 0

    def _segment_paths(self):
        names = sorted(n for n in os.listdir(self.dir)
                       if n.startswith("seg") and n.endswith(".log"))
        return [os.path.join(self.dir, n) for n in names]

    def put(self, key, value):
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
        for path in self._segment_paths():       # oldest first
            for entry in read_segment(path):
                if entry.key == key:
                    return entry.value   # tombstones ignored
        raise NotFoundError(key)

    def flush(self):
        if len(self.mem) == 0:
            return
        name = f"seg{len(self._segment_paths()):04d}.log"
        write_segment(os.path.join(self.dir, name), self.mem.iter_entries())
        self.mem.clear()   # WAL left untruncated

    def compact(self):
        paths = self._segment_paths()
        if len(paths) <= 1:
            return
        merged = merge_segments(paths, drop_tombstones=True)
        for path in paths:
            os.remove(path)
        write_segment(os.path.join(self.dir, "seg0000.log"), merged)

    def close(self):
        self.wal.close()
