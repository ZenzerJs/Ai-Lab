"""Protected deterministic checks for BENCH-027."""
import hashlib
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def spec_leaf(data):
    return hashlib.sha256(b"leaf:" + data).hexdigest()


def spec_node(l, r):
    return hashlib.sha256(b"node:" + l.encode() + r.encode()).hexdigest()


def spec_root(chunks):
    """Independent recomputation of the Merkle root."""
    level = [spec_leaf(c) for c in chunks]
    while len(level) > 1:
        nxt = [spec_node(level[i], level[i + 1])
               for i in range(0, len(level) - 1, 2)]
        if len(level) % 2 == 1:
            nxt.append(level[-1])
        level = nxt
    return level[0] if chunks else None


def run_checks():
    try:
        from chunker import chunk
        from diff import diff_ranges
        from hashing import leaf_hash, node_hash
        from merkle import MerkleTree
        from replica import Replica

        def hashing_checks():
            assert leaf_hash(b"x") == spec_leaf(b"x")
            assert leaf_hash(b"") == spec_leaf(b"")
            a, b = spec_leaf(b"a"), spec_leaf(b"b")
            assert node_hash(a, b) == spec_node(a, b)
            assert node_hash(a, b) != node_hash(b, a)   # order matters

        def chunker_checks():
            assert chunk(b"abcdef", 4) == [b"abcd", b"ef"]
            assert chunk(b"abcdef", 2) == [b"ab", b"cd", b"ef"]
            assert chunk(b"", 4) == []
            assert chunk(b"x", 1) == [b"x"]
            joined = b"".join(chunk(bytes(range(200)), 7))
            assert joined == bytes(range(200))   # no byte lost/doubled
            rejected(ValueError, lambda: chunk(b"ab", 0))
            rejected(ValueError, lambda: chunk(b"ab", -3))

        def merkle_checks():
            for n in range(0, 8):
                chunks = [bytes([i]) * (i + 1) for i in range(n)]
                assert MerkleTree(chunks).root == spec_root(chunks), n
            l0, l1, l2 = (spec_leaf(bytes([i])) for i in range(3))
            tree = MerkleTree([bytes([0]), bytes([1]), bytes([2])])
            # Odd leftover is promoted unchanged, not re-hashed.
            assert tree.root == spec_node(spec_node(l0, l1), l2)

        def diff_checks():
            mk = lambda blobs: MerkleTree(blobs)
            base = [b"a", b"b", b"c", b"d"]
            assert diff_ranges(mk(base), mk(list(base))) == []
            mod = [b"a", b"X", b"c", b"d"]
            assert diff_ranges(mk(base), mk(mod)) == [(1, 2)]
            mod2 = [b"a", b"X", b"Y", b"d"]
            assert diff_ranges(mk(base), mk(mod2)) == [(1, 3)]
            mod3 = [b"X", b"b", b"Y", b"d"]
            assert diff_ranges(mk(base), mk(mod3)) == [(0, 1), (2, 3)]
            longer = base + [b"e", b"f"]
            assert diff_ranges(mk(base), mk(longer)) == [(4, 6)]
            shorter = [b"a", b"b"]
            assert diff_ranges(mk(base), mk(shorter)) == [(2, 4)]

        def sync_checks():
            peer = Replica("p", b"A" * 40 + b"B" * 40 + b"C" * 17,
                           chunk_size=8)
            local = Replica("l", b"A" * 40 + b"X" * 40 + b"C" * 17,
                            chunk_size=8)
            assert not local.is_consistent(peer)
            repaired = local.sync_with(peer)
            assert repaired == 5        # only the B-block's 5 chunks
            assert local.is_consistent(peer)
            assert b"".join(local.chunks) == b"A" * 40 + b"B" * 40 + \
                b"C" * 17
            assert local.sync_with(peer) == 0    # idempotent
            # Peer must never be mutated by a pull-sync.
            assert peer.chunks == chunk(b"A" * 40 + b"B" * 40 +
                                        b"C" * 17, 8)

        def divergence_checks():
            a = Replica("a", b"shared" * 10, chunk_size=10)
            b = Replica("b", b"shared" * 10 + b"extra", chunk_size=10)
            repaired = b.sync_with(a)
            assert repaired == 1
            assert b.is_consistent(a)
            assert len(b.chunks) == len(a.chunks)

        for check in (hashing_checks, chunker_checks, merkle_checks,
                      diff_checks, sync_checks, divergence_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: anti_entropy_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
