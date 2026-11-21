"""Deterministic selection of experiment contracts from declared task scope."""

import re
from pathlib import Path
from typing import Any, Mapping, Optional

MODES = ("auto", "icm", "icm-lite", "baseline")
ICM_LITE = "icm_lite"
LOC_THRESHOLD = 150
LITE_CONTRACT = Path(__file__).resolve().parents[1] / "tasks" / "_template" / "icm_lite.md"

FULL_CONTRACT = """Execute this task using the full 5-stage ICM contract:
1. 01_intake: Establish scope, constraints, and context budget.
2. 02_plan: Identify impacted files and machine-verifiable acceptance criteria.
3. 03_exec: Apply targeted, diff-only edits and record the symbols changed.
4. 04_verify: Run the relevant automated checks through output sanitation and record results.
5. 05_retro: Record lessons and any follow-up needed without expanding the task's edit scope."""


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


def _estimated_loc(metadata: Mapping[str, Any], target: Optional[Path]) -> Optional[int]:
    estimate = metadata.get("estimated_loc")
    if estimate is not None:
        return estimate if type(estimate) is int and estimate >= 0 else None

    loc_range = metadata.get("target_loc_range")
    if loc_range is not None:
        match = re.fullmatch(r"([0-9]+)-([0-9]+)", str(loc_range))
        if match:
            low, high = map(int, match.groups())
            if low <= high:
                return high
        return None

    if target is not None and target.is_file():
        try:
            with target.open(encoding="utf-8") as source:
                return sum(1 for _ in source)
        except (OSError, UnicodeError):
            pass
    return None


def resolve_mode(mode: str, metadata: Mapping[str, Any], workspace: Path) -> str:
    """Return the arm ID; unknown or ambiguous complexity uses full ICM."""
    if mode == "icm-lite":
        return ICM_LITE
    if mode in ("baseline", "icm"):
        return mode
    if mode != "auto":
        raise ValueError(f"Unsupported routing mode: {mode!r}")

    single_file, target = _single_target(metadata, workspace)
    if single_file:
        loc = _estimated_loc(metadata, target)
        if loc is not None and loc < LOC_THRESHOLD:
            return ICM_LITE
    return "icm"


def build_mode_prompt(instructions: str, arm: str) -> str:
    if arm == "baseline":
        return instructions
    contract = LITE_CONTRACT.read_text(encoding="utf-8").rstrip() if arm == ICM_LITE else FULL_CONTRACT
    return f"{contract}\n\n{instructions}"
