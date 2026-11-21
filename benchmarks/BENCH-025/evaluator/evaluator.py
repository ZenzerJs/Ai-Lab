"""Protected deterministic checks for BENCH-025."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from eval import evaluate, run
        from env import Environment
        from lexer import tokenize
        from models import (Assign, Binary, EvalError, LexError, Literal,
                            Name, ParseError)
        from parser import Parser

        def lexer_checks():
            toks = tokenize("x_1 = 40 + 2;")
            kinds = [t.kind for t in toks]
            assert kinds == ["name", "eq", "num", "op", "num", "semi"]
            assert toks[2].pos == 6
            rejected(LexError, lambda: tokenize("1 @ 2"))
            rejected(LexError, lambda: tokenize("x := 3"))

        def precedence_checks():
            assert run("2 + 3 * 4") == [14]
            assert run("10 - 2 - 3") == [5]          # left-assoc
            assert run("20 / 5 / 2") == [2]
            assert run("-(3 + 4) * 2") == [-14]
            assert run("2 * (3 + 4)") == [14]
            assert run("--5") == [5]

        def parse_error_checks():
            for src in ("1 +", "(1 + 2", "1 2", "+", "=", ";",
                        "x =", "1;;2"):
                rejected(ParseError, lambda: run(src))
            assert run("1;") == [1]                  # trailing ; ok

        def eval_checks():
            assert run("x = 5; x * 2") == [5, 10]
            assert run("a = 2; b = a + 3; b") == [2, 5, 5]
            rejected(EvalError, lambda: run("nope"))
            rejected(EvalError, lambda: run("1 / 0"))
            rejected(EvalError, lambda: run("7 / 2"))  # non-integer div
            assert run("6 / 2") == [3]

        def scope_checks():
            env = Environment()
            env.define("x", 1)
            child = env.child()
            assert child.get("x") == 1
            child.define("x", 2)
            assert env.get("x") == 1                 # no parent write
            assert child.get("x") == 2
            rejected(EvalError, lambda: env.get("zzz"))
            assert run("x + 10", env=child) == [12]
            assert not env.has("zzz") and child.has("x")

        def ast_checks():
            stmts = Parser(tokenize("x = 1 + 2")).parse_program()
            assert isinstance(stmts[0], Assign)
            assert isinstance(stmts[0].value, Binary)
            assert isinstance(stmts[0].value.left, Literal)
            toks = tokenize("3 * x")
            ast = Parser(toks).parse_expr()
            assert ast.op == "*"

        for check in (lexer_checks, precedence_checks, parse_error_checks,
                      eval_checks, scope_checks, ast_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: evaluation_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
