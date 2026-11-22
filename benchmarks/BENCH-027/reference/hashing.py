"""SHA-256 hashing helpers for chunk leaves and internal Merkle nodes."""
import hashlib


def leaf_hash(data: bytes) -> str:
    """Domain-separated content hash of a data chunk."""
    return hashlib.sha256(b"leaf:" + data).hexdigest()


def node_hash(left: str, right: str) -> str:
    """Hash of an internal node, ordered left-then-right."""
    return hashlib.sha256(
        b"node:" + left.encode() + right.encode()).hexdigest()
