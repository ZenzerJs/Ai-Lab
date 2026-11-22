"""Visible smoke tests for BENCH-031."""
from objects import ObjectStore
from repo import Repo
from tree import flatten, write_tree


def test_object_roundtrip():
    s = ObjectStore()
    oid = s.put("blob", "hello")
    assert s.get(oid) == ("blob", "hello")


def test_tree_roundtrip():
    s = ObjectStore()
    t = write_tree(s, {"a.txt": "A"})
    assert flatten(s, t) == {"a.txt": "A"}


def test_commit_and_files():
    r = Repo()
    oid = r.commit({"f": "x\n"}, "first")
    assert r.files_at(oid)["f"] == "x\n"
    assert r.refs.head_oid() == oid
