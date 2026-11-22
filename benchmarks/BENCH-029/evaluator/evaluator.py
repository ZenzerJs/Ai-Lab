"""Protected deterministic checks for BENCH-029."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from engine import Regex
        from parser import ParseError, parse
        from syntax import Alt, Char, Concat, Star

        def parse_checks():
            tree = parse("ab|cd")
            assert isinstance(tree, Alt)
            assert isinstance(tree.left, Concat)
            # Postfix binds to the preceding atom, not the concat.
            star = parse("ab*")
            assert isinstance(star, Concat)
            assert isinstance(star.right, Star)
            assert isinstance(star.left, Char)
            assert parse("a|b").right.c == "b"
            rejected(ParseError, lambda: parse("(a"))
            rejected(ParseError, lambda: parse("a)"))

        def match_checks():
            assert Regex("abc").match("abcdef") == 3
            assert Regex("abc").match("xabc") is None
            assert Regex("ab*").match("abbb") == 4
            assert Regex("ab*").match("a") == 1
            assert Regex("a*").match("b") == 0
            assert Regex("ab*").match("abab") == 2
            assert Regex("a|bc").match("bc") == 2
            assert Regex("(a|b)c").match("bc") == 2
            assert Regex("a+").match("baa") is None
            assert Regex("a?b").match("b") == 1

        def class_checks():
            assert Regex("[a-c]+").match("abcabc") == 6
            assert Regex("[^a-c]+").match("xyz") == 3
            assert Regex("[^a-c]+").match("xyaz") == 2
            assert Regex(r"\d+").match("123") == 3
            assert Regex(r"\w+").match("a_9Z") == 4
            assert Regex(r"\s").match(" ") == 1
            assert Regex(r"a\.b").match("a.b") == 3
            assert Regex(r"a\.b").match("axb") is None
            assert Regex(".").match("x") == 1
            assert Regex(".").match("\n") is None

        def search_checks():
            assert Regex("bc").search("xabcy") == (2, 4)
            assert Regex("z").search("abc") is None
            assert Regex("a+").search("baab") == (1, 3)
            # Earliest position wins even if a later match is longer.
            assert Regex("a+").search("aabaaab") == (0, 2)

        def closure_checks():
            # Nested groups + star need transitive epsilon closure.
            assert Regex("(a(b|c))*").match("abac") == 4
            assert Regex("(a(b|c))*").match("") == 0
            assert Regex("((a)+)b").match("aaab") == 4
            assert Regex("(ab)+").match("ababab") == 6

        def findall_checks():
            assert Regex("a+").findall("xaaaya") == ["aaa", "a"]
            assert Regex("a+").findall("aaab") == ["aaa"]
            assert Regex("[0-9]+").findall("a1b22c333") == \
                ["1", "22", "333"]
            assert Regex("a*").findall("ba") == ["a"]
            assert Regex("xy").findall("xyxxy") == ["xy", "xy"]

        def determinism_checks():
            r = Regex("(a|b)*c")
            assert r.match("ababc") == 5
            assert r.match("ababc") == 5
            assert r.search("zzababc") == (2, 7)
            assert Regex("a").findall("") == []

        for check in (parse_checks, match_checks, class_checks,
                      search_checks, closure_checks, findall_checks,
                      determinism_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: regex_simulation_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
