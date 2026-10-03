"""Test suite and fixtures for dead_code_finder detecting unused private functions and unreachable statements."""

import unittest
from pathlib import Path
import tempfile

from src.dead_code_finder import (
    DeadCodeFinder,
    DeadCodeFinding,
    FindingType,
    find_dead_code,
    find_dead_code_from_file,
)


# Test Fixture Sources
FIXTURE_UNUSED_PRIVATE_FUNCTION = """
def _unused_func():
    return 42

def public_func():
    return 100
"""

FIXTURE_USED_PRIVATE_FUNCTION = """
def _helper_func(x):
    return x * 2

def public_func():
    return _helper_func(21)
"""

FIXTURE_UNUSED_PRIVATE_CLASS_METHOD = """
class MyService:
    def __init__(self):
        self.val = 10

    def _unused_method(self):
        return "unused"

    def public_api(self):
        return self.val
"""

FIXTURE_USED_PRIVATE_CLASS_METHOD = """
class MyService:
    def __init__(self):
        self.val = 10

    def _used_method(self):
        return self.val * 2

    def public_api(self):
        return self._used_method()
"""

FIXTURE_UNREACHABLE_AFTER_RETURN = """
def calculate(val):
    if val > 0:
        return val
        print("This is unreachable after return inside if")
    return -val
    print("This is unreachable after return at end of function")
"""

FIXTURE_UNREACHABLE_AFTER_RAISE = """
def fail_fast(condition):
    if not condition:
        raise ValueError("Invalid condition")
        logger.error("Unreachable after raise")
    return True
"""

FIXTURE_TRY_EXCEPT_UNREACHABLE = """
def complex_flow(x):
    try:
        if x == 0:
            raise ZeroDivisionError("Cannot be zero")
            print("Unreachable after raise in try")
        return 100 / x
        print("Unreachable after return in try")
    except ZeroDivisionError:
        return -1
        print("Unreachable after return in except")
"""

FIXTURE_CLEAN_CODE = """
import os

def _internal_compute(base, multiplier):
    return base * multiplier

class Worker:
    def __init__(self, multiplier):
        self.multiplier = multiplier

    def __str__(self):
        return f"Worker(multiplier={self.multiplier})"

    def _format(self, value):
        return f"Result: {value}"

    def run(self, base):
        val = _internal_compute(base, self.multiplier)
        return self._format(val)
"""

FIXTURE_ASYNC_FUNCTIONS = """
async def _unused_async_func():
    return 123

async def _used_async_func():
    return 456

async def main():
    return await _used_async_func()
"""


class TestDeadCodeFinder(unittest.TestCase):
    """Unit tests for AST-based dead code detection."""

    def test_detect_unused_private_function(self):
        findings = find_dead_code(FIXTURE_UNUSED_PRIVATE_FUNCTION)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].finding_type, FindingType.UNUSED_PRIVATE_FUNCTION)
        self.assertEqual(findings[0].name, "_unused_func")
        self.assertEqual(findings[0].lineno, 2)

    def test_allow_used_private_function(self):
        findings = find_dead_code(FIXTURE_USED_PRIVATE_FUNCTION)
        self.assertEqual(findings, [])

    def test_detect_unused_private_class_method(self):
        findings = find_dead_code(FIXTURE_UNUSED_PRIVATE_CLASS_METHOD)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].finding_type, FindingType.UNUSED_PRIVATE_FUNCTION)
        self.assertEqual(findings[0].name, "_unused_method")

    def test_allow_used_private_class_method(self):
        findings = find_dead_code(FIXTURE_USED_PRIVATE_CLASS_METHOD)
        self.assertEqual(findings, [])

    def test_detect_unreachable_after_return(self):
        findings = find_dead_code(FIXTURE_UNREACHABLE_AFTER_RETURN)
        self.assertEqual(len(findings), 2)
        for f in findings:
            self.assertEqual(f.finding_type, FindingType.UNREACHABLE_CODE)
            self.assertIn("return", f.message)
        self.assertEqual(findings[0].lineno, 5)
        self.assertEqual(findings[1].lineno, 7)

    def test_detect_unreachable_after_raise(self):
        findings = find_dead_code(FIXTURE_UNREACHABLE_AFTER_RAISE)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.finding_type, FindingType.UNREACHABLE_CODE)
        self.assertEqual(finding.lineno, 5)
        self.assertIn("raise", finding.message)

    def test_detect_unreachable_in_try_except(self):
        findings = find_dead_code(FIXTURE_TRY_EXCEPT_UNREACHABLE)
        self.assertEqual(len(findings), 3)
        for f in findings:
            self.assertEqual(f.finding_type, FindingType.UNREACHABLE_CODE)

    def test_async_private_function_detection(self):
        findings = find_dead_code(FIXTURE_ASYNC_FUNCTIONS)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].finding_type, FindingType.UNUSED_PRIVATE_FUNCTION)
        self.assertEqual(findings[0].name, "_unused_async_func")

    def test_clean_code_has_no_findings(self):
        findings = find_dead_code(FIXTURE_CLEAN_CODE)
        self.assertEqual(findings, [])

    def test_find_dead_code_from_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(FIXTURE_UNUSED_PRIVATE_FUNCTION)
            tmp_path = Path(tmp.name)

        try:
            findings = find_dead_code_from_file(tmp_path)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].name, "_unused_func")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
