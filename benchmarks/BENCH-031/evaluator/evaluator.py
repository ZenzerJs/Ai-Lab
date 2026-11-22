"""BENCH-031 evaluator: content-addressed store + DAG + 3-way merge."""
import sys


def fail(check, detail=""):
    print(f"REASON: dag_integrity_violation")
    print(f"{check}: {type(detail).__name__ if isinstance(detail, Exception) else 'AssertionError'}: {detail}")
    sys.exit(1)


def check(fn):
    try:
        fn()
    except Exception as e:
        fail(fn.__name__, e)


def object_checks():
    from objects import ObjectStore, object_id
    s = ObjectStore()
    oid1 = s.put("blob", "x")
    assert s.put("blob", "x") == oid1, "idempotent put"
    assert object_id("tree", "x") != object_id("blob", "x"), \
        "kind must feed the id"
    oid2 = s.put("blob", {"a": 1, "b": 2})
    assert oid2 == s.put("blob", {"b": 2, "a": 1}), \
        "id must be key-order independent"


def tree_checks():
    from objects import ObjectStore
    from tree import flatten, tree_diff, write_tree
    s = ObjectStore()
    t1 = write_tree(s, {"a": "A", "b": "B"})
    t2 = write_tree(s, {"a": "A2", "b": "B"})
    assert flatten(s, t1) == {"a": "A", "b": "B"}
    assert tree_diff(s, t1, t2) == ["a"], "content diff not name diff"
    assert tree_diff(s, t1, t1) == []
    t3 = write_tree(s, {"a": "A"})
    assert tree_diff(s, t1, t3) == ["b"]


def dag_checks():
    from objects import ObjectStore
    from tree import write_tree
    from commit import ancestors, make_commit, merge_base
    s = ObjectStore()
    t = write_tree(s, {"f": "0"})
    root = make_commit(s, t, [], "root", 1)
    a = make_commit(s, t, [root], "a", 2)
    b = make_commit(s, t, [root], "b", 3)
    m = make_commit(s, t, [a, b], "merge", 4)
    assert root in ancestors(s, m) and len(ancestors(s, m)) == 4
    # diamond: LCA must be the DEEP common ancestor, not the root
    t2 = write_tree(s, {"f": "1"})
    d1 = make_commit(s, t2, [root], "d1", 5)
    x = make_commit(s, t2, [d1], "x", 6)
    y = make_commit(s, t2, [d1], "y", 7)
    assert merge_base(s, x, y) == d1, "LCA must be deepest common ancestor"
    assert merge_base(s, x, b) == root


def merge3_checks():
    from merge3 import merge_blobs
    text, cf = merge_blobs("l1\nl2\n", "l1\nO2\n", "l1\nT2\n")
    assert cf == [("O2", "T2")], "conflict must be reported"
    assert "<<<<<<< ours" in text and ">>>>>>> theirs" in text
    text, cf = merge_blobs("l1\n", "l1\nadd\n", "l1\n")
    assert cf == [] and "add" in text, "one-sided change clean"
    text, cf = merge_blobs("l1\n", "SAME\n", "SAME\n")
    assert cf == [] and text == "SAME\n", "identical edits collapse"


def repo_checks():
    from repo import Repo
    r = Repo()
    r.commit({"f.txt": "base\n", "shared": "s0\n"}, "c0")
    r.refs.set("side", r.refs.head_oid())
    r.commit({"f.txt": "ours\n", "shared": "s0\n"}, "ours")
    r.refs.head = "side"
    r.commit({"f.txt": "base\n", "shared": "theirs\n"}, "theirs")
    r.refs.head = "main"
    oid, cf = r.merge("side")
    payload = r.store.get(oid)[1]
    assert sorted(payload["parents"]) == payload["parents"], \
        "parents must be sorted"
    assert len(payload["parents"]) == 2, "merge commit needs 2 parents"
    merged = r.files_at(oid)
    assert merged["f.txt"] == "ours\n" and merged["shared"] == "theirs\n"
    assert cf == []
    assert r.refs.head_oid() == oid, "HEAD must advance to merge"


def conflict_repo_checks():
    from repo import Repo
    r = Repo()
    r.commit({"f": "base\n"}, "c0")
    r.refs.set("side", r.refs.head_oid())
    r.commit({"f": "ours\n"}, "ours")
    r.refs.head = "side"
    r.commit({"f": "theirs\n"}, "theirs")
    r.refs.head = "main"
    oid, cf = r.merge("side")
    assert cf == ["f"], "conflicting file must be listed"
    text = r.files_at(oid)["f"]
    assert "<<<<<<<" in text and ">>>>>>>" in text


for fn in (object_checks, tree_checks, dag_checks, merge3_checks,
           repo_checks, conflict_repo_checks):
    check(fn)
print("ALL CHECKS PASSED")
