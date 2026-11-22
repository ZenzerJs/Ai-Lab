"""SHA-256 hashing helpers for chunks and Merkle nodes."""
import hashlib


def leaf_hash(data):
    return hashlib.sha256(data).hexdigest()


def node_hash(left, right):
    return hashlib.sha256(
        b"node:" + left.encode() + right.encode()).hexdigest()
