"""Deterministic selection of experiment contracts from declared task scope."""

import ast
from dataclasses import dataclass
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
import warnings

import tiktoken

import repo_map

MODES = ("auto", "auto-v3", "icm", "icm-lite", "icm-v2", "icm-v3", "icm-staged", "baseline")
ICM_LITE = "icm_lite"
ICM_V1 = "icm_v1"
ICM_V2 = "icm_v2"
ICM_V3 = "icm_v3"
ICM_STAGED = "icm_staged"
LOC_THRESHOLD = 150
SYMBOL_THRESHOLD = 10
ICM_V2_REPO_MAP_MAX_TOKENS = 600
ICM_V3_REPO_MAP_MAX_TOKENS = 1200
ICM_STAGED_REPO_MAP_MAX_TOKENS = ICM_V3_REPO_MAP_MAX_TOKENS
LOC_SOURCES = ("estimated_loc", "target_loc_range", "file_loc", "workspace_footprint", "unknown")
_REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = _REPO_ROOT / "contracts"
DEFAULT_CONTRACT_REGISTRY = CONTRACTS_DIR / "registry.json"
LITE_CONTRACT = _REPO_ROOT / "tasks" / "_template" / "icm_lite.md"
V2_CONTRACT = _REPO_ROOT / "tasks" / "_template" / "icm_v2.md"
V3_CONTRACT = CONTRACTS_DIR / "icm_v3.md"
STAGED_PLAN_CONTRACT = CONTRACTS_DIR / "icm_staged_plan.md"
STAGED_EXEC_CONTRACT = CONTRACTS_DIR / "icm_staged_exec.md"

ARM_TO_CONTRACT_ID: Dict[str, str] = {
    "icm": ICM_V1,
    ICM_V1: ICM_V1,
    ICM_LITE: ICM_LITE,
    ICM_V2: ICM_V2,
    ICM_V3: ICM_V3,
    ICM_STAGED: ICM_STAGED,
}

_WORKSPACE_IGNORE_DIRS = frozenset({
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".venv",
    "venv",
})
_WORKSPACE_IGNORE_SUFFIXES = frozenset({".pyc", ".pyo"})
_WORKSPACE_IGNORE_NAMES = frozenset({"INSTRUCTIONS.md"})
_PYTEST_IMPORT_RE = re.compile(r"(?m)^\s*(?:import\s+pytest|from\s+pytest\b)")
_UNITTEST_IMPORT_RE = re.compile(r"(?m)^\s*(?:import\s+unittest|from\s+unittest\b)")

_REGEX_SYMBOL_PATTERNS = (
    re.compile(r"^\s*(?:async\s+)?def\s+[a-zA-Z_]"),
    re.compile(r"^\s*class\s+[a-zA-Z_]"),
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:class|interface|type|function)\s+[a-zA-Z_]"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+[a-zA-Z_$][\w$]*\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z_$][\w$]*)\s*=>"),
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
    loc_source: str  # 'estimated_loc' | 'target_loc_range' | 'file_loc' | 'workspace_footprint' | 'unknown'
    loc: Optional[int]
    single_file: bool
    target: Optional[str]
    ast_symbol_count: Optional[int] = None
    contract_version: Optional[str] = None
    contract_hash: Optional[str] = None


def _compute_contract_sha256(contract_path: Path) -> str:
    """Compute SHA-256 over LF-normalized UTF-8 bytes for cross-platform parity."""
    normalized = contract_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def _resolve_contract_path(entry_file: str, registry_path: Path) -> Path:
    """Resolve a declared contract path strictly relative to the registry root."""
    if not isinstance(entry_file, str) or not entry_file.strip():
        raise ValueError(f"Invalid contract file path: {entry_file!r}")
    rel = Path(entry_file)
    if rel.is_absolute():
        raise ValueError(f"Contract file path must be relative: {entry_file!r}")

    reg_dir = registry_path.resolve().parent
    root_dir = reg_dir.parent if reg_dir.name == "contracts" else reg_dir

    if reg_dir.name == "contracts":
        base = root_dir if (entry_file.startswith("contracts/") or (root_dir / rel).exists()) else reg_dir
    else:
        base = reg_dir if (reg_dir / rel).exists() or not (root_dir / rel).exists() else root_dir

    candidate = (base / rel).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"Contract file escapes registry root: {entry_file!r}") from exc
    return candidate


def load_contract_registry(registry_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load the versioned contract registry mapping contract IDs to metadata dicts."""
    path = Path(registry_path) if registry_path is not None else DEFAULT_CONTRACT_REGISTRY
    if not path.is_file():
        raise ValueError(f"Contract registry not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid contract registry JSON at {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"Contract registry must be a JSON object: {path}")
    contracts = raw.get("contracts") if "contracts" in raw else raw
    if not isinstance(contracts, dict) or not contracts:
        raise ValueError(f"Contract registry must define a non-empty 'contracts' mapping: {path}")

    normalized: Dict[str, Dict[str, Any]] = {}
    for cid, entry in contracts.items():
        if not isinstance(cid, str) or not isinstance(entry, dict):
            raise ValueError(f"Malformed contract entry for {cid!r} in {path}")
        normalized[cid] = dict(entry)
    return normalized


def verify_contract_registry(registry_path: Optional[Path] = None) -> Dict[str, str]:
    """Verify every declared contract file exists and matches its declared SHA-256."""
    path = Path(registry_path) if registry_path is not None else DEFAULT_CONTRACT_REGISTRY
    registry = load_contract_registry(path)
    verified: Dict[str, str] = {}
    for cid, entry in registry.items():
        declared_id = entry.get("id")
        if declared_id is not None and declared_id != cid:
            raise ValueError(f"Contract entry ID mismatch: key {cid!r} != id {declared_id!r}")
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or not expected_hash.strip():
            raise ValueError(f"Contract '{cid}' is missing a valid sha256 digest")
        contract_path = _resolve_contract_path(entry.get("file", ""), path)
        if not contract_path.is_file():
            raise ValueError(f"Missing contract file for '{cid}': {contract_path}")
        plan_hash = _compute_contract_sha256(contract_path)

        exec_file = entry.get("exec_file")
        if exec_file is not None:
            exec_path = _resolve_contract_path(exec_file, path)
            if not exec_path.is_file():
                raise ValueError(f"Missing contract file for '{cid}': {exec_path}")
            exec_hash = _compute_contract_sha256(exec_path)
            if entry.get("plan_sha256") is not None and plan_hash != str(entry["plan_sha256"]).lower():
                raise ValueError(
                    f"SHA-256 mismatch for contract '{cid}' plan file: expected {str(entry['plan_sha256']).lower()}, got {plan_hash}"
                )
            if entry.get("exec_sha256") is not None and exec_hash != str(entry["exec_sha256"]).lower():
                raise ValueError(
                    f"SHA-256 mismatch for contract '{cid}' exec file: expected {str(entry['exec_sha256']).lower()}, got {exec_hash}"
                )
            actual_hash = hashlib.sha256(f"{plan_hash}:{exec_hash}".encode("utf-8")).hexdigest()
        else:
            actual_hash = plan_hash

        if actual_hash != expected_hash.lower():
            raise ValueError(
                f"SHA-256 mismatch for contract '{cid}': expected {expected_hash.lower()}, got {actual_hash}"
            )
        verified[cid] = actual_hash
    return verified


def resolve_contract_metadata(
    arm: str,
    registry_path: Optional[Path] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(contract_version, contract_hash)`` for an arm, or ``(None, None)``."""
    contract_id = ARM_TO_CONTRACT_ID.get(arm)
    if contract_id is None:
        return None, None
    path = Path(registry_path) if registry_path is not None else DEFAULT_CONTRACT_REGISTRY
    if not path.is_file():
        return contract_id, None
    registry = load_contract_registry(path)
    entry = registry.get(contract_id)
    if entry is None:
        return contract_id, None
    return contract_id, entry.get("sha256")


_WRAPPER_NODE_TYPES = frozenset({"export_statement", "decorated_definition"})
_AST_SYMBOL_NODE_TYPES = frozenset(repo_map.DEF_NODE_TYPES) - _WRAPPER_NODE_TYPES
_FUNC_VALUE_NODE_TYPES = frozenset({"arrow_function", "function_expression", "function"})


def _is_ast_symbol_node(node: Any) -> bool:
    if node.type in _AST_SYMBOL_NODE_TYPES:
        return True
    if node.type == "variable_declarator":
        val = node.child_by_field_name("value") if hasattr(node, "child_by_field_name") else None
        if val is not None and val.type in _FUNC_VALUE_NODE_TYPES:
            return True
    return False


def extract_ast_symbol_spans(target: Path, code: str) -> Optional[List[Tuple[str, int, int]]]:
    """Return ``(symbol_key, start_line, end_line)`` spans (1-based) for definitions in *code*."""
    if target.suffix == ".py":
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None
        spans: List[Tuple[str, int, int]] = []

        def _visit(node: ast.AST, prefix: str) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    qname = f"{prefix}.{child.name}" if prefix else child.name
                    decorator_lines = [d.lineno for d in getattr(child, "decorator_list", ()) if hasattr(d, "lineno")]
                    start = min([child.lineno, *decorator_lines])
                    end = getattr(child, "end_lineno", child.lineno) or child.lineno
                    spans.append((qname, start, end))
                    _visit(child, qname)
                else:
                    _visit(child, prefix)

        _visit(tree, "")
        return spans

    lang = repo_map.filename_to_lang(str(target))
    if not lang:
        return None
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
        lines = code.splitlines()
        seen: set[Tuple[int, int, str]] = set()
        spans = []
        for nodes in tc.nodes:
            for node in nodes:
                if not _is_ast_symbol_node(node):
                    continue
                pos = (node.start_point[0], node.start_point[1], node.type)
                if pos in seen:
                    continue
                seen.add(pos)
                name_node = node.child_by_field_name("name") if hasattr(node, "child_by_field_name") else None
                if name_node is not None and hasattr(name_node, "text") and name_node.text:
                    sym_name = name_node.text.decode("utf-8", errors="replace") if isinstance(name_node.text, bytes) else str(name_node.text)
                else:
                    row = node.start_point[0]
                    sym_name = lines[row].strip() if 0 <= row < len(lines) else f"L{row + 1}"
                spans.append((f"{node.type}:{sym_name}", node.start_point[0] + 1, node.end_point[0] + 1))
        return spans
    except Exception:
        return None


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

    spans = extract_ast_symbol_spans(target, code)
    if spans is not None and (target.suffix == ".py" or len(spans) > 0):
        return len(spans)

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

    rel_files: List[Tuple[str, Path]] = []
    for fp in files:
        try:
            rel = fp.resolve().relative_to(root).as_posix()
        except (ValueError, OSError, RuntimeError):
            continue
        rel_files.append((rel, fp))

    file_blocks: List[Tuple[str, str]] = []
    for rel, fp in sorted(rel_files, key=lambda item: item[0]):
        symbols = repo_map.extract_symbols_from_file(fp)
        if symbols:
            file_blocks.append((rel, symbols))

    if not file_blocks:
        return "# Repository Map: No AST symbols detected."

    enc = tiktoken.get_encoding(repo_map.ENCODING_NAME)
    return repo_map.binary_search_prune(file_blocks, max_tokens, enc)


def _iter_workspace_files(workspace: Optional[Path]) -> List[Tuple[str, Path]]:
    """Collect sorted ``(rel_posix, path)`` workspace files ignoring caches and INSTRUCTIONS.md."""
    if workspace is None or not workspace.exists() or not workspace.is_dir():
        return []
    root = workspace.resolve()
    collected: List[Tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _WORKSPACE_IGNORE_DIRS)
        for fname in sorted(filenames):
            if fname in _WORKSPACE_IGNORE_NAMES:
                continue
            fp = Path(dirpath, fname)
            if fp.suffix in _WORKSPACE_IGNORE_SUFFIXES:
                continue
            try:
                resolved = fp.resolve()
                rel = resolved.relative_to(root).as_posix()
            except (ValueError, OSError, RuntimeError):
                continue
            if resolved.is_file():
                collected.append((rel, fp))
    collected.sort(key=lambda item: item[0])
    return collected


def _detect_test_runner(workspace: Optional[Path], rel_files: List[Tuple[str, Path]]) -> str:
    """Deterministically detect the workspace test runner command."""
    if workspace is None or not workspace.exists():
        return "none detected"

    rel_map = {rel: fp for rel, fp in rel_files}
    if any(rel == "pytest.ini" or rel == "conftest.py" or rel.endswith("/conftest.py") for rel in rel_map):
        return "pytest -q --tb=short"

    for cfg_name in ("pyproject.toml", "setup.cfg"):
        cfg_path = rel_map.get(cfg_name)
        if cfg_path is not None:
            try:
                cfg_text = cfg_path.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                cfg_text = ""
            if "pytest" in cfg_text:
                return "pytest -q --tb=short"

    has_pytest_import = False
    has_unittest_import = False
    has_test_files = False
    for rel, fp in rel_files:
        name = Path(rel).name
        if not ((name.startswith("test_") or name.endswith("_test.py")) and name.endswith(".py")):
            continue
        has_test_files = True
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _PYTEST_IMPORT_RE.search(text):
            has_pytest_import = True
        if _UNITTEST_IMPORT_RE.search(text) or "unittest.TestCase" in text:
            has_unittest_import = True

    if has_pytest_import:
        return "pytest -q --tb=short"
    if has_unittest_import:
        return "python -m unittest discover -s tests" if (workspace / "tests").is_dir() else "python -m unittest discover"
    if has_test_files:
        return "pytest -q --tb=short"
    return "none detected"


def build_static_context_prefix(
    workspace: Optional[Path],
    max_tokens: int = ICM_V3_REPO_MAP_MAX_TOKENS,
) -> str:
    """Build a strictly byte-deterministic Layer-3 prefix (file list + test runner + AST map)."""
    rel_files = _iter_workspace_files(workspace)
    file_list = "\n".join(f"- {rel}" for rel, _ in rel_files) if rel_files else "(none)"
    test_runner = _detect_test_runner(workspace, rel_files)
    symbol_map = build_compact_repo_map(workspace, max_tokens=max_tokens)
    return (
        "## Static Workspace Context\n"
        f"### Workspace Files\n{file_list}\n\n"
        f"### Detected Test Runner\n{test_runner}\n\n"
        f"### Pre-Injected AST Symbol Map\n{symbol_map}"
    )


def _workspace_footprint(workspace: Optional[Path]) -> Tuple[int, int]:
    """Return ``(file_count, total_loc)`` across non-binary workspace source/text files."""
    file_count = 0
    total_loc = 0
    for _, fp in _iter_workspace_files(workspace):
        try:
            raw = fp.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        file_count += 1
        total_loc += len(text.replace("\r\n", "\n").splitlines())
    return file_count, total_loc


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
    explicit_arms = {
        "icm-lite": ICM_LITE,
        "icm-v2": ICM_V2,
        "icm-v3": ICM_V3,
        "icm-staged": ICM_STAGED,
        "baseline": "baseline",
        "icm": "icm",
    }
    if mode in explicit_arms:
        arm = explicit_arms[mode]
        c_ver, c_hash = resolve_contract_metadata(arm)
        return RoutingDecision(arm, "unknown", None, False, None, contract_version=c_ver, contract_hash=c_hash)
    if mode not in ("auto", "auto-v3"):
        raise ValueError(f"Unsupported routing mode: {mode!r}")

    single_file, target = _single_target(metadata, workspace)
    rel_target = None
    if target is not None:
        try:
            rel_target = target.relative_to(workspace.resolve()).as_posix()
        except ValueError:
            rel_target = str(target)

    if mode == "auto-v3":
        file_count, total_loc = _workspace_footprint(workspace)
        multi_stage = bool(metadata.get("multi_stage"))
        if multi_stage or file_count > 50:
            arm = ICM_STAGED
        elif file_count <= 12 and total_loc <= 1500:
            arm = ICM_LITE
        else:
            arm = ICM_V3
        if metadata.get("target_files") is None and metadata.get("target_files_count") is None:
            single_file = file_count == 1
        ast_symbol_count = count_ast_symbols(target)
        c_ver, c_hash = resolve_contract_metadata(arm)
        return RoutingDecision(
            arm,
            "workspace_footprint",
            total_loc,
            single_file,
            rel_target,
            ast_symbol_count=ast_symbol_count,
            contract_version=c_ver,
            contract_hash=c_hash,
        )

    loc, loc_source = _scoped_loc(metadata, target)
    ast_symbol_count = count_ast_symbols(target)

    within_loc = loc is not None and loc < LOC_THRESHOLD
    within_symbols = (
        ast_symbol_count is None
        or loc_source != "file_loc"
        or ast_symbol_count < SYMBOL_THRESHOLD
    )
    arm = ICM_LITE if single_file and within_loc and within_symbols else "icm"
    c_ver, c_hash = resolve_contract_metadata(arm)
    return RoutingDecision(
        arm,
        loc_source,
        loc,
        single_file,
        rel_target,
        ast_symbol_count=ast_symbol_count,
        contract_version=c_ver,
        contract_hash=c_hash,
    )


def resolve_mode(mode: str, metadata: Mapping[str, Any], workspace: Path) -> str:
    """Return the arm ID; unknown or ambiguous complexity uses full ICM."""
    return classify_mode(mode, metadata, workspace).arm


def build_staged_exec_prompt(
    instructions: str,
    plan_text: str,
    workspace: Optional[Path] = None,
    repo_map_max_tokens: Optional[int] = None,
    static_prefix: Optional[str] = None,
) -> str:
    """Build the Phase 2 fresh-context execution prompt from the compact Phase 1 plan."""
    max_tokens = ICM_STAGED_REPO_MAP_MAX_TOKENS if repo_map_max_tokens is None else repo_map_max_tokens
    exec_contract = STAGED_EXEC_CONTRACT.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    if static_prefix is None and workspace is not None and workspace.exists():
        static_prefix = build_static_context_prefix(workspace, max_tokens=max_tokens)
    plan_body = (plan_text or "").strip() or "(no plan produced)"
    plan_block = f"## Approved Phase 1 Compact Plan\n{plan_body}"
    parts = [p for p in (static_prefix, exec_contract, plan_block, instructions) if p]
    return "\n\n".join(parts)


def build_staged_prompts(
    instructions: str,
    workspace: Optional[Path] = None,
    plan_text: Optional[str] = None,
    repo_map_max_tokens: Optional[int] = None,
) -> Tuple[str, str]:
    """Build the ``(phase1_plan_prompt, phase2_exec_prompt)`` pair sharing the static workspace prefix."""
    max_tokens = ICM_STAGED_REPO_MAP_MAX_TOKENS if repo_map_max_tokens is None else repo_map_max_tokens
    plan_contract = STAGED_PLAN_CONTRACT.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    static_prefix: Optional[str] = None
    if workspace is not None and workspace.exists():
        static_prefix = build_static_context_prefix(workspace, max_tokens=max_tokens)
    phase1_parts = [p for p in (static_prefix, plan_contract, instructions) if p]
    phase1_prompt = "\n\n".join(phase1_parts)
    phase2_prompt = build_staged_exec_prompt(
        instructions=instructions,
        plan_text=plan_text or "",
        workspace=workspace,
        repo_map_max_tokens=max_tokens,
        static_prefix=static_prefix,
    )
    return phase1_prompt, phase2_prompt


def build_mode_prompt(
    instructions: str,
    arm: str,
    workspace: Optional[Path] = None,
    repo_map_max_tokens: Optional[int] = None,
) -> str:
    if arm == "baseline":
        return instructions
    if arm == ICM_LITE:
        contract = LITE_CONTRACT.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
        return f"{contract}\n\n{instructions}"
    if arm == ICM_V2:
        max_tokens = ICM_V2_REPO_MAP_MAX_TOKENS if repo_map_max_tokens is None else repo_map_max_tokens
        contract = V2_CONTRACT.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
        if workspace is not None and workspace.exists():
            symbol_map = build_compact_repo_map(workspace, max_tokens=max_tokens)
            return f"{contract}\n\n## Pre-Injected AST Symbol Map\n{symbol_map}\n\n{instructions}"
        return f"{contract}\n\n{instructions}"
    if arm == ICM_V3:
        max_tokens = ICM_V3_REPO_MAP_MAX_TOKENS if repo_map_max_tokens is None else repo_map_max_tokens
        contract = V3_CONTRACT.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
        if workspace is not None and workspace.exists():
            static_prefix = build_static_context_prefix(workspace, max_tokens=max_tokens)
            return f"{contract}\n\n{static_prefix}\n\n{instructions}"
        return f"{contract}\n\n{instructions}"
    if arm == ICM_STAGED:
        return build_staged_prompts(
            instructions,
            workspace=workspace,
            repo_map_max_tokens=repo_map_max_tokens,
        )[0]
    return f"{FULL_CONTRACT}\n\n{instructions}"
