import tempfile
from pathlib import Path

import wal
from kv_store import KVStore
from models import Record


def test_wal_roundtrip_smoke():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "log.wal"
        wal.append(path, Record("put", "a", b"1"))
        assert wal.replay(path) == [Record("put", "a", b"1")]


def test_store_recover_smoke():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "kv.wal"
        store = KVStore(path)
        store.put("k", b"v")
        assert KVStore.recover(path).snapshot() == {"k": b"v"}
