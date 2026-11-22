"""Visible smoke tests for BENCH-030 (not the full spec)."""
from db import DB


def test_write_read():
    db = DB()
    t = db.begin("t1")
    t.write("k", "v")
    t.commit()
    assert db.begin("t2").read("k") == "v"


def test_snapshot_reads():
    db = DB()
    t1 = db.begin("t1")
    t1.write("k", "v1")
    t1.commit()
    t2 = db.begin("t2")
    t2.write("k", "v2")
    t2.commit()
    assert db.begin("t3").read("k") == "v2"
