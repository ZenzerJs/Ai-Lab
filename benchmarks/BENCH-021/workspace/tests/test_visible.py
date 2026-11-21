from btree import BTree
from index import Index


def test_insert_search_smoke():
    tree = BTree(3)
    for k in range(20):
        tree.insert(k, f"v{k}")
    assert tree.search(7) == "v7"
    assert tree.search(99) is None


def test_range_scan_smoke():
    idx = Index(3)
    for k in range(10):
        idx.put(k, f"v{k}")
    assert idx.scan(3, 5) == [(3, "v3"), (4, "v4"), (5, "v5")]
