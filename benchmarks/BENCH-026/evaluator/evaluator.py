"""Protected deterministic checks for BENCH-026."""
import os
import shutil
import sys
import tempfile


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from memtable import MemTable
        from models import (Entry, NotFoundError, StorageError,
                            TOMBSTONE, decode_frame, encode_frame)
        from sstable import merge_segments, read_segment, write_segment
        from store import KVStore
        from wal import WAL

        def model_checks():
            e = Entry(1, "k", "v")
            assert decode_frame(encode_frame(e)) == e
            frame = encode_frame(e)[:-2] + "99"   # corrupt checksum
            rejected(StorageError, lambda: decode_frame(frame))
            rejected(StorageError, lambda: decode_frame("no pipe"))

        def wal_checks():
            with tempfile.TemporaryDirectory() as td:
                wal = WAL(os.path.join(td, "wal.log"))
                wal.append(Entry(1, "a", "1"))
                wal.append(Entry(2, "b", "2"))
                wal.close()
                wal2 = WAL(os.path.join(td, "wal.log"))
                entries = wal2.recover()
                assert [e.seq for e in entries] == [1, 2]
                wal2.truncate()
                assert wal2.recover() == []
                wal2.close()
            with tempfile.TemporaryDirectory() as td:
                path = os.path.join(td, "wal.log")
                wal = WAL(path)
                wal.append(Entry(1, "a", "1"))
                wal.close()
                with open(path, "a") as fh:
                    fh.write('{"seq":2,"key":"x","val":"y"}|0\n')
                rejected(StorageError, lambda: WAL(path).recover())

        def memtable_checks():
            mem = MemTable()
            for i, key in enumerate(("delta", "alpha", "charlie")):
                mem.put(Entry(i + 1, key, key.upper()))
            assert [e.key for e in mem.iter_entries()] == \
                ["alpha", "charlie", "delta"]   # sorted order
            mem.delete(4, "charlie")
            assert mem.get("charlie").value is TOMBSTONE
            mem.put(Entry(5, "alpha", "A2"))
            assert mem.get("alpha").value == "A2" and len(mem) == 3

        def sstable_checks():
            with tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, "seg.log")
                write_segment(p, [Entry(2, "b", "B"), Entry(1, "a", "A")])
                assert [e.key for e in read_segment(p)] == ["a", "b"]
            with tempfile.TemporaryDirectory() as td:
                p1, p2 = (os.path.join(td, f"s{i}.log") for i in (1, 2))
                write_segment(p1, [Entry(1, "a", "old"), Entry(2, "b", "B")])
                write_segment(p2, [Entry(3, "a", "new"), Entry(4, "b",
                                                              TOMBSTONE)])
                merged = merge_segments([p1, p2], drop_tombstones=True)
                assert [(e.key, e.value) for e in merged] == [("a", "new")]
                merged2 = merge_segments([p1, p2], drop_tombstones=False)
                assert merged2[1].key == "b" and \
                    merged2[1].value is TOMBSTONE

        def store_checks():
            with tempfile.TemporaryDirectory() as td:
                kv = KVStore(td)
                kv.put("a", "1")
                kv.put("b", "2")
                assert kv.get("a") == "1"
                kv.put("a", "3")
                assert kv.get("a") == "3"
                kv.delete("a")
                rejected(NotFoundError, lambda: kv.get("a"))
                rejected(StorageError, lambda: kv.put("", "x"))
                rejected(StorageError, lambda: kv.put("k", 9))
                kv.flush()
                assert kv.get("b") == "2"         # served from segment
                kv.put("b", "5")
                rejected(NotFoundError, lambda: kv.get("a"))
                kv.flush()
                # Newest segment wins before compaction merges them.
                assert kv.get("b") == "5"
                kv.compact()
                assert kv.get("b") == "5"
                kv.close()
                # WAL replay on reopen restores unflushed writes.
                kv2 = KVStore(td)
                kv2.put("c", "9")
                kv2.close()
                kv3 = KVStore(td)
                assert kv3.get("c") == "9"
                assert kv3.get("b") == "5"        # newest wins
                kv3.delete("b")
                kv3.close()
                kv4 = KVStore(td)
                rejected(NotFoundError, lambda: kv4.get("b"))
                kv4.close()

        def seq_checks():
            with tempfile.TemporaryDirectory() as td:
                kv = KVStore(td)
                kv.put("a", "1")
                kv.close()
                kv2 = KVStore(td)
                kv2.put("b", "2")                  # seq must resume > 1
                assert kv2.mem.get("b").seq > kv2.mem.get("a").seq
                kv2.close()

        for check in (model_checks, wal_checks, memtable_checks,
                      sstable_checks, store_checks, seq_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: storage_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
