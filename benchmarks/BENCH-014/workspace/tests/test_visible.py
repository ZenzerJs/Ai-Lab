from parser import parse
from validator import Validator
from compiler import SQLCompiler


def test_parse_and_compile_smoke():
    node = parse("status = 'open' AND age >= 18")
    sql, params = SQLCompiler({"status", "age"}).compile(node)
    assert sql == "(status = ? AND age >= ?)"
    assert params == ["open", 18]


def test_validate_smoke():
    node = parse("status = 'open'")
    assert Validator({"status"}).validate(node) is node
