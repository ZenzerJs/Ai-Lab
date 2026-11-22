"""Fixed-size chunking of byte payloads."""


def chunk(data, size):
    if size <= 0:
        raise ValueError("chunk size must be positive")
    return [data[i:i + size]
            for i in range(0, len(data) - size + 1, size)]
