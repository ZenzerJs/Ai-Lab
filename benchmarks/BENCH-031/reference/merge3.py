"""Line-based three-way merge of text blobs.

Aligns base->ours and base->theirs via difflib opcodes, then merges
change REGIONS: a base region changed on only one side takes that
side's replacement; both sides changed to the same text collapse;
differing replacements emit a conflict hunk. Line-ending style and the
trailing-newline convention are inherited from `base` (falling back to
`ours` when base is empty).
"""
import difflib


def _chunks(base_lines, side_lines):
    """(lo, hi, replacement_lines) edits turning base into side."""
    sm = difflib.SequenceMatcher(None, base_lines, side_lines,
                                 autojunk=False)
    return [(b1, b2, side_lines[s1:s2])
            for tag, b1, b2, s1, s2 in sm.get_opcodes()
            if tag != "equal"]


def _effective(base_lines, changes, lo, hi):
    """One side's content for the union region base[lo:hi]."""
    out, pos = [], lo
    for c_lo, c_hi, repl in changes:
        out.extend(base_lines[pos:c_lo])
        out.extend(repl)
        pos = c_hi
    out.extend(base_lines[pos:hi])
    return out


def merge_blobs(base: str, ours: str, theirs: str):
    """Merge two revisions against a common ancestor.

    Returns (merged_text, conflicts) where conflicts lists
    (ours_text, theirs_text) pairs for every real divergence.
    """
    if ours == theirs:
        return ours, []
    b, o, t = base.splitlines(), ours.splitlines(), theirs.splitlines()
    ocs, tcs = _chunks(b, o), _chunks(b, t)
    out, conflicts = [], []
    i = 0
    while i < len(b) or ocs or tcs:
        starts = [c[0] for c in (ocs[0] if ocs else None,
                                 tcs[0] if tcs else None) if c]
        nxt = min(starts) if starts else len(b)
        out.extend(b[i:nxt])
        i = nxt
        if not starts:
            break
        # union region [lo, hi): every change touching it is merged in
        lo = hi = i
        o_reg, t_reg = [], []
        moved = True
        while moved:
            moved = False
            while ocs and ocs[0][0] <= hi:
                c = ocs.pop(0)
                o_reg.append(c)
                hi = max(hi, c[1])
                moved = True
            while tcs and tcs[0][0] <= hi:
                c = tcs.pop(0)
                t_reg.append(c)
                hi = max(hi, c[1])
                moved = True
        o_eff = _effective(b, o_reg, lo, hi)
        t_eff = _effective(b, t_reg, lo, hi)
        b_eff = b[lo:hi]
        if o_eff == t_eff:
            out.extend(o_eff)
        elif o_eff == b_eff:
            out.extend(t_eff)     # only theirs changed the region
        elif t_eff == b_eff:
            out.extend(o_eff)     # only ours changed the region
        else:
            conflicts.append(("\n".join(o_eff), "\n".join(t_eff)))
            out.append("<<<<<<< ours")
            out.extend(o_eff)
            out.append("=======")
            out.extend(t_eff)
            out.append(">>>>>>> theirs")
        i = hi
    eol = "\r\n" if "\r\n" in base else "\n"
    src = base or ours
    text = eol.join(out)
    if out and src.endswith(("\n", "\r\n")):
        text += eol
    return text, conflicts
