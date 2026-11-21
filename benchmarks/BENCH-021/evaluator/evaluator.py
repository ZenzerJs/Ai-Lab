"""Protected deterministic checks for BENCH-021."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import Config, DuplicateKey, InvalidConfig, KeyNotFound
        from btree import BTree
        from index import Index, restore

        def model_checks():
            for order in (0, 1, -3, 1.5, True, "3"):
                rejected(InvalidConfig, lambda: Config(order))
            cfg = Config(4)
            assert cfg.max_keys == 4 and cfg.min_keys == 2
            assert Config(3).min_keys == 1

        def insert_search_checks():
            tree = BTree(3)
            for k in range(40):
                tree.insert(k, f"v{k}")
                tree.validate()
            assert [k for k, _v in tree.items()] == list(range(40))
            for k in range(40):
                assert tree.search(k) == f"v{k}"
            assert tree.search(41) is None
            rejected(DuplicateKey, lambda: tree.insert(10, "x"))
            rejected(ValueError, lambda: tree.insert(1.5, "x"))
            rejected(ValueError, lambda: tree.insert(True, "x"))
            # Separator-equal keys must resolve through the right child.
            tree2 = BTree(3)
            for k in range(25):
                tree2.insert(k, str(k))
            def separators(node):
                if node.is_leaf:
                    return
                for sep in node.keys:
                    assert tree2.search(sep) == str(sep), \
                        f"separator key {sep} unreachable"
                for child in node.children:
                    separators(child)
            separators(tree2.root)

        def delete_checks():
            tree = BTree(3)
            for k in range(30):
                tree.insert(k, f"v{k}")
            for k in (0, 5, 7, 12, 29, 28, 1, 2):
                tree.delete(k)
                tree.validate()
            remaining = [k for k in range(30) if k not in (0, 5, 7, 12, 29, 28, 1, 2)]
            assert [k for k, _v in tree.items()] == remaining
            for k in remaining:
                assert tree.search(k) == f"v{k}"
            rejected(KeyNotFound, lambda: tree.delete(5))
            # Heavy delete cascade keeps occupancy bounds valid.
            tree2 = BTree(3)
            for k in range(60):
                tree2.insert(k, "x")
            for k in range(0, 60, 2):
                tree2.delete(k)
                tree2.validate()
            assert [k for k, _v in tree2.items()] == list(range(1, 60, 2))
            # Empty tree stays consistent.
            tree3 = BTree(3)
            for k in range(12):
                tree3.insert(k, "x")
            for k in range(12):
                tree3.delete(k)
            tree3.validate()
            assert tree3.items() == []
            assert tree3.search(3) is None

        def range_scan_checks():
            tree = BTree(4)
            for k in range(0, 50, 2):
                tree.insert(k, f"v{k}")
            assert tree.range_scan(6, 14) == [(k, f"v{k}") for k in (6, 8, 10, 12, 14)]
            assert tree.range_scan(0, 0) == [(0, "v0")]
            assert tree.range_scan(48, 48) == [(48, "v48")]
            assert tree.range_scan(20, 10) == []
            assert tree.range_scan(7, 13) == [(k, f"v{k}") for k in (8, 10, 12)]
            # Boundary inclusivity at both ends.
            assert tree.range_scan(0, 48)[0] == (0, "v0")
            assert tree.range_scan(0, 48)[-1] == (48, "v48")

        def index_checks():
            idx = Index(3)
            for k in range(25):
                idx.put(k, f"v{k}")
            assert idx.get(9) == "v9"
            idx.remove(9)
            assert idx.get(9) is None
            assert idx.verify()
            snap = idx.snapshot()
            assert snap, "empty snapshot"
            for page in snap.values():
                assert page["kind"] in ("leaf", "internal")
            pids = list(snap.keys())
            assert pids == sorted(pids,
                                  key=lambda p: (p[0], int(p[1:])))
            rebuilt = restore(snap)
            assert [k for k, _v in rebuilt.tree.items()] == \
                [k for k in range(25) if k != 9]
            assert rebuilt.verify()

        for check in (model_checks, insert_search_checks, delete_checks,
                      range_scan_checks, index_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: ordering_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
