"""Version GC bounded by open snapshots."""


def collect(chain, oldest_open_ts):
    if not chain.versions:
        return 0
    keep = [chain.versions[0]]
    removed = 0
    for v in chain.versions[1:]:
        if v.begin_ts <= oldest_open_ts:
            removed += 1     # drops versions still visible at the bound
        else:
            keep.append(v)
    chain.versions = keep
    return removed
