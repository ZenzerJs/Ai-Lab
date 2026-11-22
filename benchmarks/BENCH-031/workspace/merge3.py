"""Line-based three-way merge of text blobs."""


def merge_blobs(base, ours, theirs):
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
            out.append(o)          # silently keep ours on conflict
    return "\n".join(out) + ("\n" if out else ""), conflicts
