"""Line-based three-way merge of text blobs."""


def merge_blobs(base: str, ours: str, theirs: str):
    """Merge two revisions against a common ancestor.

    Lines changed on only one side are taken; both sides changed to the
    SAME text collapse cleanly; differing edits on both sides emit a
    conflict hunk. Returns (merged_text, conflicts) where conflicts is a
    list of (ours_text, theirs_text) pairs.
    """
    if ours == theirs:
        return ours, []
    base_lines, our_lines = base.splitlines(), ours.splitlines()
    their_lines = theirs.splitlines()
    out, conflicts = [], []
    n = max(len(base_lines), len(our_lines), len(their_lines))
    for i in range(n):
        b = base_lines[i] if i < len(base_lines) else None
        o = our_lines[i] if i < len(our_lines) else None
        t = their_lines[i] if i < len(their_lines) else None
        if o == t:
            if o is not None:
                out.append(o)
        elif o == b:
            if t is not None:
                out.append(t)
        elif t == b:
            if o is not None:
                out.append(o)
        else:
            conflicts.append((o or "", t or ""))
            out.append("<<<<<<< ours")
            if o is not None:
                out.append(o)
            out.append("=======")
            if t is not None:
                out.append(t)
            out.append(">>>>>>> theirs")
    return "\n".join(out) + ("\n" if out else ""), conflicts
