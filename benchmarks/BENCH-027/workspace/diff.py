"""Merkle diffing: leaf ranges whose hashes disagree."""


def diff_ranges(local, remote):
    if local.root == remote.root:
        return []
    return [(0, max(len(local.leaves), len(remote.leaves)))]
