"""Thompson construction: AST -> NFA fragment."""
from nfa import NFA, State
from syntax import Alt, Any, Char, Class, Concat, Opt, Plus, Star


def compile(node) -> NFA:
    """Compile an AST node into an NFA with single start/accept."""
    start, accept = State(), State()
    if isinstance(node, Char):
        start.edges.append((lambda ch, c=node.c: ch == c, accept))
    elif isinstance(node, Any):
        start.edges.append((lambda ch: ch != "\n", accept))
    elif isinstance(node, Class):
        ranges = node.ranges
        if node.negated:
            start.edges.append(
                (lambda ch, rs=ranges:
                 all(not lo <= ch <= hi for lo, hi in rs), accept))
        else:
            start.edges.append(
                (lambda ch, rs=ranges:
                 any(lo <= ch <= hi for lo, hi in rs), accept))
    elif isinstance(node, Concat):
        left, right = compile(node.left), compile(node.right)
        left.accept.eps.append(right.start)
        return NFA(left.start, right.accept)
    elif isinstance(node, Alt):
        left, right = compile(node.left), compile(node.right)
        start.eps.extend([left.start, right.start])
        left.accept.eps.append(accept)
        right.accept.eps.append(accept)
    elif isinstance(node, Star):
        inner = compile(node.node)
        start.eps.extend([inner.start, accept])
        inner.accept.eps.extend([inner.start, accept])
    elif isinstance(node, Plus):
        inner = compile(node.node)
        start.eps.append(inner.start)
        inner.accept.eps.extend([inner.start, accept])
    elif isinstance(node, Opt):
        inner = compile(node.node)
        start.eps.extend([inner.start, accept])
        inner.accept.eps.append(accept)
    else:
        raise TypeError(f"cannot compile {type(node).__name__}")
    return NFA(start, accept)
