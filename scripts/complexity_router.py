"""Deterministic selection of experiment contracts from declared task scope."""

import ast
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any, List, Mapping, Optional, Tuple
import warnings

import tiktoken

import repo_map

MODES = ("auto", "icm", "icm-lite", "icm-v2", "baseline")
ICM_LITE = "icm_lite"
ICM_V2 = "icm_v2"
LOC_THRESHOLD = 150
SYMBOL_THRESHOLD = 10
ICM_V2_REPO_MAP_MAX_TOKENS = 600
LOC_SOURCES = ("estimated_loc", "target_loc_range", "file_loc", "unknown")
LITE_CONTRACT = Path(__file__).resolve().parents[1] / "tasks" / "_template" / "icm_lite.md"
V2_CONTRACT = Path(__file__).resolve().parents[1] / "tasks" / "_template" / "icm_v2.md"

_REGEX_SYMBOL_PATTERNS = (
    re.compile(r"^\s*(?:async\s+)?def\s+[a-zA-Z_]"),
    re.compile(r"^\s*class\s+[a-zA-Z_]"),
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:class|interface|type|function)\s+[a-zA-Z_]"),
    re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+[a-zA-Z_]"),
    re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?[a-zA-Z_]"),
)

FULL_CONTRACT = """Execute this task using the full 5-stage ICM contract:
1. 01_intake: Establish scope, constraints, and context budget.
2. 02_plan: Identify impacted files and machine-verifiable acceptance criteria.
3. 03_exec: Apply targeted, diff-only edits and record the symbols changed.
4. 04_verify: Run the relevant automated checks through output sanitation and record results.
5. 05_retro: Record lessons and any follow-up needed without expanding the task's edit scope."""


@dataclass(frozen=True)
class RoutingDecision:
    """Resolved arm plus the scope evidence that produced it."""

    arm: str
    loc_source: str  # 'estimated_loc' | 'target_loc_range' | 'file_loc' | 'unknown'
    loc: Optional[int]
    single_file: bool
    target: Optional[str]
    ast_symbol_count: Optional[int] = None


_WRAPPER_NODE_TYPES = frozenset({"export_statement", "decorated_definition"})
_AST_SYMBOL_NODE_TYPES = frozenset(repo_map.DEF_NODE_TYPES) - _WRAPPER_NODE_TYPES


def count_ast_symbols(target: Optional[Path]) -> Optional[int]:
    """Count AST-level symbol definitions (functions, async functions, classes) in a file.

    Uses Python's ``ast`` module for ``.py`` files, falling back to tree-sitter via
    ``grep_ast`` (same node types as ``repo_map.py``) and finally regex signatures for
    non-Python or syntactically incomplete files.
    """
    if target is None or not target.is_file():
        return None
    try:
        code = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None

    if target.suffix == ".py":
        try:
            tree = ast.parse(code)
            return sum(
                1
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            )
        except SyntaxError:
            pass

    lang = repo_map.filename_to_lang(str(target))
    if lang:
        try:
            tc = repo_map.TreeContext(
                filename=str(target),
                code=code,
                color=False,
                line_number=False,
                mark_lois=False,
                margin=0,
                parent_context=False,
                child_context=False,
                last_line=False,
                loi_pad=0,
            )
            seen: set[Tuple[int, int, str]] = set()
            for nodes in tc.nodes:
                for node in nodes:
                    if node.type in _AST_SYMBOL_NODE_TYPES:
                        seen.add((node.start_point[0], node.start_point[1], node.type))
            if seen:
                return len(seen)
        except Exception:
            pass

    return sum(
        1
        for line in code.splitlines()
        if any(pat.search(line) for pat in _REGEX_SYMBOL_PATTERNS)
    )


def build_compact_repo_map(
    workspace: Optional[Path],
    max_tokens: int = ICM_V2_REPO_MAP_MAX_TOKENS,
) -> str:
    """Build a deterministic, token-bounded AST symbol/signature map for a workspace."""
    if workspace is None or not workspace.exists():
        return "# Repository Map: No AST symbols detected."

    root = workspace.resolve()
    files = repo_map.collect_target_files(root, root)
    if not files:
        return "# Repository Map: No AST symbols detected."

    def _rel_posix(fp: Path) -> str:
        try:
            return fp.resolve().relative_to(root).as_posix()
        except ValueError:
            return fp.as_posix()

    file_blocks: List[Tuple[str, str]] = []
    for fp in sorted(files, key=_rel_posix):
        symbols = repo_map.extract_symbols_from_file(fp)
        if symbols:
            file_blocks.append((_rel_posix(fp), symbols))

    if not file_blocks:
        return "# Repository Map: No AST symbols detected."

    enc = tiktoken.get_encoding(repo_map.ENCODING_NAME)
    return repo_map.binary_search_prune(file_blocks, max_tokens, enc)


def _single_target(metadata: Mapping[str, Any], workspace: Path) -> tuple[bool, Optional[Path]]:
    count = metadata.get("target_files_count")
    if count is not None and (type(count) is not int or count != 1):
        return False, None

    files = metadata.get("target_files")
    if files is None:
        return count == 1, None
    if not isinstance(files, list):
        return False, None

    root = workspace.resolve()
    paths = set()
    for name in files:
        if not isinstance(name, str) or not name.strip() or Path(name).is_absolute():
            return False, None
        try:
            path = (root / name).resolve()
            path.relative_to(root)
        except (ValueError, OSError, RuntimeError):
            return False, None
        if path == root or path.is_dir():
            return False, None
        paths.add(path)

    if len(paths) != 1:
        return False, None
    return True, paths.pop()


def _scoped_loc(metadata: Mapping[str, Any], target: Optional[Path]) -> tuple[Optional[int], str]:
    """Resolve task LOC from declared metadata, warning on malformed fields.

    Malformed fields are ignored so a bad estimate never hides a usable range or file.
    """
    estimate = metadata.get("estimated_loc")
    if estimate is not None:
        if type(estimate) is int and estimate >= 0:
            return estimate, "estimated_loc"
        warnings.warn(
            f"Malformed estimated_loc {estimate!r}: expected a non-negative int; falling through to other scope sources.",
            stacklevel=3,
        )

    loc_range = metadata.get("target_loc_range")
    if loc_range is not None:
        match = re.fullmatch(r"([0-9]+)-([0-9]+)", str(loc_range))
        if match:
            low, high = map(int, match.groups())
            if low <= high:
                return high, "target_loc_range"
        warnings.warn(
            f"Malformed target_loc_range {loc_range!r}: expected a 'low-high' digit range with low <= high; ignoring it.",
            stacklevel=3,
        )

    if target is not None and target.is_file():
        try:
            with target.open(encoding="utf-8") as source:
                return sum(1 for _ in source), "file_loc"
        except (OSError, UnicodeError):
            pass
    return None, "unknown"


def classify_mode(mode: str, metadata: Mapping[str, Any], workspace: Path) -> RoutingDecision:
    """Resolve the arm and report which scope source supplied the LOC & AST evidence."""
    if mode == "icm-lite":
        return RoutingDecision(ICM_LITE, "unknown", None, False, None)
    if mode == "icm-v2":
        return RoutingDecision(ICM_V2, "unknown", None, False, None)
    if mode in ("baseline", "icm"):
        return RoutingDecision(mode, "unknown", None, False, None)
    if mode != "auto":
        raise ValueError(f"Unsupported routing mode: {mode!r}")

    single_file, target = _single_target(metadata, workspace)
    loc, loc_source = _scoped_loc(metadata, target)
    ast_symbol_count = count_ast_symbols(target)

    within_loc = loc is not None and loc < LOC_THRESHOLD
    within_symbols = (
        ast_symbol_count is None
        or loc_source != "file_loc"
        or ast_symbol_count < SYMBOL_THRESHOLD
    )
    arm = ICM_LITE if single_file and within_loc and within_symbols else "icm"

    rel_target = None
    if target is not None:
        try:
            rel_target = target.relative_to(workspace.resolve()).as_posix()
        except ValueError:
            rel_target = str(target)
    return RoutingDecision(arm, loc_source, loc, single_file, rel_target, ast_symbol_count=ast_symbol_count)


def resolve_mode(mode: str, metadata: Mapping[str, Any], workspace: Path) -> str:
    """Return the arm ID; unknown or ambiguous complexity uses full ICM."""
    return classify_mode(mode, metadata, workspace).arm


def build_mode_prompt(
    instructions: str,
    arm: str,
    workspace: Optional[Path] = None,
    repo_map_max_tokens: int = ICM_V2_REPO_MAP_MAX_TOKENS,
) -> str:
    if arm == "baseline":
        return instructions
    if arm == ICM_LITE:
        contract = LITE_CONTRACT.read_text(encoding="utf-8").rstrip()
        return f"{contract}\n\n{instructions}"
    if arm == ICM_V2:
        contract = V2_CONTRACT.read_text(encoding="utf-8").rstrip()
        if workspace is not None and workspace.exists():
            symbol_map = build_compact_repo_map(workspace, max_tokens=repo_map_max_tokens)
            return f"{contract}\n\n## Pre-Injected AST Symbol Map\n{symbol_map}\n\n{instructions}"
        return f"{contract}\n\n{instructions}"
    return f"{FULL_CONTRACT}\n\n{instructions}"
