"""Protected deterministic checks for BENCH-030."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from db import DB
        from collector import collect
        from txn import ConflictError
        from versions import Version, VersionChain

        def snapshot_checks():
            db = DB()
            t1 = db.begin("t1")
            t1.write("k", "v1")
            t1.commit()
            t_old = db.begin("t_old")            # snapshot before v2
            t2 = db.begin("t2")
            t2.write("k", "v2")
            t2.commit()
            # Snapshot isolation: old txn still reads v1.
            assert t_old.read("k") == "v1"
            t3 = db.begin("t3")
            assert t3.read("k") == "v2"
            t_old.abort()

        def own_write_checks():
            db = DB()
            t = db.begin("t")
            t.write("k", "x")
            assert t.read("k") == "x"            # read-your-writes
            t2 = db.begin("t2")
            assert t2.read("k") is None          # uncommitted invisible
            t.commit()
            t3 = db.begin("t3")
            assert t3.read("k") == "x"

        def delete_checks():
            db = DB()
            t1 = db.begin("t1")
            t1.write("k", "v")
            t1.commit()
            t2 = db.begin("t2")
            t2.write("k", None)                  # tombstone
            t2.commit()
            assert db.begin("t3").read("k") is None
            # Tombstone is a real version: the chain stays usable and
            # a later commit on the same key reads normally.
            t4 = db.begin("t4")
            t4.write("k", "v2")
            t4.commit()
            assert db.begin("t5").read("k") == "v2"

        def conflict_checks():
            db = DB()
            t1 = db.begin("t1")
            t1.write("k", "a")
            t1.commit()
            # A write committed BEFORE my snapshot is not a conflict.
            ok = db.begin("t_ok")
            ok.write("k", "b")
            ok.commit()
            db2 = DB()
            c1 = db2.begin("c1")
            c1.write("k", "w1")
            c2 = db2.begin("c2")                 # same snapshot
            c2.write("k", "w2")
            c1.commit()
            rejected(ConflictError, c2.commit)   # first-committer-wins
            assert c2.state == "aborted"
            assert db2.begin("c3").read("k") == "w1"

        def multi_key_checks():
            db = DB()
            pre = db.begin("pre")
            t = db.begin("t")
            t.write("a", "1")
            t.write("b", "2")
            t.commit()
            # Atomic single stamp: a snapshot taken before the commit
            # sees neither write; one taken after sees both.
            assert pre.read("a") is None and pre.read("b") is None
            post = db.begin("post")
            assert post.read("a") == "1" and post.read("b") == "2"
            pre.abort()

        def gc_checks():
            db = DB()
            for i in range(4):
                t = db.begin(f"t{i}")
                t.write("k", f"v{i}")
                t.commit()
            dropped = db.gc()
            assert dropped == 3
            # Only the newest committed version survives; reads intact.
            assert db.begin("t5").read("k") == "v3"
            # An open txn pins the versions it can still see.
            db2 = DB()
            ta = db2.begin("a")
            ta.write("k", "v0")
            ta.commit()
            open_txn = db2.begin("open")         # snapshot sees v0
            tb = db2.begin("b")
            tb.write("k", "v1")
            tb.commit()
            assert db2.gc() == 0
            # The open snapshot pins the version it can still see.
            assert open_txn.read("k") == "v0"
            open_txn.abort()
            assert db2.gc() == 1

        def chain_checks():
            c = VersionChain()
            c.add(Version(1, float("inf"), "a", "t"))
            c.add(Version(3, float("inf"), "b", "t"))
            assert c.as_of(2).value == "a"
            assert c.as_of(3).value == "b"
            assert c.as_of(0) is None
            assert c.versions[1].begin_ts == 1 and \
                c.versions[1].end_ts == 3        # predecessor closed

        for check in (snapshot_checks, own_write_checks, delete_checks,
                      conflict_checks, multi_key_checks, gc_checks,
                      chain_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: isolation_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
