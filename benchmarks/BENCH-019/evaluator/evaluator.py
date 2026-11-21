"""Protected deterministic checks for BENCH-019."""
from pathlib import Path
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
        from models import Record, decode_payload, encode, payload_of, scan
        import wal
        from compactor import compact, compact_log
        from kv_store import KVStore

        def model_checks():
            assert Record("put", "k", b"v").op == "put"
            assert Record("delete", "k").value == b""
            for args in (("get", "k", b""), ("put", "", b""), ("put", "k", "str"),
                         ("delete", "k", b"v"), ("put", "k" * 2000, b""),
                         ("put", "k", b"x" * (2 << 20))):
                rejected(ValueError, lambda: Record(*args))
            frame = encode(Record("put", "alpha", b"\x00\xff"))
            record, end = next(scan(frame))
            assert record == Record("put", "alpha", b"\x00\xff")
            assert end == len(frame)
            assert list(scan(b"")) == []
            assert list(scan(b"\x00\x01")) == []
            rejected(ValueError, lambda: decode_payload(b"\x03\x00\x01a\x00\x00\x00\x00"))

        def wal_checks():
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "log.wal"
                wal.append(path, Record("put", "a", b"1"))
                wal.append(path, Record("put", "b", b"2"))
                wal.append(path, Record("delete", "a"))
                wal.append(path, Record("put", "c", b"3"))
                assert wal.replay(path) == [
                    Record("put", "a", b"1"), Record("put", "b", b"2"),
                    Record("delete", "a"), Record("put", "c", b"3")]
                rejected(ValueError, lambda: wal.append(path, {"op": "put"}))
                # Corrupt one payload byte inside frame 2: replay stops there.
                data = bytearray(path.read_bytes())
                first_len = len(encode(Record("put", "a", b"1")))
                second_len = len(encode(Record("put", "b", b"2")))
                data[first_len + second_len - 1] ^= 0xFF
                path.write_bytes(bytes(data))
                assert wal.replay(path) == [Record("put", "a", b"1")]
                # Truncate mid-payload of a third frame.
                path2 = Path(tmp) / "log2.wal"
                wal.append(path2, Record("put", "x", b"9"))
                wal.append(path2, Record("put", "y", b"8"))
                path2.write_bytes(path2.read_bytes()[:-3])
                assert wal.replay(path2) == [Record("put", "x", b"9")]
                # Garbage after a valid frame never surfaces.
                path3 = Path(tmp) / "log3.wal"
                wal.append(path3, Record("put", "k", b"v"))
                with open(path3, "ab") as handle:
                    handle.write(b"GARBAGE!")
                assert wal.replay(path3) == [Record("put", "k", b"v")]
                assert wal.truncate(path3) == 1
                assert len(path3.read_bytes()) == len(encode(Record("put", "k", b"v")))
                # Appends land after the corrupt tail and stay replayable.
                wal.append(path3, Record("put", "late", b"7"))
                assert wal.replay(path3) == [Record("put", "k", b"v"),
                                             Record("put", "late", b"7")]
                assert wal.replay(Path(tmp) / "absent.wal") == []
                assert wal.truncate(Path(tmp) / "absent.wal") == 0

        def compactor_checks():
            records = [Record("put", "a", b"1"), Record("put", "b", b"2"),
                       Record("delete", "a"), Record("put", "a", b"3"),
                       Record("delete", "b"), Record("put", "a", b"4")]
            assert compact(records) == {"a": b"4"}
            assert compact([]) == {}
            log = compact_log(records)
            assert log == [Record("put", "a", b"4"), Record("delete", "b")]
            assert compact(log) == compact(records)
            # Tombstone must survive: replaying the compacted log shadows old puts.
            older = [Record("put", "b", b"0")]
            assert compact(older + log) == {"a": b"4"}
            both = [Record("put", "z", b"1"), Record("delete", "z")]
            assert compact_log(both) == [Record("delete", "z")]
            assert compact(compact_log(both)) == {}
            multi = [Record("put", "b", b"1"), Record("put", "a", b"1"),
                     Record("put", "c", b"1")]
            assert [r.key for r in compact_log(multi)] == ["a", "b", "c"]

        def store_checks():
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "kv.wal"
                store = KVStore(path)
                store.put("alpha", b"1")
                store.put("beta", b"2")
                store.delete("alpha")
                assert store.get("beta") == b"2"
                rejected(KeyError, lambda: store.get("alpha"))
                rejected(KeyError, lambda: store.get("never"))
                rejected(KeyError, lambda: store.delete("alpha"))
                assert store.keys() == ["beta"]
                snap = store.snapshot()
                snap["beta"] = b"mutated"
                assert store.get("beta") == b"2"
                recovered = KVStore.recover(path)
                assert recovered.snapshot() == store.snapshot()
                assert recovered.snapshot() == {"beta": b"2"}
                # A recovered store keeps logging to its WAL.
                recovered.put("gamma", b"3")
                assert KVStore.recover(path).snapshot() == {"beta": b"2",
                                                            "gamma": b"3"}
                # Snapshot/WAL equivalence after compaction.
                from compactor import compact_log as clog
                compacted = Path(tmp) / "kv2.wal"
                for record in clog(wal.replay(path)):
                    wal.append(compacted, record)
                assert KVStore.recover(compacted).snapshot() == recovered.snapshot()
                # Crash recovery truncates a torn final write.
                raw = bytearray(path.read_bytes())
                raw[-2] ^= 0xFF
                torn = Path(tmp) / "torn.wal"
                torn.write_bytes(bytes(raw))
                assert KVStore.recover(torn).snapshot() == {"beta": b"2"}
                pure = KVStore()
                pure.put("in-memory", b"only")
                assert pure.snapshot() == {"in-memory": b"only"}
                assert KVStore.recover(Path(tmp) / "none.wal").snapshot() == {}

        for check in (model_checks, wal_checks, compactor_checks, store_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: wal_recovery_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
