"""Deterministic fixed-size chunking of byte payloads."""


def chunk(data: bytes, size: int) -> list:
    """Split `data` into ordered chunks of at most `size` bytes.

    Every byte of `data` belongs to exactly one chunk; the final chunk
    may be shorter than `size`. Raises ValueError when size <= 0.
    """
    if size <= 0:
        raise ValueError("chunk size must be positive")
    return [data[i:i + size] for i in range(0, len(data), size)]
