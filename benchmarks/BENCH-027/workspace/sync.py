"""Repair planning and application for replica sync."""
from diff import diff_ranges


def plan_repair(local, remote):
    return [("fetch", s, e) for s, e in diff_ranges(local, remote)]


def apply_plan(local_chunks, remote_chunks, plan):
    out = list(local_chunks)
    for _op, start, end in plan:
        out[start:end] = remote_chunks[start:end]
    return out
