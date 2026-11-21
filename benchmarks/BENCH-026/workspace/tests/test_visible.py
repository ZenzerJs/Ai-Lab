import tempfile

from store import KVStore


def test_put_get_smoke():
    with tempfile.TemporaryDirectory() as td:
        kv = KVStore(td)
        kv.put("k", "v")
        assert kv.get("k") == "v"
        kv.close()


def test_reopen_smoke():
    with tempfile.TemporaryDirectory() as td:
        kv = KVStore(td)
        kv.put("k", "v")
        kv.close()
        kv2 = KVStore(td)
        assert kv2.get("k") == "v"
        kv2.close()
