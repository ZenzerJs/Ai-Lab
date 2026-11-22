"""Version GC bounded by the oldest open snapshot."""
from versions import INF


def collect(chain, oldest_open_ts) -> int:
    """Drop versions no open or future transaction can read.

    The newest version is always kept. An older version is garbage when
    its end_ts <= oldest_open_ts: every reader at ts >= oldest_open_ts
    sees the newer version that closed it. Returns versions removed.
    """
    if not chain.versions:
        return 0
    keep = [chain.versions[0]]
    removed = 0
    for v in chain.versions[1:]:
        if v.end_ts <= oldest_open_ts:
            removed += 1
        else:
            keep.append(v)
    chain.versions = keep
    return removed
