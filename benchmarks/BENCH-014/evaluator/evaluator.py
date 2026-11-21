"""Protected deterministic checks for BENCH-014."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from ast_nodes import And, Comparison, Field, Literal, Not, Or
        from parser import parse
        from validator import Validator
        from compiler import SQLCompiler
    except Exception as exc:
        fail("import_error", exc)

    def model_checks():
        cmp = Comparison(Field("a"), "=", Literal(1))
        assert cmp.op == "="
        for name in ("", "1abc", "a-b", "a b", "a'", "a;"):
            rejected(ValueError, lambda: Field(name))
        for value in (True, [1], {"x": 1}, b"x", None):
            rejected(ValueError, lambda: Literal(value))
        for value in (float("nan"), float("inf")):
            rejected(ValueError, lambda: Literal(value))
        assert Literal("x").value == "x" and Literal(-3).value == -3
        for op in ("==", "in", "LIKE", "", "=~"):
            rejected(ValueError, lambda: Comparison(Field("a"), op, Literal(1)))
        rejected(ValueError, lambda: Comparison(Field("a"), "like", Literal(1)))
        rejected(ValueError, lambda: Comparison(Field("a"), ">", Literal("s")))
        rejected(ValueError, lambda: Comparison(Field("a"), "=", 1))
        rejected(ValueError, lambda: Comparison("a", "=", Literal(1)))
        assert Comparison(Field("a"), "like", Literal("x%")).literal.value == "x%"
        assert Comparison(Field("a"), ">=", Literal(1.5)).literal.value == 1.5
        rejected(ValueError, lambda: And(()))
        rejected(ValueError, lambda: Or([]))
        rejected(ValueError, lambda: And((Comparison(Field("a"), "=", Literal(1)), 5)))
        rejected(ValueError, lambda: Not(5))
        node = Comparison(Field("a"), "=", Literal(1))
        assert And((node, node)).children == (node, node)
        assert Not(node).child is node

    def parser_checks():
        node = parse("a = 1 OR b = 2 AND c = 3")
        assert isinstance(node, Or) and len(node.children) == 2
        assert isinstance(node.children[0], Comparison)
        assert isinstance(node.children[1], And) and len(node.children[1].children) == 2
        node = parse("(a = 1 OR b = 2) AND c = 3")
        assert isinstance(node, And)
        assert isinstance(node.children[0], Or)
        node = parse("NOT a = 1 OR b = 2")
        assert isinstance(node, Or) and isinstance(node.children[0], Not)
        node = parse("NOT NOT a = 1")
        assert isinstance(node, Not) and isinstance(node.child, Not)
        node = parse("a = 'it\\'s' AND b = -3.5 AND c like 'x%'")
        assert node.children[0].literal.value == "it's"
        assert node.children[1].literal.value == -3.5
        assert isinstance(node.children[1].literal.value, float)
        assert node.children[2].op == "like"
        node = parse("a = -3")
        assert node.literal.value == -3 and isinstance(node.literal.value, int)
        for bad in ("a == 1", "a = 1 extra", "a =", "a", "= 1", "(a = 1",
                    "a = 1)", "a = 'x", "a = [1]", "a AND b = 1",
                    "a = 1 or b = 2", "a > 's'", "like = 1"):
            rejected(ValueError, lambda: parse(bad))
        def flatten(node):
            if isinstance(node, And):
                out = []
                for child in node.children:
                    out.extend(flatten(child))
                return out
            return [node]
        node = parse("a = 1 AND b = 2 AND c = 3")
        assert isinstance(node, And)
        leaves = flatten(node)
        assert len(leaves) == 3 and all(isinstance(leaf, Comparison)
                                        for leaf in leaves)

    def validator_checks():
        validator = Validator({"a", "b"})
        node = parse("a = 1 AND b = 2")
        assert validator.validate(node) is node
        for text in ("c = 1", "a = 1 AND c = 2", "a = 1 OR (b = 2 AND c = 3)",
                     "NOT c = 1", "(a = 1 OR c = 2) AND b = 3"):
            rejected(ValueError, lambda: validator.validate(parse(text)))
        rejected(ValueError, lambda: Validator({"a"}).validate(parse("b = 1 AND a = 2")))
        rejected(ValueError, lambda: Validator(set()).validate(parse("z = 1")))
        assert Validator({"a", "b"}).validate(node) is node

    def compiler_checks():
        compiler = SQLCompiler({"a", "b", "c", "name"})
        sql, params = compiler.compile(parse("a = 1 OR b = 2 AND c = 3"))
        assert sql == "(a = ? OR (b = ? AND c = ?))"
        assert params == [1, 2, 3]
        sql, params = compiler.compile(parse("(a = 1 OR b = 2) AND c = 3"))
        assert sql == "((a = ? OR b = ?) AND c = ?)"
        sql, params = compiler.compile(parse("NOT a = 1 AND name like 'x%'"))
        assert sql == "(NOT (a = ?) AND name LIKE ?)"
        assert params == [1, "x%"]
        sql, params = compiler.compile(parse("name = 'x\\' OR \\'1\\'=\\'1' AND a = 1"))
        assert "' OR '" not in sql and "'1'" not in sql
        assert sql == "(name = ? AND a = ?)"
        assert params[0] == "x' OR '1'='1"
        sql, params = compiler.compile(parse("name = 'a; DROP TABLE users; --'"))
        assert sql == "name = ?" and params == ["a; DROP TABLE users; --"]
        rejected(ValueError, lambda: compiler.compile(parse("unknown = 1")))
        rejected(ValueError, lambda: compiler.compile(parse("a = 1 OR unknown = 2")))
        rejected(ValueError, lambda: compiler.compile(parse("NOT unknown = 1")))

    for check in (model_checks, parser_checks, validator_checks, compiler_checks):
        try:
            check()
        except Exception as exc:
            fail("sql_compiler_invariant_violation",
                 f"{check.__name__}: {type(exc).__name__}: {exc}")
    print("ALL CHECKS PASSED")


def fail(reason, detail):
    print(f"REASON: {reason}", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
