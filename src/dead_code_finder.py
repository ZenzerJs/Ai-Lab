"""AST-based dead code finder detecting unused private functions and unreachable statements."""

import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Set, Union


class FindingType(str, Enum):
    """Categorization of detected dead code findings."""
    UNUSED_PRIVATE_FUNCTION = "unused_private_function"
    UNREACHABLE_CODE = "unreachable_code"


@dataclass(frozen=True)
class DeadCodeFinding:
    """Represents a single detected dead code occurrence."""
    finding_type: FindingType
    name: str
    lineno: int
    col_offset: int
    message: str


class _ReferenceCollector(ast.NodeVisitor):
    """Visitor collecting all identifier references across the AST."""

    def __init__(self) -> None:
        self.references: Set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        # Collect referenced identifiers
        self.references.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Collect attribute access names (e.g. self._helper)
        self.references.add(node.attr)
        self.generic_visit(node)


class DeadCodeFinder(ast.NodeVisitor):
    """AST visitor detecting unused private functions and unreachable statements."""

    def __init__(self) -> None:
        self.findings: List[DeadCodeFinding] = []
        self._private_functions: List[Union[ast.FunctionDef, ast.AsyncFunctionDef]] = []

    def _is_private_function(self, name: str) -> bool:
        """Return True if name is private (starts with single underscore, not dunder)."""
        return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._is_private_function(node.name):
            self._private_functions.append(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self._is_private_function(node.name):
            self._private_functions.append(node)
        self.generic_visit(node)

    def _check_block_reachability(self, statements: List[ast.stmt]) -> None:
        """Check a sequence of statements for unreachable code following return or raise."""
        terminated = False
        terminator_type = ""

        for stmt in statements:
            if terminated:
                # Any statement following a terminator in the same block is unreachable
                stmt_desc = type(stmt).__name__
                self.findings.append(
                    DeadCodeFinding(
                        finding_type=FindingType.UNREACHABLE_CODE,
                        name=stmt_desc,
                        lineno=stmt.lineno,
                        col_offset=stmt.col_offset,
                        message=f"Unreachable statement '{stmt_desc}' detected after {terminator_type} statement",
                    )
                )
            elif isinstance(stmt, (ast.Return, ast.Raise)):
                terminated = True
                terminator_type = "return" if isinstance(stmt, ast.Return) else "raise"

    def generic_visit(self, node: ast.AST) -> None:
        """Visit child nodes while also inspecting all statement lists for reachability."""
        # Check all attributes of the node that contain lists of statements
        for field, value in ast.iter_fields(node):
            if isinstance(value, list) and value and all(isinstance(item, ast.stmt) for item in value):
                self._check_block_reachability(value)
        super().generic_visit(node)

    def analyze(self, tree: ast.AST) -> List[DeadCodeFinding]:
        """Analyze an AST tree and return all detected dead code findings."""
        self.findings = []
        self._private_functions = []

        # Pass 1: Walk tree to find unreachable statements and record private functions
        self.visit(tree)

        # Pass 2: Collect all name references in the AST
        ref_collector = _ReferenceCollector()
        ref_collector.visit(tree)

        # Check which private functions are never referenced
        for func_node in self._private_functions:
            func_name = func_node.name
            # Count occurrences of the function name in references
            # If name is only referenced 0 times (or if only definition), it is unused.
            # Notice ref_collector collects all Name and Attribute nodes.
            # In a FunctionDef, the function name is a string on func_node.name, not an ast.Name child!
            # Therefore, any appearance in ref_collector is a genuine usage/reference.
            if func_name not in ref_collector.references:
                self.findings.append(
                    DeadCodeFinding(
                        finding_type=FindingType.UNUSED_PRIVATE_FUNCTION,
                        name=func_name,
                        lineno=func_node.lineno,
                        col_offset=func_node.col_offset,
                        message=f"Private function '{func_name}' is defined but never used",
                    )
                )

        # Sort findings deterministically by line number, then column offset
        self.findings.sort(key=lambda f: (f.lineno, f.col_offset, f.finding_type.value))
        return list(self.findings)


def find_dead_code(source: str, filename: Optional[str] = None) -> List[DeadCodeFinding]:
    """Parse source string and return all detected dead code findings."""
    tree = ast.parse(source, filename=filename or "<string>")
    finder = DeadCodeFinder()
    return finder.analyze(tree)


def find_dead_code_from_file(filepath: Union[str, Path]) -> List[DeadCodeFinding]:
    """Read a Python file, parse its AST, and return all detected dead code findings."""
    path = Path(filepath)
    source = path.read_text(encoding="utf-8")
    return find_dead_code(source, filename=str(path))
