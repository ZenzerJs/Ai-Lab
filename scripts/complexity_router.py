"""Deterministic selection of experiment contracts from declared task scope."""

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any, Mapping, Optional
import warnings

MODES = ("auto", "icm", "icm-lite", "baseline")
ICM_LITE = "icm_lite"
LOC_THRESHOLD = 150
LOC_SOURCES = ("estimated_loc", "target_loc_range", "file_loc", "unknown")
LITE_CONTRACT = Path(__file__).resolve().parents[1] / "tasks" / "_template" / "icm_lite.md"

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
    """Resolve the arm and report which scope source supplied the LOC evidence."""
    if mode == "icm-lite":
        return RoutingDecision(ICM_LITE, "unknown", None, False, None)
    if mode in ("baseline", "icm"):
        return RoutingDecision(mode, "unknown", None, False, None)
    if mode != "auto":
        raise ValueError(f"Unsupported routing mode: {mode!r}")

    single_file, target = _single_target(metadata, workspace)
    loc, loc_source = _scoped_loc(metadata, target)
    arm = ICM_LITE if single_file and loc is not None and loc < LOC_THRESHOLD else "icm"
    rel_target = None
    if target is not None:
        try:
            rel_target = target.relative_to(workspace.resolve()).as_posix()
        except ValueError:
            rel_target = str(target)
    return RoutingDecision(arm, loc_source, loc, single_file, rel_target)


def resolve_mode(mode: str, metadata: Mapping[str, Any], workspace: Path) -> str:
    """Return the arm ID; unknown or ambiguous complexity uses full ICM."""
    return classify_mode(mode, metadata, workspace).arm


def build_mode_prompt(instructions: str, arm: str) -> str:
    if arm == "baseline":
        return instructions
    contract = LITE_CONTRACT.read_text(encoding="utf-8").rstrip() if arm == ICM_LITE else FULL_CONTRACT
    return f"{contract}\n\n{instructions}"
