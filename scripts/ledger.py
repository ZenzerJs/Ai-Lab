#!/usr/bin/env python3
"""
scripts/ledger.py - SQLite Storage Engine for A/B Token Usage & Cost Analytics

Manages tables for runs, tasks, and cache-aware model pricing.
Enforces auditable rate seeding from config/PRICING.json.
Provides analytical functions for per-task comparison and cumulative savings.
"""

import ast
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = DEFAULT_ROOT / "data" / "usage.db"
DEFAULT_PRICING_PATH = DEFAULT_ROOT / "config" / "PRICING.json"

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from pricing import (  # noqa: E402
    COST_SOURCE_BILLED_DIRECT,
    COST_SOURCE_ESTIMATED_ACU_DERIVED,
    COST_SOURCE_UNAVAILABLE,
    DEFAULT_DEVIN_ACU_USD_RATE,
    calculate_acu_cost,
    classify_cost_source,
    get_devin_acu_usd_rate,
    validate_acus_consumed,
)

# Trailing effort levels telemetry appends to a base model id
# (e.g. gemini-4-argon-low -> gemini-4-argon).
EFFORT_SUFFIXES = frozenset({"low", "medium", "high", "xhigh"})


def base_model_id(model: str) -> str:
    """Strip one trailing effort suffix for pricing fallback lookups."""
    if not isinstance(model, str):
        return model
    base, sep, suffix = model.rpartition("-")
    if sep and base and suffix.lower() in EFFORT_SUFFIXES:
        return base
    return model


def sanitize_export_text(text: Optional[str]) -> Optional[str]:
    """Redact private file paths and sentinel secrets from public export."""
    if not text:
        return text
    # Windows user paths (both backslash and forward slash)
    cleaned = re.sub(r"[A-Za-z]:[\\/][Uu]sers[\\/][^\\/]+[\\/]", lambda _: r".../...", text)
    # Unix user paths
    cleaned = re.sub(r"/(?:home|Users)/[^/]+/", lambda _: ".../", cleaned)
    # Generic key-value secret patterns: api_key=..., key: ..., token: ..., secret=..., password=...
    cleaned = re.sub(
        r"(?:(?:api[_-]?)?key|secret|token|password|auth|bearer)\s*[:=]\s*[^\s,;\"'}{]+",
        lambda _: "[REDACTED_SECRET]",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Provider-specific key tokens:
    # Google AI Studio / Gemini: AIzaSy...
    cleaned = re.sub(r"AIzaSy[a-zA-Z0-9_-]{30,}", "[REDACTED_SECRET]", cleaned)
    # Anthropic API Key: sk-ant-...
    cleaned = re.sub(r"sk-ant-[a-zA-Z0-9_-]{20,}", "[REDACTED_SECRET]", cleaned)
    # OpenAI API Key: sk-... (including sk-proj-...)
    cleaned = re.sub(r"sk-(?:proj-)?[a-zA-Z0-9_-]{20,}", "[REDACTED_SECRET]", cleaned)
    # GitHub Token: ghp_..., gho_..., github_pat_...
    cleaned = re.sub(r"(?:gh[pours]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{50,})", "[REDACTED_SECRET]", cleaned)
    return cleaned


PUBLIC_RUN_KEYS = {
    "id",
    "task_id",
    "arm",
    "model",
    "run_index",
    "timestamp",
    "input_tokens",
    "output_tokens",
    "thinking_tokens",
    "cache_read_tokens",
    "total_tokens",
    "num_turns",
    "duration_seconds",
    "source_kind",
    "evidence_status",
    "exclusion_reasons",
    "cost_status",
    "cost_usd",
    "cost_source",
    "acus_consumed",
    "acu_usd_rate",
    "estimated_cost_usd",
    "is_simulation",
    "execution_status",
    "verification_status",
    "manifest_id",
    "evaluator_hash",
    "is_eligible",
    "is_comparison_eligible",
    "provenance_valid",
    "reporting_category",
    "evidence_ref",
    "notes",
    "tool_calls_count",
    "tool_errors_count",
    "max_consecutive_tool_streak",
    "loop_detected",
}


def to_public_run(run: Dict[str, Any], sanitize: bool = True) -> Dict[str, Any]:
    """Convert an internal run dict to an allowlisted sanitized public representation."""
    out = {}
    for k in PUBLIC_RUN_KEYS:
        if k in run:
            out[k] = run[k]

    out.setdefault("source_kind", run.get("source_kind") or "unknown")
    out.setdefault("evidence_status", run.get("evidence_status") or "unverified")
    out["cost_source"] = classify_cost_source(out)
    if (
        out["cost_source"] == COST_SOURCE_ESTIMATED_ACU_DERIVED
        and out.get("estimated_cost_usd") is None
        and out.get("cost_usd") is not None
    ):
        out["estimated_cost_usd"] = out["cost_usd"]

    if isinstance(out.get("exclusion_reasons"), str):
        try:
            out["exclusion_reasons"] = json.loads(out["exclusion_reasons"])
        except Exception:
            pass

    if sanitize:
        if out.get("evidence_ref"):
            ref_str = str(out["evidence_ref"])
            filename = re.split(r"[\\/]", ref_str)[-1]
            out["evidence_ref"] = sanitize_export_text(filename)
        if out.get("notes"):
            out["notes"] = sanitize_export_text(str(out["notes"]))

    return out


class TelemetryValidationError(ValueError):
    """Raised when telemetry NDJSON syntax or fields are invalid."""
    def __init__(self, message: str, line_number: Optional[int] = None, event_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.line_number = line_number
        self.event_data = event_data


class DuplicateConflictError(ValueError):
    """Raised when an import arrives with an existing import_id but conflicting data."""
    pass


def reconstruct_total_tokens(
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    thinking_tokens: Optional[int],
    cache_read_tokens: Optional[int],
    adapter_name: Optional[str],
) -> Optional[int]:
    """
    Reconstruct total_tokens strictly under an explicit adapter schema (Finding 4).
    Prevents double-counting when cache_read or thinking tokens overlap with input/output.
    """
    if input_tokens is None:
        return None

    out = output_tokens or 0
    has_extra = (cache_read_tokens is not None or thinking_tokens is not None)

    # If neither cache nor thinking counters are present, total is simply input + output
    if not has_extra:
        return input_tokens + out

    # Extra counters present: require explicit adapter schema to avoid double-counting
    if not adapter_name:
        return None

    adapter = str(adapter_name).lower()
    cache = cache_read_tokens or 0

    if "subset" in adapter or any(m in adapter for m in ("anthropic", "claude")):
        # In Anthropic / subset schema:
        # - input_tokens already includes cache_read_tokens
        # - output_tokens already includes thinking_tokens
        return input_tokens + out
    elif "separate" in adapter or any(m in adapter for m in ("gemini", "openai")):
        # In separate schema:
        # - input_tokens does not include cache_read_tokens
        # - output_tokens already includes thinking_tokens or separate
        return input_tokens + out + cache
    return None


_TOOL_TARGET_PARAM_KEYS = (
    "target_path",
    "TargetFile",
    "AbsolutePath",
    "path",
    "file_path",
    "FilePath",
    "DirectoryPath",
    "SearchPath",
    "SearchDirectory",
    "NotebookPath",
)


def _iter_ndjson_lines(stream: Any) -> List[Any]:
    """Normalize Path, str, bytes, file-like, or sequence into a list of raw lines/dicts."""
    if stream is None:
        return []
    if isinstance(stream, (Path, os.PathLike)):
        return Path(stream).read_text(encoding="utf-8", errors="replace").splitlines()
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace").splitlines()
    if isinstance(stream, str):
        return stream.splitlines()
    if hasattr(stream, "read"):
        content = stream.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return content.splitlines()
    if isinstance(stream, (list, tuple)):
        return list(stream)
    return list(stream)


def _extract_target_path(step_update: Dict[str, Any]) -> Optional[str]:
    """Extract target file or directory path from a step_update tool payload."""
    if step_update.get("target_path"):
        return str(step_update["target_path"])
    tool_info = step_update.get("tool_info")
    if isinstance(tool_info, dict):
        params = tool_info.get("parameters")
        if isinstance(params, dict):
            for key in _TOOL_TARGET_PARAM_KEYS:
                val = params.get(key)
                if val:
                    return str(val)
    return None


def extract_ndjson_tool_metrics(
    stream: Any,
    streak_threshold: int = 6,
    error_threshold: int = 3,
) -> Dict[str, Any]:
    """
    Parse agy stream-json NDJSON lines for tool calls, tool errors, and loop detection.
    Deduplicates `step_update` records by `step_index`, keeping the final state per step,
    and computes metrics over steps with `step_type == "tool"`.
    """
    raw_lines = _iter_ndjson_lines(stream)
    steps_by_index: Dict[Tuple[int, int], Dict[str, Any]] = {}
    anon_seq = 0

    for item in raw_lines:
        if isinstance(item, dict):
            ev = item
        else:
            line = str(item).strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(ev, dict):
                continue

        if ev.get("event") != "step_update":
            continue

        su = ev.get("step_update") if isinstance(ev.get("step_update"), dict) else ev
        step_idx = su.get("step_index")
        if step_idx is not None:
            try:
                key = (0, int(step_idx))
            except (TypeError, ValueError):
                anon_seq += 1
                key = (1, anon_seq)
        else:
            anon_seq += 1
            key = (1, anon_seq)
        steps_by_index[key] = su

    tool_steps = [
        steps_by_index[k]
        for k in sorted(steps_by_index.keys())
        if steps_by_index[k].get("step_type") == "tool"
    ]

    tool_calls_count = len(tool_steps)
    tool_errors_count = 0
    max_streak = 0
    cur_streak = 0
    prev_tool: Optional[str] = None
    events: List[Dict[str, Any]] = []

    for seq, step in enumerate(tool_steps, start=1):
        tool_info = step.get("tool_info") if isinstance(step.get("tool_info"), dict) else {}
        tool_name = step.get("tool_name") or tool_info.get("name")
        tool_name_str = str(tool_name) if tool_name else None
        status = str(step.get("state") or step.get("status") or "UNKNOWN")

        if status == "ERROR":
            tool_errors_count += 1

        if tool_name_str and tool_name_str == prev_tool:
            cur_streak += 1
        elif tool_name_str:
            cur_streak = 1
            prev_tool = tool_name_str
        else:
            cur_streak = 0
            prev_tool = None

        if cur_streak > max_streak:
            max_streak = cur_streak

        events.append({
            "seq": seq,
            "phase": str(step.get("phase") or "tool"),
            "tool_name": tool_name_str,
            "target_path": _extract_target_path(step),
            "status": status,
        })

    loop_detected = bool(
        max_streak >= streak_threshold or tool_errors_count >= error_threshold
    )

    return {
        "tool_calls_count": tool_calls_count,
        "tool_errors_count": tool_errors_count,
        "max_consecutive_tool_streak": max_streak,
        "loop_detected": loop_detected,
        "events": events,
    }


def validate_and_parse_telemetry(
    stream: Any,
    adapter_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse and validate NDJSON telemetry event stream.
    Enforces:
    - TEL-01: Malformed JSON or invalid event objects raise TelemetryValidationError with line number.
    - TEL-02: Missing usage counters remain None (unknown), not 0.
    - TEL-03: Negative or non-numeric counters/durations rejected.
    - TEL-04: Replayed identical events deduplicated without double counting.
    - TEL-05: Final cumulative usage from run_complete is not double-summed with per-turn events.
    """
    if isinstance(stream, str):
        lines = stream.splitlines()
    elif isinstance(stream, list):
        lines = stream
    else:
        raise TelemetryValidationError("Telemetry stream must be a list of strings or a single string")

    seen_event_ids: Dict[str, Dict[str, Any]] = {}
    seen_event_lines: set = set()
    seen_turns: Dict[int, Dict[str, Any]] = {}

    task_id = None
    arm = None
    model = None
    run_index = None
    timestamp = None
    resolved_adapter_name = adapter_name
    num_turns = 0
    duration_seconds = 0.0
    acus_consumed: Optional[float] = None
    devin_session_id: Optional[str] = None

    cumulative_usage: Optional[Dict[str, Any]] = None
    turn_usages: List[Dict[str, Any]] = []
    has_run_complete = False

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TelemetryValidationError(
                f"Line {idx}: Malformed NDJSON syntax: {exc}", line_number=idx
            ) from exc

        if not isinstance(event, dict):
            raise TelemetryValidationError(
                f"Line {idx}: Event must be a JSON object, got {type(event).__name__}",
                line_number=idx,
            )

        if "task_id" in event and event["task_id"]:
            task_id = str(event["task_id"])
        if "arm" in event and event["arm"]:
            arm = str(event["arm"])
        if "model" in event and event["model"]:
            model = str(event["model"])
        elif model is None and isinstance(event.get("init"), dict) and event["init"].get("model"):
            model = str(event["init"]["model"])
        if "timestamp" in event and event["timestamp"]:
            timestamp = str(event["timestamp"])
        if "adapter_name" in event and event["adapter_name"]:
            resolved_adapter_name = str(event["adapter_name"])
        elif "adapter" in event and event["adapter"]:
            resolved_adapter_name = str(event["adapter"])
        elif "cache_accounting" in event and event["cache_accounting"]:
            resolved_adapter_name = str(event["cache_accounting"])
        elif isinstance(event.get("usage"), dict):
            if "adapter_name" in event["usage"] and event["usage"]["adapter_name"]:
                resolved_adapter_name = str(event["usage"]["adapter_name"])
            elif "cache_accounting" in event["usage"] and event["usage"]["cache_accounting"]:
                resolved_adapter_name = str(event["usage"]["cache_accounting"])

        # Extract Devin session ACU telemetry when present in NDJSON events
        raw_devin_id = (
            event.get("devin_session_id")
            or event.get("devin_id")
            or (
                event["devin_session"].get("session_id") or event["devin_session"].get("devin_id")
                if isinstance(event.get("devin_session"), dict)
                else None
            )
        )
        if raw_devin_id:
            devin_session_id = str(raw_devin_id)

        if "run_index" in event and event["run_index"] is not None:
            try:
                ridx = int(event["run_index"])
                if ridx < 0:
                    raise TelemetryValidationError(
                        f"Line {idx}: 'run_index' cannot be negative ({ridx})", line_number=idx
                    )
                run_index = ridx
            except (ValueError, TypeError):
                raise TelemetryValidationError(
                    f"Line {idx}: Invalid 'run_index': {event['run_index']}", line_number=idx
                )

        def _check_int(val: Any, field_name: str) -> Optional[int]:
            if val is None:
                return None
            if isinstance(val, bool):
                raise TelemetryValidationError(
                    f"Line {idx}: Counter '{field_name}' must be an integer, got boolean: {val}",
                    line_number=idx,
                    event_data=event,
                )
            if isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    raise TelemetryValidationError(
                        f"Line {idx}: Counter '{field_name}' cannot be non-finite float (NaN/Inf): {val}",
                        line_number=idx,
                        event_data=event,
                    )
                if not val.is_integer():
                    raise TelemetryValidationError(
                        f"Line {idx}: Counter '{field_name}' cannot be a non-integer float: {val}",
                        line_number=idx,
                        event_data=event,
                    )
                val = int(val)
            try:
                ival = int(val)
            except (ValueError, TypeError):
                raise TelemetryValidationError(
                    f"Line {idx}: Counter '{field_name}' must be an integer, got: {val}",
                    line_number=idx,
                    event_data=event,
                )
            if ival < 0:
                raise TelemetryValidationError(
                    f"Line {idx}: Counter '{field_name}' cannot be negative ({val})",
                    line_number=idx,
                    event_data=event,
                )
            return ival

        def _check_float(val: Any, field_name: str) -> Optional[float]:
            if val is None:
                return None
            if isinstance(val, bool):
                raise TelemetryValidationError(
                    f"Line {idx}: Field '{field_name}' must be a float, got boolean: {val}",
                    line_number=idx,
                    event_data=event,
                )
            try:
                fval = float(val)
            except (ValueError, TypeError):
                raise TelemetryValidationError(
                    f"Line {idx}: Field '{field_name}' must be a float, got: {val}",
                    line_number=idx,
                    event_data=event,
                )
            if math.isnan(fval) or math.isinf(fval):
                raise TelemetryValidationError(
                    f"Line {idx}: Field '{field_name}' cannot be non-finite float (NaN/Inf): {val}",
                    line_number=idx,
                    event_data=event,
                )
            if fval < 0.0:
                raise TelemetryValidationError(
                    f"Line {idx}: Field '{field_name}' cannot be negative ({val})",
                    line_number=idx,
                    event_data=event,
                )
            return fval

        if "duration_seconds" in event and event["duration_seconds"] is not None:
            dur = _check_float(event["duration_seconds"], "duration_seconds")
            if dur is not None:
                duration_seconds = dur

        # Deduplication (TEL-04)
        ev_id = event.get("event_id") or event.get("id")
        if ev_id is not None:
            ev_id_str = str(ev_id)
            if ev_id_str in seen_event_ids:
                if seen_event_ids[ev_id_str] == event:
                    continue  # Exact duplicate event replayed
                else:
                    raise TelemetryValidationError(
                        f"Line {idx}: Duplicate event_id '{ev_id_str}' with conflicting content",
                        line_number=idx,
                        event_data=event,
                    )
            seen_event_ids[ev_id_str] = event
        else:
            event_hash = json.dumps(event, sort_keys=True)
            if event_hash in seen_event_lines:
                continue  # Exact line duplication replayed
            seen_event_lines.add(event_hash)

        ev_type = str(event.get("type") or event.get("event") or "").lower()

        raw_acus = event.get("acus_consumed")
        if raw_acus is None and isinstance(event.get("usage"), dict):
            raw_acus = event["usage"].get("acus_consumed")
        if raw_acus is None and isinstance(event.get("devin_session"), dict):
            raw_acus = event["devin_session"].get("acus_consumed")
        if raw_acus is None and isinstance(event.get("result"), dict):
            res_dict = event["result"]
            raw_acus = res_dict.get("acus_consumed")
            if raw_acus is None and isinstance(res_dict.get("usage"), dict):
                raw_acus = res_dict["usage"].get("acus_consumed")
        if raw_acus is not None:
            try:
                acus_consumed = validate_acus_consumed(raw_acus)
            except ValueError as exc:
                raise TelemetryValidationError(
                    f"Line {idx}: Invalid 'acus_consumed': {exc}",
                    line_number=idx,
                    event_data=event,
                ) from exc

        # Turn event
        if ev_type == "turn" or "turn" in event:
            t = _check_int(event.get("turn", 0), "turn")
            if t and t > num_turns:
                num_turns = t

            u_obj = event.get("usage") if isinstance(event.get("usage"), dict) else event
            has_turn_usage = any(
                k in u_obj
                for k in ("input_tokens", "output_tokens", "thinking_tokens", "cache_read_tokens", "total_tokens")
            )
            if has_turn_usage:
                turn_u = {
                    "input_tokens": _check_int(u_obj.get("input_tokens"), "input_tokens"),
                    "output_tokens": _check_int(u_obj.get("output_tokens"), "output_tokens"),
                    "thinking_tokens": _check_int(u_obj.get("thinking_tokens"), "thinking_tokens"),
                    "cache_read_tokens": _check_int(u_obj.get("cache_read_tokens"), "cache_read_tokens"),
                    "total_tokens": _check_int(u_obj.get("total_tokens"), "total_tokens"),
                }
                if t is not None:
                    if t in seen_turns:
                        if seen_turns[t] != turn_u:
                            raise TelemetryValidationError(
                                f"Line {idx}: Conflicting turn usage for turn {t}",
                                line_number=idx,
                                event_data=event,
                            )
                    else:
                        seen_turns[t] = turn_u
                        turn_usages.append(turn_u)
                else:
                    turn_usages.append(turn_u)

        # Run complete / summary / agy result event
        if ev_type in ("run_complete", "session_end", "summary", "result") or "result" in event:
            res_obj = event.get("result") if isinstance(event.get("result"), dict) else event
            if "num_turns" in res_obj and res_obj["num_turns"] is not None:
                nt = _check_int(res_obj["num_turns"], "num_turns")
                if nt:
                    num_turns = nt
            if "duration_seconds" in res_obj and res_obj["duration_seconds"] is not None:
                dur = _check_float(res_obj["duration_seconds"], "duration_seconds")
                if dur is not None:
                    duration_seconds = dur

            if "usage" in res_obj and isinstance(res_obj["usage"], dict):
                ev_u = res_obj["usage"]
                new_cumulative = {
                    "input_tokens": _check_int(ev_u.get("input_tokens"), "input_tokens"),
                    "output_tokens": _check_int(ev_u.get("output_tokens"), "output_tokens"),
                    "thinking_tokens": _check_int(ev_u.get("thinking_tokens"), "thinking_tokens"),
                    "cache_read_tokens": _check_int(ev_u.get("cache_read_tokens"), "cache_read_tokens"),
                    "total_tokens": _check_int(ev_u.get("total_tokens"), "total_tokens"),
                }
                if (
                    new_cumulative["total_tokens"] is None
                    and new_cumulative["input_tokens"] is not None
                ):
                    new_cumulative["total_tokens"] = reconstruct_total_tokens(
                        input_tokens=new_cumulative["input_tokens"],
                        output_tokens=new_cumulative["output_tokens"],
                        thinking_tokens=new_cumulative["thinking_tokens"],
                        cache_read_tokens=new_cumulative["cache_read_tokens"],
                        adapter_name=resolved_adapter_name,
                    )
                if has_run_complete and cumulative_usage is not None and cumulative_usage != new_cumulative:
                    raise TelemetryValidationError(
                        f"Line {idx}: Multiple conflicting run_complete/result events in stream",
                        line_number=idx,
                        event_data=event,
                    )
                cumulative_usage = new_cumulative
            has_run_complete = True

    turns_with_usage = set(seen_turns.keys())
    is_partial_turn_coverage = bool(num_turns > 1 and len(turns_with_usage) > 0 and len(turns_with_usage) < num_turns)

    # Resolve usage counters
    if cumulative_usage is not None:
        # TEL-05: Final cumulative usage chosen; per-turn usage not double-counted
        final_usage = cumulative_usage
        is_partial_telemetry = False
        field_completeness = {
            "input_tokens": cumulative_usage["input_tokens"] is not None,
            "output_tokens": cumulative_usage["output_tokens"] is not None,
            "thinking_tokens": cumulative_usage["thinking_tokens"] is not None,
            "cache_read_tokens": cumulative_usage["cache_read_tokens"] is not None,
        }
    elif turn_usages:
        has_in = any(u["input_tokens"] is not None for u in turn_usages)
        has_out = any(u["output_tokens"] is not None for u in turn_usages)
        has_think = any(u["thinking_tokens"] is not None for u in turn_usages)
        has_cache = any(u["cache_read_tokens"] is not None for u in turn_usages)
        has_total = any(u["total_tokens"] is not None for u in turn_usages)

        any_in_missing = any(u["input_tokens"] is None for u in turn_usages)
        any_out_missing = any(u["output_tokens"] is None for u in turn_usages)
        any_think_missing = any(u["thinking_tokens"] is None for u in turn_usages)
        any_cache_missing = any(u["cache_read_tokens"] is None for u in turn_usages)
        is_partial_telemetry = is_partial_turn_coverage or any_in_missing or any_out_missing

        sum_in = sum(u["input_tokens"] for u in turn_usages if u["input_tokens"] is not None) if has_in else None
        sum_out = sum(u["output_tokens"] for u in turn_usages if u["output_tokens"] is not None) if has_out else None
        sum_think = sum(u["thinking_tokens"] for u in turn_usages if u["thinking_tokens"] is not None) if has_think else None
        sum_cache = sum(u["cache_read_tokens"] for u in turn_usages if u["cache_read_tokens"] is not None) if has_cache else None
        sum_total = sum(u["total_tokens"] for u in turn_usages if u["total_tokens"] is not None) if has_total else None

        if sum_total is None and sum_in is not None and not is_partial_telemetry:
            sum_total = reconstruct_total_tokens(
                input_tokens=sum_in,
                output_tokens=sum_out,
                thinking_tokens=sum_think,
                cache_read_tokens=sum_cache,
                adapter_name=resolved_adapter_name,
            )

        final_usage = {
            "input_tokens": sum_in,
            "output_tokens": sum_out,
            "thinking_tokens": sum_think,
            "cache_read_tokens": sum_cache,
            "total_tokens": sum_total,
        }
        field_completeness = {
            "input_tokens": has_in and not any_in_missing and not is_partial_turn_coverage,
            "output_tokens": has_out and not any_out_missing and not is_partial_turn_coverage,
            "thinking_tokens": has_think and not any_think_missing and not is_partial_turn_coverage,
            "cache_read_tokens": has_cache and not any_cache_missing and not is_partial_turn_coverage,
        }
    else:
        # TEL-02: Omit usage counters from a completed run -> unknown (None), NOT zero
        is_partial_telemetry = False
        final_usage = {
            "input_tokens": None,
            "output_tokens": None,
            "thinking_tokens": None,
            "cache_read_tokens": None,
            "total_tokens": None,
        }
        field_completeness = {
            "input_tokens": False,
            "output_tokens": False,
            "thinking_tokens": False,
            "cache_read_tokens": False,
        }

    tool_metrics = extract_ndjson_tool_metrics(lines)

    return {
        "task_id": task_id,
        "arm": arm,
        "model": model,
        "run_index": run_index,
        "timestamp": timestamp,
        "usage": final_usage,
        "num_turns": num_turns if num_turns > 0 else 1,
        "duration_seconds": duration_seconds,
        "has_usage": final_usage["input_tokens"] is not None,
        "has_run_complete": has_run_complete,
        "is_partial": is_partial_telemetry,
        "is_partial_turn_coverage": is_partial_turn_coverage,
        "turns_with_usage_count": len(turns_with_usage),
        "adapter_name": resolved_adapter_name,
        "field_completeness": field_completeness,
        "tool_metrics": tool_metrics,
        "acus_consumed": acus_consumed,
        "devin_session_id": devin_session_id,
    }


def validate_evidence_file(
    file_path: Any,
    expected_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate a referenced evidence artifact.
    Returns validation status, integrity boolean, exclusion reason, and actual SHA-256.
    """
    if not file_path:
        return {
            "status": "missing",
            "is_valid": False,
            "exclusion_reason": "evidence_file_missing",
            "actual_hash": None,
            "expected_hash": expected_hash,
        }
    path = Path(file_path)
    if not path.is_file():
        return {
            "status": "missing",
            "is_valid": False,
            "exclusion_reason": "evidence_file_missing",
            "actual_hash": None,
            "expected_hash": expected_hash,
        }
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_hash = h.hexdigest()
    except (OSError, PermissionError) as exc:
        return {
            "status": "unreadable",
            "is_valid": False,
            "exclusion_reason": f"evidence_file_unreadable: {exc}",
            "actual_hash": None,
            "expected_hash": expected_hash,
        }

    if expected_hash:
        if actual_hash.lower() != expected_hash.lower():
            return {
                "status": "invalid",
                "is_valid": False,
                "exclusion_reason": "evidence_hash_mismatch",
                "actual_hash": actual_hash,
                "expected_hash": expected_hash,
            }

    return {
        "status": "verified",
        "is_valid": True,
        "exclusion_reason": None,
        "actual_hash": actual_hash,
        "expected_hash": expected_hash or actual_hash,
    }


def evaluate_run_eligibility(
    run: Dict[str, Any],
    capture_policy: str = "approved",
) -> Dict[str, Any]:
    """
    Shared eligibility, provenance validation, cost completeness, and correctness evaluation rules.
    Decouples provenance validity, correctness evaluation, cost completeness, and comparison eligibility (Finding 1 & 5).
    """
    provenance_reasons: List[str] = []
    cost_reasons: List[str] = []
    execution_reasons: List[str] = []
    correctness_reasons: List[str] = []

    source_kind = str(run.get("source_kind", "unknown")).lower()
    evidence_status = str(run.get("evidence_status", "unverified")).lower()
    is_simulation = bool(run.get("is_simulation", 0))
    cost_status = str(run.get("cost_status", "unknown")).lower()

    policy = (capture_policy or run.get("capture_policy") or "approved").lower()

    category = "measured"
    if source_kind == "fixture":
        provenance_reasons.append("fixture_replay")
        category = "fixture"
    elif source_kind == "unknown":
        provenance_reasons.append("legacy_unknown_provenance")
        category = "historical"
    elif source_kind == "imported":
        category = "imported"
        if evidence_status != "verified":
            provenance_reasons.append("unverified_import")
        else:
            provenance_reasons.append("imported_record")
    elif source_kind == "live":
        ev_ref = run.get("evidence_ref")
        ev_hash = run.get("evidence_hash")

        # Under approved capture policy (default), require validated supporting evidence record
        if policy in ("approved", "strict", "enforced"):
            if not ev_ref:
                provenance_reasons.append("evidence_missing")
                category = "historical"
            elif not ev_hash:
                provenance_reasons.append("evidence_hash_missing")
                category = "historical"
            else:
                p = Path(ev_ref)
                if not p.is_file() and not p.is_absolute():
                    candidate = DEFAULT_ROOT / p
                    if candidate.is_file():
                        p = candidate
                if p.is_file():
                    val = validate_evidence_file(p, ev_hash)
                    if not val["is_valid"]:
                        category = "historical"
                        provenance_reasons.append(val["exclusion_reason"])
                else:
                    provenance_reasons.append("evidence_file_missing")
                    category = "historical"
        else:
            # Permissive / legacy testing policy
            if evidence_status != "verified":
                category = "historical"
                if evidence_status == "invalid":
                    provenance_reasons.append("evidence_hash_mismatch")
                elif evidence_status == "missing":
                    provenance_reasons.append("evidence_missing")
                else:
                    provenance_reasons.append("unverified_evidence")
            elif ev_ref and ev_hash:
                p = Path(ev_ref)
                if not p.is_file() and not p.is_absolute():
                    candidate = DEFAULT_ROOT / p
                    if candidate.is_file():
                        p = candidate
                if p.is_file():
                    val = validate_evidence_file(p, ev_hash)
                    if not val["is_valid"]:
                        category = "historical"
                        provenance_reasons.append(val["exclusion_reason"])
    else:
        category = "historical"
        provenance_reasons.append(f"unrecognized_source_{source_kind}")

    if is_simulation:
        provenance_reasons.append("simulation")
        if category == "measured":
            category = "simulation"

    provenance_valid = (len(provenance_reasons) == 0 and category == "measured")

    # Cost completeness evaluation
    input_tokens = run.get("input_tokens")
    output_tokens = run.get("output_tokens")
    acus_consumed = run.get("acus_consumed")
    cost_source = classify_cost_source(run)
    is_acu_derived = (
        acus_consumed is not None
        and cost_source == COST_SOURCE_ESTIMATED_ACU_DERIVED
        and cost_status not in ("unavailable", "incomplete", "unknown")
    )
    is_cost_complete = True

    if not is_acu_derived and (input_tokens is None or output_tokens is None):
        cost_reasons.append("missing_usage_telemetry")
        is_cost_complete = False

    if cost_status in ("unavailable", "incomplete", "unknown"):
        cost_reasons.append(f"cost_{cost_status}")
        is_cost_complete = False

    # Execution status evaluation
    exec_status = str(run.get("execution_status", "completed") or "completed").lower()
    if exec_status not in ("completed", ""):
        execution_reasons.append(f"execution_{exec_status}")

    # Correctness evaluation (decoupled from cost and provenance)
    verif_status = str(run.get("verification_status", "not_run") or "not_run").lower()
    is_correct: Optional[bool] = None
    if verif_status == "passed":
        is_correct = True
    elif verif_status in ("failed", "evaluator_error"):
        is_correct = False
        correctness_reasons.append(f"verification_{verif_status}")

    # Parse stored exclusion reasons
    stored_reasons_parsed = []
    stored_reasons = run.get("exclusion_reasons")
    if stored_reasons:
        if isinstance(stored_reasons, str):
            try:
                parsed_r = json.loads(stored_reasons)
                if isinstance(parsed_r, list):
                    stored_reasons_parsed.extend(parsed_r)
            except Exception:
                pass
        elif isinstance(stored_reasons, list):
            stored_reasons_parsed.extend(stored_reasons)

    # Measurement exclusion reasons: provenance, cost, and execution issues (NOT correctness failures)
    measurement_exclusion_reasons: List[str] = []
    for r_item in provenance_reasons + cost_reasons + execution_reasons + stored_reasons_parsed:
        if r_item not in measurement_exclusion_reasons:
            measurement_exclusion_reasons.append(r_item)

    all_reasons: List[str] = []
    for r_item in measurement_exclusion_reasons + correctness_reasons:
        if r_item not in all_reasons:
            all_reasons.append(r_item)

    if (not provenance_valid or not is_cost_complete) and category == "measured":
        category = "historical"

    is_measurement_eligible = bool(category == "measured" and exec_status in ("completed", "") and is_cost_complete)
    # Comparison eligibility requires both measurement eligibility AND task correctness
    is_comparison_eligible = bool(is_measurement_eligible and is_correct is True)
    # is_eligible reflects measurement eligibility, so test failures remain measurable attempts
    is_eligible = is_measurement_eligible

    return {
        "is_eligible": is_eligible,
        "is_measurement_eligible": is_measurement_eligible,
        "is_comparison_eligible": is_comparison_eligible,
        "provenance_valid": provenance_valid,
        "category": category,
        "exclusion_reasons": all_reasons,
        "measurement_exclusion_reasons": measurement_exclusion_reasons,
        "is_cost_complete": is_cost_complete,
        "correctness_status": verif_status,
        "verification_status": verif_status,
        "is_correct": is_correct,
        "execution_status": exec_status,
        "provenance_reasons": provenance_reasons,
        "cost_reasons": cost_reasons,
        "execution_reasons": execution_reasons,
        "correctness_reasons": correctness_reasons,
    }


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Connect to SQLite database and ensure schema exists."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        if str(path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.Error:
        pass
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create schema tables if they do not already exist without altering existing tables."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runs'")
    runs_table_exists = bool(cursor.fetchone())

    if not runs_table_exists:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    arm TEXT NOT NULL,
                    model TEXT NOT NULL,
                    run_index INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    thinking_tokens INTEGER,
                    cache_read_tokens INTEGER,
                    total_tokens INTEGER,
                    num_turns INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    source_kind TEXT NOT NULL DEFAULT 'unknown',
                    evidence_status TEXT NOT NULL DEFAULT 'unverified',
                    exclusion_reasons TEXT,
                    evidence_ref TEXT,
                    evidence_hash TEXT,
                    import_id TEXT,
                    cost_status TEXT NOT NULL DEFAULT 'unknown',
                    cost_usd REAL,
                    cost_source TEXT,
                    acus_consumed REAL,
                    acu_usd_rate REAL,
                    estimated_cost_usd REAL,
                    is_simulation INTEGER NOT NULL DEFAULT 0,
                    notes TEXT,
                    execution_status TEXT NOT NULL DEFAULT 'completed',
                    verification_status TEXT NOT NULL DEFAULT 'not_run',
                    manifest_id TEXT,
                    evaluator_hash TEXT,
                    tool_calls_count INTEGER,
                    tool_errors_count INTEGER,
                    max_consecutive_tool_streak INTEGER,
                    loop_detected INTEGER
                );

                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    seq INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    tool_name TEXT,
                    target_path TEXT,
                    status TEXT NOT NULL,
                    diff_hash TEXT,
                    rollback_ref TEXT,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    prompt_path TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pricing (
                    model TEXT PRIMARY KEY,
                    input_usd_per_mtok REAL NOT NULL,
                    cache_read_usd_per_mtok REAL NOT NULL,
                    output_usd_per_mtok REAL NOT NULL,
                    source_url TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    pricing_mode TEXT,
                    provider_note TEXT,
                    cache_accounting TEXT DEFAULT 'separate',
                    thinking_usd_per_mtok REAL,
                    thinking_billed_as TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_runs_task_arm ON runs(task_id, arm);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_import_id ON runs(import_id) WHERE import_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id, seq);
            """)
    else:
        # Check if table already has provenance columns; if so, ensure Phase 2+ runner columns exist
        cursor.execute("PRAGMA table_info(runs)")
        cols = {row[1] for row in cursor.fetchall()}
        if "source_kind" in cols:
            with conn:
                if "execution_status" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN execution_status TEXT NOT NULL DEFAULT 'completed'")
                if "verification_status" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'not_run'")
                if "manifest_id" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN manifest_id TEXT")
                if "evaluator_hash" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN evaluator_hash TEXT")
                if "tool_calls_count" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN tool_calls_count INTEGER")
                if "tool_errors_count" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN tool_errors_count INTEGER")
                if "max_consecutive_tool_streak" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN max_consecutive_tool_streak INTEGER")
                if "loop_detected" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN loop_detected INTEGER")
                if "cost_source" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN cost_source TEXT")
                if "acus_consumed" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN acus_consumed REAL")
                if "acu_usd_rate" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN acu_usd_rate REAL")
                if "estimated_cost_usd" not in cols:
                    conn.execute("ALTER TABLE runs ADD COLUMN estimated_cost_usd REAL")

        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    seq INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    tool_name TEXT,
                    target_path TEXT,
                    status TEXT NOT NULL,
                    diff_hash TEXT,
                    rollback_ref TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id, seq)")

        # Ensure pricing columns exist on existing pricing tables
        cursor.execute("PRAGMA table_info(pricing)")
        p_cols = {row[1] for row in cursor.fetchall()}
        if p_cols:
            with conn:
                if "pricing_mode" not in p_cols:
                    conn.execute("ALTER TABLE pricing ADD COLUMN pricing_mode TEXT")
                if "provider_note" not in p_cols:
                    conn.execute("ALTER TABLE pricing ADD COLUMN provider_note TEXT")
                if "cache_accounting" not in p_cols:
                    conn.execute("ALTER TABLE pricing ADD COLUMN cache_accounting TEXT DEFAULT 'separate'")
                if "thinking_usd_per_mtok" not in p_cols:
                    conn.execute("ALTER TABLE pricing ADD COLUMN thinking_usd_per_mtok REAL")
                if "thinking_billed_as" not in p_cols:
                    conn.execute("ALTER TABLE pricing ADD COLUMN thinking_billed_as TEXT")


def migrate_db(conn: sqlite3.Connection) -> bool:
    """
    Migrate a legacy database to the Phase 1 provenance schema transactionally.
    Safe to re-run (idempotent).
    Preserves all existing rows and values.
    Assigns legacy records:
      source_kind = 'unknown'
      evidence_status = 'unverified'
      exclusion_reasons = '["legacy_record_unknown_provenance"]'
      cost_status = 'unavailable'
      is_simulation = 0
    Returns True if migration was applied, False if already migrated.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(runs)")
    cols = {row[1]: row for row in cursor.fetchall()}

    if not cols:
        init_db(conn)
        return True

    # MIG-02: Idempotent check & Phase 2+ column / run_events upgrade
    if "source_kind" in cols:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='run_events'")
        run_events_exists = bool(cursor.fetchone())
        applied_upgrade = False
        with conn:
            if "execution_status" not in cols:
                conn.execute("ALTER TABLE runs ADD COLUMN execution_status TEXT NOT NULL DEFAULT 'completed'")
                applied_upgrade = True
            if "verification_status" not in cols:
                conn.execute("ALTER TABLE runs ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'not_run'")
                applied_upgrade = True
            if "manifest_id" not in cols:
                conn.execute("ALTER TABLE runs ADD COLUMN manifest_id TEXT")
                applied_upgrade = True
            if "evaluator_hash" not in cols:
                conn.execute("ALTER TABLE runs ADD COLUMN evaluator_hash TEXT")
                applied_upgrade = True
            if "tool_calls_count" not in cols:
                conn.execute("ALTER TABLE runs ADD COLUMN tool_calls_count INTEGER")
                applied_upgrade = True
            if "tool_errors_count" not in cols:
                conn.execute("ALTER TABLE runs ADD COLUMN tool_errors_count INTEGER")
                applied_upgrade = True
            if "max_consecutive_tool_streak" not in cols:
                conn.execute("ALTER TABLE runs ADD COLUMN max_consecutive_tool_streak INTEGER")
                applied_upgrade = True
            if "loop_detected" not in cols:
                conn.execute("ALTER TABLE runs ADD COLUMN loop_detected INTEGER")
                applied_upgrade = True
            if not run_events_exists:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS run_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id INTEGER NOT NULL,
                        seq INTEGER NOT NULL,
                        phase TEXT NOT NULL,
                        tool_name TEXT,
                        target_path TEXT,
                        status TEXT NOT NULL,
                        diff_hash TEXT,
                        rollback_ref TEXT,
                        timestamp TEXT NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id, seq)")
                applied_upgrade = True
        return applied_upgrade

    # MIG-03: Transactional migration with rollback safety
    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("""
            CREATE TABLE runs__migrating (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                arm TEXT NOT NULL,
                model TEXT NOT NULL,
                run_index INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                thinking_tokens INTEGER,
                cache_read_tokens INTEGER,
                total_tokens INTEGER,
                num_turns INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                source_kind TEXT NOT NULL DEFAULT 'unknown',
                evidence_status TEXT NOT NULL DEFAULT 'unverified',
                exclusion_reasons TEXT,
                evidence_ref TEXT,
                evidence_hash TEXT,
                import_id TEXT,
                cost_status TEXT NOT NULL DEFAULT 'unknown',
                cost_usd REAL,
                cost_source TEXT,
                acus_consumed REAL,
                acu_usd_rate REAL,
                estimated_cost_usd REAL,
                is_simulation INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                execution_status TEXT NOT NULL DEFAULT 'completed',
                verification_status TEXT NOT NULL DEFAULT 'not_run',
                manifest_id TEXT,
                evaluator_hash TEXT,
                tool_calls_count INTEGER,
                tool_errors_count INTEGER,
                max_consecutive_tool_streak INTEGER,
                loop_detected INTEGER
            )
        """)

        legacy_exclusion = json.dumps(["legacy_record_unknown_provenance"])
        conn.execute("""
            INSERT INTO runs__migrating (
                id, task_id, arm, model, run_index, timestamp,
                input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                total_tokens, num_turns, duration_seconds,
                source_kind, evidence_status, exclusion_reasons,
                cost_status, is_simulation
            )
            SELECT
                id, task_id, arm, model, run_index, timestamp,
                input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                total_tokens, num_turns, duration_seconds,
                'unknown', 'unverified', ?,
                'unavailable', 0
            FROM runs
        """, (legacy_exclusion,))

        # Verify row counts match before dropping
        cursor.execute("SELECT COUNT(*) FROM runs")
        orig_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM runs__migrating")
        new_count = cursor.fetchone()[0]
        if orig_count != new_count:
            raise RuntimeError(f"Row count mismatch during migration: {orig_count} vs {new_count}")

        conn.execute("DROP TABLE runs")
        conn.execute("ALTER TABLE runs__migrating RENAME TO runs")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_import_id ON runs(import_id) WHERE import_id IS NOT NULL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_task_arm ON runs(task_id, arm)")

        # Ensure pricing columns exist
        pricing_columns = {row[1] for row in conn.execute("PRAGMA table_info(pricing)").fetchall()}
        if "pricing_mode" not in pricing_columns:
            conn.execute("ALTER TABLE pricing ADD COLUMN pricing_mode TEXT")
        if "provider_note" not in pricing_columns:
            conn.execute("ALTER TABLE pricing ADD COLUMN provider_note TEXT")
        if "cache_accounting" not in pricing_columns:
            conn.execute("ALTER TABLE pricing ADD COLUMN cache_accounting TEXT DEFAULT 'separate'")
        if "thinking_usd_per_mtok" not in pricing_columns:
            conn.execute("ALTER TABLE pricing ADD COLUMN thinking_usd_per_mtok REAL")
        if "thinking_billed_as" not in pricing_columns:
            conn.execute("ALTER TABLE pricing ADD COLUMN thinking_billed_as TEXT")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                seq INTEGER NOT NULL,
                phase TEXT NOT NULL,
                tool_name TEXT,
                target_path TEXT,
                status TEXT NOT NULL,
                diff_hash TEXT,
                rollback_ref TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id, seq)")

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise


def seed_pricing(
    pricing_path: Optional[Path] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
    prune: bool = False,
) -> int:
    """Seed pricing table from config/PRICING.json. Never hardcodes rates in code."""
    path = Path(pricing_path) if pricing_path else DEFAULT_PRICING_PATH
    if not path.exists():
        raise FileNotFoundError(f"Pricing configuration file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    models = data.get("models", {})
    if not models:
        raise ValueError(f"No models declared in pricing config: {path}")

    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    count = 0
    with conn:
        if prune:
            placeholders = ",".join("?" for _ in models)
            conn.execute(
                f"DELETE FROM pricing WHERE model NOT IN ({placeholders})",
                tuple(models.keys()),
            )
        for model_id, rates in models.items():
            conn.execute(
                """
                INSERT INTO pricing (
                    model, input_usd_per_mtok, cache_read_usd_per_mtok,
                    output_usd_per_mtok, source_url, fetched_at, pricing_mode, provider_note,
                    cache_accounting, thinking_usd_per_mtok, thinking_billed_as
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model) DO UPDATE SET
                    input_usd_per_mtok = excluded.input_usd_per_mtok,
                    cache_read_usd_per_mtok = excluded.cache_read_usd_per_mtok,
                    output_usd_per_mtok = excluded.output_usd_per_mtok,
                    source_url = excluded.source_url,
                    fetched_at = excluded.fetched_at,
                    pricing_mode = excluded.pricing_mode,
                    provider_note = excluded.provider_note,
                    cache_accounting = excluded.cache_accounting,
                    thinking_usd_per_mtok = excluded.thinking_usd_per_mtok,
                    thinking_billed_as = excluded.thinking_billed_as
                """,
                (
                    model_id,
                    float(rates["input_usd_per_mtok"]),
                    float(rates["cache_read_usd_per_mtok"]),
                    float(rates["output_usd_per_mtok"]),
                    str(rates["source_url"]),
                    str(rates.get("fetched_at", datetime.now(timezone.utc).isoformat())),
                    rates.get("pricing_mode"),
                    rates.get("provider_note"),
                    rates.get("cache_accounting", "separate"),
                    float(rates["thinking_usd_per_mtok"]) if "thinking_usd_per_mtok" in rates else None,
                    rates.get("thinking_billed_as"),
                ),
            )
            count += 1

    if should_close:
        conn.close()

    return count


def _declared_pricing_models() -> Set[str]:
    """Model ids declared in config/PRICING.json."""
    with open(DEFAULT_PRICING_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    models = data.get("models") or {}
    return set(models) if isinstance(models, dict) else set()


def get_pricing(model: str, conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieve pricing rates for a given model from DB, auto-seeding if needed."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pricing WHERE model = ?", (model,))
    row = cursor.fetchone()

    if not row:
        # Seed only when a config-declared model that could satisfy this
        # lookup (the id itself or its effort-stripped base) is missing from
        # the table: a fresh table stays read-only and a table seeded from a
        # custom rate card is never overwritten by the bundled card.
        try:
            base = base_model_id(model)
            present = {r["model"] for r in cursor.execute("SELECT model FROM pricing")}
            missing = _declared_pricing_models() - present
            if model in missing or base in missing:
                seed_pricing(conn=conn)
                cursor.execute("SELECT * FROM pricing WHERE model = ?", (model,))
                row = cursor.fetchone()
        except Exception:
            pass

    if not row:
        # Effort-suffixed ids resolve to the base model's rate card.
        base = base_model_id(model)
        if base != model:
            cursor.execute("SELECT * FROM pricing WHERE model = ?", (base,))
            row = cursor.fetchone()

    if not row:
        if should_close:
            conn.close()
        raise ValueError(
            f"Pricing not found for model '{model}'. "
            f"Add rates to config/PRICING.json and re-run seed."
        )

    result = dict(row)
    if should_close:
        conn.close()
    return result


def calculate_cost_detailed(
    input_tokens: Optional[int],
    cache_read_tokens: Optional[int],
    output_tokens: Optional[int],
    model: str,
    thinking_tokens: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
    is_simulation: bool = False,
    is_partial: bool = False,
    acus_consumed: Optional[float] = None,
    acu_usd_rate: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute cache-aware USD cost for token profile with provider semantics,
    or derive estimated_cost_usd from Devin ACUs when direct token pricing
    is unavailable. Enforces ACC-01 to ACC-07 and TEL-02.
    """
    validated_acus = validate_acus_consumed(acus_consumed)

    def _acu_or_unavailable(reason: str, rates_obj: Any = None) -> Dict[str, Any]:
        if validated_acus is not None:
            acu_res = calculate_acu_cost(
                validated_acus,
                acu_usd_rate=acu_usd_rate,
                is_simulation=is_simulation,
                is_partial=is_partial,
            )
            acu_res["rates"] = rates_obj
            return acu_res
        return {
            "cost_usd": None,
            "estimated_cost_usd": None,
            "acus_consumed": None,
            "acu_usd_rate": None,
            "cost_status": "unavailable",
            "cost_source": COST_SOURCE_UNAVAILABLE,
            "reasons": [reason],
            "rates": rates_obj,
        }

    if input_tokens is None or output_tokens is None:
        return _acu_or_unavailable("missing_usage_telemetry")

    try:
        rates = get_pricing(model, conn=conn, db_path=db_path)
    except ValueError:
        return _acu_or_unavailable("model_rate_absent")

    thinking = thinking_tokens or 0
    thinking_cost = 0.0
    if thinking > 0:
        thinking_billed_as = rates.get("thinking_billed_as")
        thinking_rate = rates.get("thinking_usd_per_mtok")
        if thinking_billed_as == "output":
            thinking_cost = thinking * rates["output_usd_per_mtok"]
        elif thinking_rate is not None:
            thinking_cost = thinking * float(thinking_rate)
        else:
            return _acu_or_unavailable("thinking_token_pricing_unspecified", rates)

    cache_read = cache_read_tokens or 0
    inp = input_tokens or 0
    cache_mode = rates.get("cache_accounting", "separate")

    if cache_mode == "subset":
        uncached_input = max(0, inp - cache_read)
        input_cost = uncached_input * rates["input_usd_per_mtok"]
        cache_cost = cache_read * rates["cache_read_usd_per_mtok"]
    elif cache_mode == "separate":
        input_cost = inp * rates["input_usd_per_mtok"]
        cache_cost = cache_read * rates["cache_read_usd_per_mtok"]
    else:
        return _acu_or_unavailable(f"unknown_cache_accounting_{cache_mode}", rates)

    out = output_tokens or 0
    output_cost = out * rates["output_usd_per_mtok"]

    total_micro_usd = input_cost + cache_cost + output_cost + thinking_cost
    cost_usd = round(total_micro_usd / 1_000_000.0, 6)

    reasons: List[str] = []
    if is_simulation:
        cost_status = "simulation"
        reasons.append("simulation")
    elif is_partial:
        cost_status = "incomplete"
        reasons.append("partial_telemetry")
    else:
        cost_status = "usage_estimate"

    return {
        "cost_usd": cost_usd,
        "estimated_cost_usd": None,
        "acus_consumed": validated_acus,
        "acu_usd_rate": None,
        "cost_status": cost_status,
        "cost_source": COST_SOURCE_BILLED_DIRECT,
        "reasons": reasons,
        "rates": rates,
    }


def calculate_cost(
    input_tokens: Optional[int],
    cache_read_tokens: Optional[int],
    output_tokens: Optional[int],
    model: str,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
    thinking_tokens: Optional[int] = None,
    is_simulation: bool = False,
    is_partial: bool = False,
) -> Optional[float]:
    res = calculate_cost_detailed(
        input_tokens=input_tokens,
        cache_read_tokens=cache_read_tokens,
        output_tokens=output_tokens,
        model=model,
        thinking_tokens=thinking_tokens,
        conn=conn,
        db_path=db_path,
        is_simulation=is_simulation,
        is_partial=is_partial,
    )
    return res["cost_usd"]


def record_task(
    task_id: str,
    prompt_path: Optional[str] = None,
    notes: Optional[str] = None,
    created_at: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Record or update a task entry."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO tasks (id, prompt_path, notes, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                prompt_path = COALESCE(excluded.prompt_path, tasks.prompt_path),
                notes = COALESCE(excluded.notes, tasks.notes)
            """,
            (task_id, prompt_path, notes, timestamp),
        )

    if should_close:
        conn.close()


def clear_task_runs(task_id: str, conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None, arm: Optional[str] = None) -> int:
    """Clear previous experimental runs for a task to allow clean idempotent re-runs."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='run_events'")
        has_run_events = bool(cursor.fetchone())
        if arm:
            if has_run_events:
                conn.execute(
                    "DELETE FROM run_events WHERE run_id IN (SELECT id FROM runs WHERE task_id = ? AND arm = ?)",
                    (task_id, arm),
                )
            cursor = conn.execute("DELETE FROM runs WHERE task_id = ? AND arm = ?", (task_id, arm))
        else:
            if has_run_events:
                conn.execute(
                    "DELETE FROM run_events WHERE run_id IN (SELECT id FROM runs WHERE task_id = ?)",
                    (task_id,),
                )
            cursor = conn.execute("DELETE FROM runs WHERE task_id = ?", (task_id,))
        count = cursor.rowcount

    if should_close:
        conn.close()

    return count


def record_run(
    task_id: str,
    arm: str,
    model: str,
    run_index: int,
    timestamp: str,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    thinking_tokens: Optional[int] = None,
    cache_read_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    num_turns: int = 1,
    duration_seconds: float = 0.0,
    source_kind: str = "unknown",
    evidence_status: str = "unverified",
    exclusion_reasons: Optional[List[str]] = None,
    evidence_ref: Optional[str] = None,
    evidence_hash: Optional[str] = None,
    import_id: Optional[str] = None,
    cost_status: Optional[str] = None,
    cost_usd: Optional[float] = None,
    cost_source: Optional[str] = None,
    acus_consumed: Optional[float] = None,
    acu_usd_rate: Optional[float] = None,
    estimated_cost_usd: Optional[float] = None,
    is_simulation: bool = False,
    notes: Optional[str] = None,
    execution_status: str = "completed",
    verification_status: str = "not_run",
    manifest_id: Optional[str] = None,
    evaluator_hash: Optional[str] = None,
    tool_calls_count: Optional[int] = None,
    tool_errors_count: Optional[int] = None,
    max_consecutive_tool_streak: Optional[int] = None,
    loop_detected: Optional[Any] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Record a run into the SQLite ledger with full provenance and accounting metadata."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    record_task(task_id, conn=conn)

    # Reconstruct total_tokens strictly under an explicit adapter schema (Finding 4)
    if total_tokens is None and input_tokens is not None:
        rates = None
        try:
            rates = get_pricing(model, conn=conn, db_path=db_path)
        except Exception:
            pass
        cache_mode = rates.get("cache_accounting") if rates else None
        total_tokens = reconstruct_total_tokens(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
            cache_read_tokens=cache_read_tokens,
            adapter_name=cache_mode,
        )

    # Ensure non-null execution and verification statuses
    if not execution_status:
        execution_status = "completed"
    if not verification_status:
        verification_status = "not_run"

    # Lifecycle status implications
    if execution_status == "timed_out":
        if exclusion_reasons is None:
            exclusion_reasons = []
        if "timeout" not in exclusion_reasons:
            exclusion_reasons.append("timeout")
    elif execution_status == "interrupted":
        if exclusion_reasons is None:
            exclusion_reasons = []
        if "interrupted_attempt" not in exclusion_reasons:
            exclusion_reasons.append("interrupted_attempt")
    elif execution_status == "failed":
        if exclusion_reasons is None:
            exclusion_reasons = []
        if "execution_failed" not in exclusion_reasons:
            exclusion_reasons.append("execution_failed")

    if verification_status == "evaluator_error":
        if exclusion_reasons is None:
            exclusion_reasons = []
        if "evaluator_error" not in exclusion_reasons:
            exclusion_reasons.append("evaluator_error")

    # Calculate cost if not provided
    validated_acus = validate_acus_consumed(acus_consumed)
    is_part = (cost_status == "incomplete") or (exclusion_reasons is not None and "partial_telemetry" in exclusion_reasons)
    if cost_usd is None and (input_tokens is not None or validated_acus is not None):
        cost_calc = calculate_cost_detailed(
            input_tokens=input_tokens,
            cache_read_tokens=cache_read_tokens,
            output_tokens=output_tokens,
            model=model,
            thinking_tokens=thinking_tokens,
            conn=conn,
            db_path=db_path,
            is_simulation=is_simulation,
            is_partial=is_part,
            acus_consumed=validated_acus,
            acu_usd_rate=acu_usd_rate,
        )
        cost_usd = cost_calc["cost_usd"]
        if not cost_status:
            cost_status = cost_calc["cost_status"]
        if not cost_source:
            cost_source = cost_calc.get("cost_source")
        if acu_usd_rate is None and cost_calc.get("acu_usd_rate") is not None:
            acu_usd_rate = cost_calc["acu_usd_rate"]
        if estimated_cost_usd is None and cost_calc.get("estimated_cost_usd") is not None:
            estimated_cost_usd = cost_calc["estimated_cost_usd"]
        if cost_calc["reasons"]:
            if exclusion_reasons is None:
                exclusion_reasons = []
            for r in cost_calc["reasons"]:
                if r not in exclusion_reasons:
                    exclusion_reasons.append(r)
    elif cost_status is None:
        if validated_acus is not None and cost_usd is not None:
            cost_status = COST_SOURCE_ESTIMATED_ACU_DERIVED
        else:
            cost_status = "unavailable" if input_tokens is None else "usage_estimate"

    if not cost_source:
        cost_source = classify_cost_source(
            {
                "cost_status": cost_status,
                "cost_usd": cost_usd,
                "acus_consumed": validated_acus,
                "input_tokens": input_tokens,
            }
        )
    if cost_source == COST_SOURCE_ESTIMATED_ACU_DERIVED:
        if estimated_cost_usd is None and cost_usd is not None:
            estimated_cost_usd = cost_usd
        if acu_usd_rate is None and validated_acus is not None:
            acu_usd_rate = get_devin_acu_usd_rate()

    if input_tokens is None and validated_acus is None:
        if exclusion_reasons is None:
            exclusion_reasons = []
        if "missing_usage_telemetry" not in exclusion_reasons:
            exclusion_reasons.append("missing_usage_telemetry")

    reasons_json = json.dumps(exclusion_reasons) if exclusion_reasons else None

    # Determine if table has phase 1 or phase 2 columns
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(runs)")
    cols = {row[1] for row in cursor.fetchall()}

    loop_val = (1 if loop_detected else 0) if loop_detected is not None else None

    with conn:
        if "source_kind" in cols:
            if "execution_status" in cols and "tool_calls_count" in cols and "acus_consumed" in cols:
                cursor = conn.execute(
                    """
                    INSERT INTO runs (
                        task_id, arm, model, run_index, timestamp,
                        input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                        total_tokens, num_turns, duration_seconds,
                        source_kind, evidence_status, exclusion_reasons,
                        evidence_ref, evidence_hash, import_id,
                        cost_status, cost_usd, cost_source, acus_consumed, acu_usd_rate, estimated_cost_usd,
                        is_simulation, notes,
                        execution_status, verification_status, manifest_id, evaluator_hash,
                        tool_calls_count, tool_errors_count, max_consecutive_tool_streak, loop_detected
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        arm,
                        model,
                        run_index,
                        timestamp,
                        input_tokens,
                        output_tokens,
                        thinking_tokens,
                        cache_read_tokens,
                        total_tokens,
                        int(num_turns),
                        float(duration_seconds),
                        source_kind,
                        evidence_status,
                        reasons_json,
                        evidence_ref,
                        evidence_hash,
                        import_id,
                        cost_status,
                        cost_usd,
                        cost_source,
                        validated_acus,
                        acu_usd_rate,
                        estimated_cost_usd,
                        1 if is_simulation else 0,
                        notes,
                        execution_status,
                        verification_status,
                        manifest_id,
                        evaluator_hash,
                        tool_calls_count,
                        tool_errors_count,
                        max_consecutive_tool_streak,
                        loop_val,
                    ),
                )
            elif "execution_status" in cols and "tool_calls_count" in cols:
                cursor = conn.execute(
                    """
                    INSERT INTO runs (
                        task_id, arm, model, run_index, timestamp,
                        input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                        total_tokens, num_turns, duration_seconds,
                        source_kind, evidence_status, exclusion_reasons,
                        evidence_ref, evidence_hash, import_id,
                        cost_status, cost_usd, is_simulation, notes,
                        execution_status, verification_status, manifest_id, evaluator_hash,
                        tool_calls_count, tool_errors_count, max_consecutive_tool_streak, loop_detected
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        arm,
                        model,
                        run_index,
                        timestamp,
                        input_tokens,
                        output_tokens,
                        thinking_tokens,
                        cache_read_tokens,
                        total_tokens,
                        int(num_turns),
                        float(duration_seconds),
                        source_kind,
                        evidence_status,
                        reasons_json,
                        evidence_ref,
                        evidence_hash,
                        import_id,
                        cost_status,
                        cost_usd,
                        1 if is_simulation else 0,
                        notes,
                        execution_status,
                        verification_status,
                        manifest_id,
                        evaluator_hash,
                        tool_calls_count,
                        tool_errors_count,
                        max_consecutive_tool_streak,
                        loop_val,
                    ),
                )
            elif "execution_status" in cols:
                cursor = conn.execute(
                    """
                    INSERT INTO runs (
                        task_id, arm, model, run_index, timestamp,
                        input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                        total_tokens, num_turns, duration_seconds,
                        source_kind, evidence_status, exclusion_reasons,
                        evidence_ref, evidence_hash, import_id,
                        cost_status, cost_usd, is_simulation, notes,
                        execution_status, verification_status, manifest_id, evaluator_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        arm,
                        model,
                        run_index,
                        timestamp,
                        input_tokens,
                        output_tokens,
                        thinking_tokens,
                        cache_read_tokens,
                        total_tokens,
                        int(num_turns),
                        float(duration_seconds),
                        source_kind,
                        evidence_status,
                        reasons_json,
                        evidence_ref,
                        evidence_hash,
                        import_id,
                        cost_status,
                        cost_usd,
                        1 if is_simulation else 0,
                        notes,
                        execution_status,
                        verification_status,
                        manifest_id,
                        evaluator_hash,
                    ),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO runs (
                        task_id, arm, model, run_index, timestamp,
                        input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                        total_tokens, num_turns, duration_seconds,
                        source_kind, evidence_status, exclusion_reasons,
                        evidence_ref, evidence_hash, import_id,
                        cost_status, cost_usd, is_simulation, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        arm,
                        model,
                        run_index,
                        timestamp,
                        input_tokens,
                        output_tokens,
                        thinking_tokens,
                        cache_read_tokens,
                        total_tokens,
                        int(num_turns),
                        float(duration_seconds),
                        source_kind,
                        evidence_status,
                        reasons_json,
                        evidence_ref,
                        evidence_hash,
                        import_id,
                        cost_status,
                        cost_usd,
                        1 if is_simulation else 0,
                        notes,
                    ),
                )
        else:
            # Legacy table fallback: insert into legacy schema
            cursor = conn.execute(
                """
                INSERT INTO runs (
                    task_id, arm, model, run_index, timestamp,
                    input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                    total_tokens, num_turns, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    arm,
                    model,
                    run_index,
                    timestamp,
                    int(input_tokens or 0),
                    int(output_tokens or 0),
                    int(thinking_tokens or 0),
                    int(cache_read_tokens or 0),
                    int(total_tokens or 0),
                    int(num_turns),
                    float(duration_seconds),
                ),
            )
        run_id = cursor.lastrowid

    if should_close:
        conn.close()

    return run_id


def record_run_event(
    run_id: int,
    seq: int,
    phase: str,
    status: str,
    tool_name: Optional[str] = None,
    target_path: Optional[str] = None,
    diff_hash: Optional[str] = None,
    rollback_ref: Optional[str] = None,
    timestamp: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Persist a single provenance / state-transition event for a run in run_events."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    ts = timestamp or datetime.now(timezone.utc).isoformat()
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO run_events (
                run_id, seq, phase, tool_name, target_path,
                status, diff_hash, rollback_ref, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(run_id),
                int(seq),
                str(phase),
                tool_name,
                target_path,
                str(status),
                diff_hash,
                rollback_ref,
                ts,
            ),
        )
        event_id = int(cursor.lastrowid)

    if should_close:
        conn.close()

    return event_id


def get_run_events(
    run_id: int,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Retrieve ordered state-transition and tool events for a given run_id."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='run_events'")
        if not cursor.fetchone():
            return []
        cursor.execute(
            "SELECT * FROM run_events WHERE run_id = ? ORDER BY seq ASC, id ASC",
            (int(run_id),),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def backfill_tool_metrics_from_evidence(
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> int:
    """
    Idempotently populate tool_calls_count, tool_errors_count,
    max_consecutive_tool_streak, and loop_detected for runs rows whose
    evidence_ref exists on disk and tool_calls_count IS NULL.
    """
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    updated = 0
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(runs)")
        cols = {row[1] for row in cursor.fetchall()}
        if "tool_calls_count" not in cols:
            if "source_kind" in cols:
                init_db(conn)
            else:
                return 0

        cursor.execute(
            """
            SELECT id, evidence_ref FROM runs
            WHERE tool_calls_count IS NULL
              AND evidence_ref IS NOT NULL
              AND evidence_ref != ''
            """
        )
        candidates = cursor.fetchall()

        with conn:
            for row in candidates:
                ev_ref = row["evidence_ref"]
                p = Path(ev_ref)
                if not p.is_file() and not p.is_absolute():
                    candidate = DEFAULT_ROOT / p
                    if candidate.is_file():
                        p = candidate
                if not p.is_file():
                    continue
                try:
                    metrics = extract_ndjson_tool_metrics(p)
                except Exception:
                    continue
                conn.execute(
                    """
                    UPDATE runs
                    SET tool_calls_count = ?,
                        tool_errors_count = ?,
                        max_consecutive_tool_streak = ?,
                        loop_detected = ?
                    WHERE id = ? AND tool_calls_count IS NULL
                    """,
                    (
                        metrics["tool_calls_count"],
                        metrics["tool_errors_count"],
                        metrics["max_consecutive_tool_streak"],
                        1 if metrics["loop_detected"] else 0,
                        row["id"],
                    ),
                )
                updated += 1
        return updated
    finally:
        if should_close:
            conn.close()


_ORPHAN_EVIDENCE_RE = re.compile(
    r"^live_(?P<task_id>[A-Za-z0-9-]+?)(?:_(?P<model_slug>[a-z0-9][a-z0-9._-]+))?_(?P<arm>baseline|icm|icm_lite|icm-subagents|delegation)_run(?P<run_idx>\d+)_(?P<epoch>\d+)\.ndjson$"
)


def import_orphan_evidence_runs(
    evidence_dir: Optional[Path] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> int:
    """
    Idempotently import unreferenced live_*.ndjson evidence files into runs
    as source_kind='imported', evidence_status='verified', excluded from
    measured cost/savings totals. Returns count of newly imported rows.
    """
    ev_dir = Path(evidence_dir) if evidence_dir is not None else DEFAULT_ROOT / "experiments" / "evidence"
    if not ev_dir.is_dir():
        return 0

    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    imported = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT evidence_ref, import_id FROM runs")
        existing_basenames = set()
        existing_imports = set()
        for row in cursor.fetchall():
            if row["evidence_ref"]:
                existing_basenames.add(Path(str(row["evidence_ref"]).replace("\\", "/")).name)
            if row["import_id"]:
                existing_imports.add(str(row["import_id"]))

        for p in sorted(ev_dir.glob("live_*.ndjson")):
            import_id = f"orphan:{p.name}"
            if p.name in existing_basenames or import_id in existing_imports:
                continue

            m = _ORPHAN_EVIDENCE_RE.match(p.name)
            if not m:
                continue
            task_id = m.group("task_id")
            arm = m.group("arm")
            epoch = int(m.group("epoch"))

            raw_bytes = p.read_bytes()
            ev_hash = hashlib.sha256(raw_bytes).hexdigest()
            lines = raw_bytes.decode("utf-8", errors="replace").splitlines()
            if not lines:
                continue

            parsed = validate_and_parse_telemetry(lines)
            tool_m = parsed.get("tool_metrics") or extract_ndjson_tool_metrics(lines)
            u = parsed["usage"]

            model = "gemini-3.8-flash-low"
            resp_text = ""
            for raw_line in lines:
                s = raw_line.strip()
                if not s:
                    continue
                try:
                    ev_obj = json.loads(s)
                except json.JSONDecodeError:
                    continue
                if ev_obj.get("event") == "init" and isinstance(ev_obj.get("init"), dict):
                    if ev_obj["init"].get("model"):
                        model = str(ev_obj["init"]["model"])
                elif ev_obj.get("event") == "result":
                    res = ev_obj.get("result")
                    if isinstance(res, str):
                        try:
                            res = ast.literal_eval(res)
                        except Exception:
                            res = {}
                    if isinstance(res, dict):
                        resp_text = str(res.get("response") or "")

            if arm == "baseline" and ("ICM" in resp_text or "TSK-" in resp_text):
                reasons = ["superseded_or_contaminated_baseline"]
            else:
                reasons = ["superseded_prior_attempt"]

            cursor.execute(
                "SELECT COALESCE(MAX(run_index), 0) FROM runs WHERE task_id = ? AND arm = ?",
                (task_id, arm),
            )
            next_run_idx = int(cursor.fetchone()[0]) + 1

            try:
                rel_ref = p.resolve().relative_to(DEFAULT_ROOT.resolve()).as_posix()
            except ValueError:
                rel_ref = str(p)

            ts = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
            record_run(
                task_id=task_id,
                arm=arm,
                model=model,
                run_index=next_run_idx,
                timestamp=ts,
                input_tokens=u["input_tokens"],
                output_tokens=u["output_tokens"],
                thinking_tokens=u.get("thinking_tokens"),
                cache_read_tokens=u.get("cache_read_tokens"),
                total_tokens=u["total_tokens"],
                num_turns=parsed["num_turns"],
                duration_seconds=parsed["duration_seconds"],
                source_kind="imported",
                evidence_status="verified",
                exclusion_reasons=reasons,
                evidence_ref=rel_ref,
                evidence_hash=ev_hash,
                import_id=import_id,
                notes="Archived prior live NDJSON attempt imported for provenance completeness; excluded from measured cost aggregates.",
                execution_status="completed",
                verification_status="not_run",
                tool_calls_count=tool_m["tool_calls_count"],
                tool_errors_count=tool_m["tool_errors_count"],
                max_consecutive_tool_streak=tool_m["max_consecutive_tool_streak"],
                loop_detected=tool_m["loop_detected"],
                conn=conn,
            )
            existing_basenames.add(p.name)
            existing_imports.add(import_id)
            imported += 1

        return imported
    finally:
        if should_close:
            conn.close()


def import_run(
    conn: sqlite3.Connection,
    run_dict: Dict[str, Any],
    db_path: Optional[Path] = None,
) -> int:
    """
    Import a run record with provenance and duplicate conflict handling.
    - IMP-01: Idempotent duplicate ingestion returns existing run ID without duplicating.
    - IMP-02: Same import_id with conflicting content raises DuplicateConflictError.
    - PROV-03: Telemetry without verified source evidence classified as unverified import.
    """
    task_id = run_dict["task_id"]
    arm = run_dict["arm"]
    model = run_dict["model"]
    run_index = int(run_dict["run_index"])
    timestamp = run_dict.get("timestamp") or datetime.now(timezone.utc).isoformat()

    import_id = run_dict.get("import_id")
    if not import_id:
        ts = run_dict.get("timestamp")
        if ts:
            import_id = f"{task_id}:{arm}:{run_index}:{ts}"
        else:
            import_id = f"{task_id}:{arm}:{run_index}"

    # Check for existing run by import_id
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE import_id = ?", (import_id,))
    existing = cursor.fetchone()

    if existing:
        ex = dict(existing)
        diffs = []
        for fld in ("task_id", "arm", "model"):
            if run_dict.get(fld) != ex.get(fld):
                diffs.append(f"{fld} (existing: {ex.get(fld)} vs new: {run_dict.get(fld)})")
        if int(run_dict.get("run_index", 0)) != int(ex.get("run_index", 0)):
            diffs.append(f"run_index (existing: {ex.get('run_index')} vs new: {run_dict.get('run_index')})")
        for fld in ("input_tokens", "output_tokens"):
            if run_dict.get(fld) != ex.get(fld):
                diffs.append(f"{fld} (existing: {ex.get(fld)} vs new: {run_dict.get(fld)})")
        for fld in ("cache_read_tokens", "thinking_tokens"):
            v_new = run_dict.get(fld)
            v_ex = ex.get(fld)
            if (v_new or 0) != (v_ex or 0):
                diffs.append(f"{fld} (existing: {v_ex} vs new: {v_new})")
        new_acus = validate_acus_consumed(run_dict.get("acus_consumed"))
        ex_acus = validate_acus_consumed(ex.get("acus_consumed"))
        if (new_acus is None) != (ex_acus is None) or (
            new_acus is not None and ex_acus is not None and abs(new_acus - ex_acus) > 1e-6
        ):
            diffs.append(f"acus_consumed (existing: {ex_acus} vs new: {new_acus})")
        if "num_turns" in run_dict and int(run_dict["num_turns"]) != int(ex.get("num_turns", 1)):
            diffs.append(f"num_turns (existing: {ex.get('num_turns')} vs new: {run_dict['num_turns']})")
        if "duration_seconds" in run_dict and abs(float(run_dict["duration_seconds"]) - float(ex.get("duration_seconds", 0.0))) > 1e-4:
            diffs.append(f"duration_seconds (existing: {ex.get('duration_seconds')} vs new: {run_dict['duration_seconds']})")
        if diffs:
            raise DuplicateConflictError(
                f"Conflicting import for import_id '{import_id}': {', '.join(diffs)}"
            )
        # Idempotent match (IMP-01)
        return ex["id"]

    source_kind = run_dict.get("source_kind", "imported")
    evidence_ref = run_dict.get("evidence_ref")
    evidence_hash = run_dict.get("evidence_hash")
    exclusion_reasons = list(run_dict.get("exclusion_reasons") or [])

    # An imported record cannot claim live origin; imports are classified as imported (or fixture/unknown if so declared).
    if source_kind not in ("fixture", "unknown", "imported"):
        source_kind = "imported"

    if evidence_ref:
        val = validate_evidence_file(evidence_ref, evidence_hash)
        evidence_status = val["status"]
        if not val["is_valid"]:
            exclusion_reasons.append(val["exclusion_reason"])
    else:
        # PROV-03: Without evidence file, cannot be verified
        evidence_status = "unverified"
        if "unverified_import" not in exclusion_reasons and source_kind == "imported":
            exclusion_reasons.append("unverified_import")

    # Cost calculation
    cost_info = calculate_cost_detailed(
        input_tokens=run_dict.get("input_tokens"),
        cache_read_tokens=run_dict.get("cache_read_tokens"),
        output_tokens=run_dict.get("output_tokens"),
        model=model,
        thinking_tokens=run_dict.get("thinking_tokens"),
        conn=conn,
        db_path=db_path,
        is_simulation=bool(run_dict.get("is_simulation", 0)),
        is_partial=bool(run_dict.get("is_partial", False)),
        acus_consumed=run_dict.get("acus_consumed"),
        acu_usd_rate=run_dict.get("acu_usd_rate"),
    )
    cost_usd = run_dict.get("cost_usd") if run_dict.get("cost_usd") is not None else cost_info["cost_usd"]
    cost_status = run_dict.get("cost_status") or cost_info["cost_status"]
    cost_source = run_dict.get("cost_source") or cost_info.get("cost_source")
    acus_consumed = run_dict.get("acus_consumed")
    acu_usd_rate = run_dict.get("acu_usd_rate") if run_dict.get("acu_usd_rate") is not None else cost_info.get("acu_usd_rate")
    estimated_cost_usd = run_dict.get("estimated_cost_usd") if run_dict.get("estimated_cost_usd") is not None else cost_info.get("estimated_cost_usd")
    if cost_info["reasons"]:
        for r in cost_info["reasons"]:
            if r not in exclusion_reasons:
                exclusion_reasons.append(r)

    total_tokens = run_dict.get("total_tokens")
    if total_tokens is None and run_dict.get("input_tokens") is not None:
        adapter = run_dict.get("adapter_name") or run_dict.get("cache_accounting")
        if not adapter:
            try:
                rates = get_pricing(model, conn=conn, db_path=db_path)
                adapter = rates.get("cache_accounting") if rates else None
            except Exception:
                pass
        total_tokens = reconstruct_total_tokens(
            input_tokens=run_dict.get("input_tokens"),
            output_tokens=run_dict.get("output_tokens"),
            thinking_tokens=run_dict.get("thinking_tokens"),
            cache_read_tokens=run_dict.get("cache_read_tokens"),
            adapter_name=adapter,
        )

    run_id = record_run(
        task_id=task_id,
        arm=arm,
        model=model,
        run_index=run_index,
        timestamp=timestamp,
        input_tokens=run_dict.get("input_tokens"),
        output_tokens=run_dict.get("output_tokens"),
        thinking_tokens=run_dict.get("thinking_tokens"),
        cache_read_tokens=run_dict.get("cache_read_tokens"),
        total_tokens=total_tokens,
        num_turns=run_dict.get("num_turns", 1),
        duration_seconds=run_dict.get("duration_seconds", 0.0),
        source_kind=source_kind,
        evidence_status=evidence_status,
        exclusion_reasons=exclusion_reasons,
        evidence_ref=evidence_ref,
        evidence_hash=evidence_hash,
        import_id=import_id,
        cost_status=cost_status,
        cost_usd=cost_usd,
        cost_source=cost_source,
        acus_consumed=acus_consumed,
        acu_usd_rate=acu_usd_rate,
        estimated_cost_usd=estimated_cost_usd,
        is_simulation=bool(run_dict.get("is_simulation", 0)),
        notes=run_dict.get("notes"),
        execution_status=run_dict.get("execution_status") or "completed",
        verification_status=run_dict.get("verification_status") or "not_run",
        manifest_id=run_dict.get("manifest_id"),
        evaluator_hash=run_dict.get("evaluator_hash"),
        tool_calls_count=run_dict.get("tool_calls_count"),
        tool_errors_count=run_dict.get("tool_errors_count"),
        max_consecutive_tool_streak=run_dict.get("max_consecutive_tool_streak"),
        loop_detected=run_dict.get("loop_detected"),
        conn=conn,
        db_path=db_path,
    )
    return run_id


def _compute_arm_efficiency_metrics(arm_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute pass-rate, cost/tokens per passing patch, and tool/loop metrics over arm rows."""
    verified_count = len([r for r in arm_rows if r.get("verification_status") == "passed"])
    pass_rate = (verified_count / len(arm_rows)) if arm_rows else None
    # Compute per-pass metrics over telemetry-bearing rows only, so runs with
    # cost_status="unavailable" / null token counters don't null the aggregate.
    cost_rows = [r for r in arm_rows if r.get("cost_usd") is not None]
    cost_passes = len([r for r in cost_rows if r.get("verification_status") == "passed"])
    cost_per_passing_patch_usd = (
        sum(r["cost_usd"] for r in cost_rows) / cost_passes
        if cost_passes > 0
        else None
    )
    token_rows = [r for r in arm_rows if r.get("total_tokens") is not None]
    token_passes = len([r for r in token_rows if r.get("verification_status") == "passed"])
    tokens_per_passing_patch = (
        sum(r["total_tokens"] for r in token_rows) / token_passes
        if token_passes > 0
        else None
    )
    total_tool_calls = sum(
        int(r["tool_calls_count"]) for r in arm_rows if r.get("tool_calls_count") is not None
    )
    total_tool_errors = sum(
        int(r["tool_errors_count"]) for r in arm_rows if r.get("tool_errors_count") is not None
    )
    loop_runs_count = sum(1 for r in arm_rows if bool(r.get("loop_detected")))
    return {
        "passed_count": verified_count,
        "pass_rate": pass_rate,
        "cost_per_passing_patch_usd": cost_per_passing_patch_usd,
        "tokens_per_passing_patch": tokens_per_passing_patch,
        "total_tool_calls": total_tool_calls,
        "total_tool_errors": total_tool_errors,
        "loop_runs_count": loop_runs_count,
    }


def _compute_task_summary_with_rows(
    task_id: str,
    conn: sqlite3.Connection,
    model_override: Optional[str] = None,
    include_all: bool = False,
    capture_policy: str = "approved",
    model_filter: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Internal helper returning (task_summary_dict, enriched_rows)."""
    cursor = conn.cursor()
    if model_filter is not None:
        cursor.execute(
            "SELECT * FROM runs WHERE task_id = ? AND model = ? ORDER BY arm, run_index",
            (task_id, model_filter),
        )
    else:
        cursor.execute("SELECT * FROM runs WHERE task_id = ? ORDER BY arm, run_index", (task_id,))
    rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        return {
            "task_id": task_id,
            "model": model_filter,
            "series_id": f"{task_id}::{model_filter or ''}",
            "has_measured_data": False,
            "status": "empty",
            "total_runs": 0,
            "measured_runs_count": 0,
            "comparison_eligible_runs_count": 0,
            "passed_runs_count": 0,
            "failed_runs_count": 0,
            "cost_incomplete_runs_count": 0,
            "arms": {},
            "savings": None,
        }, []

    is_sim = (model_override is not None)

    for r in rows:
        model_to_use = model_override or r["model"]
        is_row_partial = (r.get("cost_status") == "incomplete") or (
            isinstance(r.get("exclusion_reasons"), str) and "partial_telemetry" in r["exclusion_reasons"]
        )
        cost_info = calculate_cost_detailed(
            r["input_tokens"],
            r["cache_read_tokens"],
            r["output_tokens"],
            model_to_use,
            thinking_tokens=r.get("thinking_tokens"),
            conn=conn,
            is_simulation=is_sim or bool(r.get("is_simulation", 0)),
            is_partial=is_row_partial,
            acus_consumed=None if is_sim else r.get("acus_consumed"),
            acu_usd_rate=None if is_sim else r.get("acu_usd_rate"),
        )
        if not is_sim and r.get("cost_status") in ("unavailable", "incomplete"):
            pass
        else:
            r["cost_status"] = cost_info["cost_status"]

        if r.get("cost_usd") is None or is_sim:
            r["cost_usd"] = cost_info["cost_usd"]
        if not is_sim:
            r["cost_source"] = r.get("cost_source") or cost_info.get("cost_source") or classify_cost_source(r)
            if r["cost_source"] == COST_SOURCE_ESTIMATED_ACU_DERIVED:
                if r.get("estimated_cost_usd") is None and r.get("cost_usd") is not None:
                    r["estimated_cost_usd"] = r["cost_usd"]
                if r.get("acu_usd_rate") is None and cost_info.get("acu_usd_rate") is not None:
                    r["acu_usd_rate"] = cost_info["acu_usd_rate"]
        else:
            r["cost_source"] = cost_info.get("cost_source") or classify_cost_source(r)

        elig = evaluate_run_eligibility(r, capture_policy=capture_policy)
        r["is_eligible"] = elig["is_eligible"]
        r["is_measurement_eligible"] = elig["is_measurement_eligible"]
        r["is_comparison_eligible"] = elig["is_comparison_eligible"]
        r["provenance_valid"] = elig["provenance_valid"]
        r["reporting_category"] = elig["category"]
        r["exclusion_reasons"] = elig["exclusion_reasons"]
        r["is_cost_complete"] = elig["is_cost_complete"]
        r["correctness_status"] = elig["correctness_status"]
        r["is_correct"] = elig["is_correct"]

        if is_sim:
            r["is_simulation"] = 1

    # Partition runs
    measured_runs = [r for r in rows if r["reporting_category"] == "measured" and not r.get("is_simulation")]
    sim_measured_runs = [
        r for r in rows
        if r["reporting_category"] == "measured"
        and r.get("input_tokens") is not None
        and r.get("cost_status") not in ("unavailable", "incomplete")
    ]
    fixture_runs = [r for r in rows if r["reporting_category"] == "fixture"]
    historical_runs = [r for r in rows if r["reporting_category"] == "historical"]
    imported_runs = [r for r in rows if r["reporting_category"] == "imported"]
    simulated_runs = [r for r in rows if r.get("is_simulation") or r["reporting_category"] == "simulation"]

    if is_sim:
        active_runs = [r for r in sim_measured_runs if r.get("is_comparison_eligible")] if not include_all else sim_measured_runs
    else:
        active_runs = [r for r in measured_runs if r.get("is_comparison_eligible")] if not include_all else rows

    has_measured = len(active_runs) > 0

    arms_data: Dict[str, List[Dict[str, Any]]] = {}
    for r in active_runs:
        arm = r["arm"].lower()
        if arm not in arms_data:
            arms_data[arm] = []
        arms_data[arm].append(r)

    task_exc_reasons: List[str] = []
    for r in rows:
        reasons = r.get("exclusion_reasons") or []
        if isinstance(reasons, str):
            try:
                reasons = json.loads(reasons)
            except Exception:
                reasons = [reasons]
        for re_item in reasons:
            if re_item not in task_exc_reasons:
                task_exc_reasons.append(str(re_item))

    series_model = model_filter or (rows[0]["model"] if rows else None)
    summary: Dict[str, Any] = {
        "task_id": task_id,
        "model": series_model,
        "series_id": f"{task_id}::{series_model or ''}",
        "has_measured_data": has_measured,
        "is_simulation": is_sim,
        "total_runs": len(rows),
        "scheduled_count": len(rows),
        "completed_count": len([r for r in rows if r.get("execution_status") == "completed"]),
        "verified_count": len([r for r in rows if r.get("verification_status") == "passed"]),
        "failed_count": len([r for r in rows if r.get("verification_status") in ("failed", "evaluator_error") or r.get("execution_status") == "failed"]),
        "excluded_count": len([r for r in rows if not r.get("is_comparison_eligible")]),
        "cost_eligible_count": len([r for r in rows if r.get("is_measurement_eligible") and r.get("cost_usd") is not None]),
        "exclusion_reasons": task_exc_reasons,
        "source_kinds": sorted(list({str(r.get("source_kind") or "unknown") for r in rows})),
        "evidence_statuses": sorted(list({str(r.get("evidence_status") or "unverified") for r in rows})),
        "measured_runs_count": len(measured_runs) if not is_sim else len(sim_measured_runs),
        "comparison_eligible_runs_count": len([r for r in rows if r.get("is_comparison_eligible")]),
        "passed_runs_count": len([r for r in rows if r.get("verification_status") == "passed"]),
        "failed_runs_count": len([r for r in rows if r.get("verification_status") in ("failed", "evaluator_error")]),
        "unverified_runs_count": len([r for r in rows if r.get("verification_status") == "not_run"]),
        "cost_incomplete_runs_count": len([r for r in rows if not r.get("is_cost_complete")]),
        "fixture_runs_count": len(fixture_runs),
        "historical_runs_count": len(historical_runs),
        "imported_runs_count": len(imported_runs),
        "simulated_runs_count": len(simulated_runs),
        "arms": {},
        "savings": None,
        "excluded_runs": [
            to_public_run(r)
            for r in rows if not r.get("is_comparison_eligible")
        ],
    }

    # Populate per-arm metrics for all arms present in rows
    distinct_arms = sorted(list({r["arm"].lower() for r in rows}))
    for arm_name in distinct_arms:
        all_arm_rows = [r for r in rows if r["arm"].lower() == arm_name]
        qualifying_runs = arms_data.get(arm_name, [])
        telemetry_runs = (
            qualifying_runs
            if qualifying_runs
            else [
                r
                for r in all_arm_rows
                if r.get("source_kind") == "live"
                and r.get("evidence_status") == "verified"
                and r.get("execution_status") == "completed"
            ]
        )
        valid_costs = [r["cost_usd"] for r in qualifying_runs if r["cost_usd"] is not None]
        inputs = [r["input_tokens"] for r in telemetry_runs if r["input_tokens"] is not None]
        caches = [r["cache_read_tokens"] for r in telemetry_runs if r["cache_read_tokens"] is not None]
        outputs = [r["output_tokens"] for r in telemetry_runs if r["output_tokens"] is not None]
        totals = [r["total_tokens"] for r in telemetry_runs if r["total_tokens"] is not None]
        thinkings = [r["thinking_tokens"] for r in telemetry_runs if r.get("thinking_tokens") is not None]
        turns = [r["num_turns"] for r in telemetry_runs]
        durations = [r["duration_seconds"] for r in telemetry_runs]

        mean_cost = sum(valid_costs) / len(valid_costs) if valid_costs else None
        min_cost = min(valid_costs) if valid_costs else None
        max_cost = max(valid_costs) if valid_costs else None

        mean_input = (sum(inputs) / len(inputs)) if inputs else None
        mean_cache = (sum(caches) / len(caches)) if caches else None
        total_prompt = ((mean_input or 0) + (mean_cache or 0))
        cache_hit_ratio = ((mean_cache / total_prompt) if (total_prompt > 0 and mean_cache is not None) else 0.0)

        arm_exc_reasons: List[str] = []
        for r in all_arm_rows:
            reasons = r.get("exclusion_reasons") or []
            if isinstance(reasons, str):
                try:
                    reasons = json.loads(reasons)
                except Exception:
                    reasons = [reasons]
            for re_item in reasons:
                if re_item not in arm_exc_reasons:
                    arm_exc_reasons.append(str(re_item))

        source_kinds = sorted(list({str(r.get("source_kind") or "unknown") for r in all_arm_rows}))
        evidence_statuses = sorted(list({str(r.get("evidence_status") or "unverified") for r in all_arm_rows}))
        active_eff_rows = [r for r in all_arm_rows if r.get("source_kind") != "imported"] or all_arm_rows
        eff = _compute_arm_efficiency_metrics(active_eff_rows)

        summary["arms"][arm_name] = {
            "n": len(qualifying_runs),
            "cost_complete_n": len(valid_costs),
            "scheduled_count": len(all_arm_rows),
            "evaluated_count": len(active_eff_rows),
            "completed_count": len([r for r in all_arm_rows if r.get("execution_status") == "completed"]),
            "verified_count": eff["passed_count"],
            "passed_count": eff["passed_count"],
            "pass_rate": eff["pass_rate"],
            "cost_per_passing_patch_usd": eff["cost_per_passing_patch_usd"],
            "tokens_per_passing_patch": eff["tokens_per_passing_patch"],
            "total_tool_calls": eff["total_tool_calls"],
            "total_tool_errors": eff["total_tool_errors"],
            "loop_runs_count": eff["loop_runs_count"],
            "failed_count": len([r for r in all_arm_rows if r.get("verification_status") in ("failed", "evaluator_error") or r.get("execution_status") == "failed"]),
            "excluded_count": len([r for r in all_arm_rows if not r.get("is_comparison_eligible")]),
            "cost_eligible_count": len([r for r in all_arm_rows if r.get("is_measurement_eligible") and r.get("cost_usd") is not None]),
            "exclusion_reasons": arm_exc_reasons,
            "source_kinds": source_kinds,
            "evidence_statuses": evidence_statuses,
            "model": model_override or all_arm_rows[0]["model"],
            "mean_cost_usd": mean_cost,
            "min_cost_usd": min_cost,
            "max_cost_usd": max_cost,
            "mean_input_tokens": mean_input,
            "mean_cache_read_tokens": mean_cache,
            "mean_output_tokens": (sum(outputs) / len(outputs)) if outputs else None,
            "mean_thinking_tokens": (sum(thinkings) / len(thinkings)) if thinkings else None,
            "mean_total_tokens": (sum(totals) / len(totals)) if totals else None,
            "mean_num_turns": (sum(turns) / len(turns)) if turns else 0,
            "mean_duration_seconds": (sum(durations) / len(durations)) if durations else 0.0,
            "cache_hit_ratio": cache_hit_ratio,
            "runs": [to_public_run(r) for r in qualifying_runs],
        }

    is_task_demo = bool(not has_measured and len(rows) > 0)
    summary["is_demo_report"] = is_task_demo

    if not active_runs or len(arms_data) == 0:
        summary["status"] = "no_eligible_measured_runs"
        return summary, rows

    # Compare baseline vs governed arm
    gov_arm = None
    if "icm-subagents" in summary["arms"] and summary["arms"]["icm-subagents"]["n"] > 0:
        gov_arm = "icm-subagents"
    elif "icm" in summary["arms"] and summary["arms"]["icm"]["n"] > 0:
        gov_arm = "icm"
    elif "delegation" in summary["arms"] and summary["arms"]["delegation"]["n"] > 0:
        gov_arm = "delegation"
    else:
        for k in summary["arms"]:
            if k != "baseline" and summary["arms"][k]["n"] > 0:
                gov_arm = k
                break

    if "baseline" in summary["arms"] and gov_arm:
        b = summary["arms"]["baseline"]
        i = summary["arms"][gov_arm]

        if b["mean_cost_usd"] is not None and i["mean_cost_usd"] is not None:
            cost_diff = b["mean_cost_usd"] - i["mean_cost_usd"]
            cost_pct = (cost_diff / b["mean_cost_usd"] * 100.0) if b["mean_cost_usd"] > 0 else None
            tokens_diff = (b["mean_total_tokens"] - i["mean_total_tokens"]) if (b["mean_total_tokens"] is not None and i["mean_total_tokens"] is not None) else None
            thinking_diff = ((b["mean_thinking_tokens"] or 0) - (i["mean_thinking_tokens"] or 0))
            turns_diff = b["mean_num_turns"] - i["mean_num_turns"]
            duration_diff = b["mean_duration_seconds"] - i["mean_duration_seconds"]

            base_tokens = b["mean_total_tokens"] or 0
            icm_tokens = i["mean_total_tokens"] or 0
            cost_per_mtok_base = (b["mean_cost_usd"] / base_tokens * 1_000_000) if base_tokens > 0 else None
            cost_per_mtok_icm = (i["mean_cost_usd"] / icm_tokens * 1_000_000) if icm_tokens > 0 else None
            savings_per_mtok = (cost_per_mtok_base - cost_per_mtok_icm) if (cost_per_mtok_base is not None and cost_per_mtok_icm is not None) else None

            summary["governed_arm"] = gov_arm
            summary["savings"] = {
                "mean_savings_usd": cost_diff,
                "mean_savings_percent": cost_pct,
                "mean_total_tokens_saved": tokens_diff,
                "mean_thinking_tokens_saved": thinking_diff,
                "mean_turns_saved": turns_diff,
                "mean_duration_seconds_saved": duration_diff,
                "cache_hit_ratio_baseline": b["cache_hit_ratio"],
                "cache_hit_ratio_icm": i["cache_hit_ratio"],
                "cost_per_mtok_baseline": cost_per_mtok_base,
                "cost_per_mtok_icm": cost_per_mtok_icm,
                "savings_usd_per_mtok": savings_per_mtok,
                "projected_savings_10m": (savings_per_mtok * 10) if savings_per_mtok is not None else None,
                "projected_savings_100m": (savings_per_mtok * 100) if savings_per_mtok is not None else None,
            }

    return summary, rows


def task_summary(
    task_id: str,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
    model_override: Optional[str] = None,
    include_all: bool = False,
    capture_policy: str = "approved",
    model_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate per-arm means, error bands, and savings metrics for a task."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    try:
        summary, _ = _compute_task_summary_with_rows(
            task_id=task_id,
            conn=conn,
            model_override=model_override,
            include_all=include_all,
            capture_policy=capture_policy,
            model_filter=model_filter,
        )
        return summary
    finally:
        if should_close:
            conn.close()


def cumulative_savings(
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
    model_override: Optional[str] = None,
    include_mock: bool = False,
    capture_policy: str = "approved",
) -> Dict[str, Any]:
    """Compute total measured savings across all tasks using shared eligibility."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT task_id, model FROM runs ORDER BY task_id, model")
    all_task_models = [(row["task_id"], row["model"]) for row in cursor.fetchall()]

    is_sim = (model_override is not None)

    total_baseline_cost = 0.0
    total_icm_cost = 0.0
    total_baseline_tokens = 0
    total_icm_tokens = 0
    total_token_paired_baseline_cost = 0.0
    total_token_paired_icm_cost = 0.0
    total_token_paired_baseline_tokens = 0
    total_token_paired_icm_tokens = 0
    total_baseline_cache_read = 0
    total_baseline_input = 0
    total_icm_cache_read = 0
    total_icm_input = 0
    total_measured_runs = 0
    task_summaries = []
    all_enriched_rows: List[Dict[str, Any]] = []

    total_fixture_count = 0
    total_historical_count = 0
    total_imported_count = 0
    total_simulated_count = 0
    total_passed_count = 0
    total_failed_count = 0
    total_cost_incomplete_count = 0
    total_comparison_eligible_count = 0

    has_measured_pairs = False

    for tid, model_name in all_task_models:
        s, enriched_rows = _compute_task_summary_with_rows(
            tid,
            conn=conn,
            model_override=model_override,
            capture_policy=capture_policy,
            model_filter=model_name,
        )
        task_summaries.append(s)
        all_enriched_rows.extend(enriched_rows)

        total_fixture_count += s.get("fixture_runs_count", 0)
        total_historical_count += s.get("historical_runs_count", 0)
        total_imported_count += s.get("imported_runs_count", 0)
        total_simulated_count += s.get("simulated_runs_count", 0)
        total_passed_count += s.get("passed_runs_count", 0)
        total_failed_count += s.get("failed_runs_count", 0)
        total_cost_incomplete_count += s.get("cost_incomplete_runs_count", 0)
        total_comparison_eligible_count += s.get("comparison_eligible_runs_count", 0)

        gov_arm = s.get("governed_arm")
        if s.get("has_measured_data") and "baseline" in s.get("arms", {}) and gov_arm and gov_arm in s.get("arms", {}):
            b_n = s["arms"]["baseline"]["n"]
            g_n = s["arms"][gov_arm]["n"]
            total_measured_runs += b_n + g_n

            b_runs = {r["run_index"]: r for r in s["arms"]["baseline"]["runs"]}
            g_runs = {r["run_index"]: r for r in s["arms"][gov_arm]["runs"]}
            common_indexes = sorted(set(b_runs.keys()) & set(g_runs.keys()))
            for ridx in common_indexes:
                b_r = b_runs[ridx]
                g_r = g_runs[ridx]
                if b_r.get("cost_usd") is not None and g_r.get("cost_usd") is not None:
                    total_baseline_cost += b_r["cost_usd"]
                    total_icm_cost += g_r["cost_usd"]
                    b_tok = b_r.get("total_tokens") or 0
                    g_tok = g_r.get("total_tokens") or 0
                    total_baseline_tokens += b_tok
                    total_icm_tokens += g_tok
                    if b_tok > 0 and g_tok > 0:
                        total_token_paired_baseline_cost += b_r["cost_usd"]
                        total_token_paired_icm_cost += g_r["cost_usd"]
                        total_token_paired_baseline_tokens += b_tok
                        total_token_paired_icm_tokens += g_tok
                    total_baseline_cache_read += (b_r.get("cache_read_tokens") or 0)
                    total_baseline_input += (b_r.get("input_tokens") or 0)
                    total_icm_cache_read += (g_r.get("cache_read_tokens") or 0)
                    total_icm_input += (g_r.get("input_tokens") or 0)
                    has_measured_pairs = True

    if has_measured_pairs:
        measured_savings_usd = total_baseline_cost - total_icm_cost
        savings_pct = (
            (measured_savings_usd / total_baseline_cost * 100.0)
            if total_baseline_cost > 0
            else None
        )
        cost_per_mtok_base = (
            (total_token_paired_baseline_cost / total_token_paired_baseline_tokens * 1_000_000)
            if total_token_paired_baseline_tokens > 0
            else None
        )
        cost_per_mtok_icm = (
            (total_token_paired_icm_cost / total_token_paired_icm_tokens * 1_000_000)
            if total_token_paired_icm_tokens > 0
            else None
        )
        savings_usd_per_mtok = (cost_per_mtok_base - cost_per_mtok_icm) if (cost_per_mtok_base is not None and cost_per_mtok_icm is not None) else None
        total_icm_all_in = total_icm_input + total_icm_cache_read
        total_base_all_in = total_baseline_input + total_baseline_cache_read
        icm_cache_hit_pct = round(total_icm_cache_read / total_icm_all_in * 100.0, 1) if total_icm_all_in > 0 else None
        baseline_cache_hit_pct = round(total_baseline_cache_read / total_base_all_in * 100.0, 1) if total_base_all_in > 0 else None
    else:
        measured_savings_usd = None
        savings_pct = None
        cost_per_mtok_base = None
        cost_per_mtok_icm = None
        savings_usd_per_mtok = None
        icm_cache_hit_pct = None
        baseline_cache_hit_pct = None

    # Compute per-arm counts across all task summaries
    per_arm_counts: Dict[str, Dict[str, Any]] = {}
    for s in task_summaries:
        for arm_name, arm_stat in s.get("arms", {}).items():
            if arm_name not in per_arm_counts:
                per_arm_counts[arm_name] = {
                    "scheduled": 0,
                    "completed": 0,
                    "verified": 0,
                    "failed": 0,
                    "excluded": 0,
                    "cost_eligible": 0,
                    "exclusion_reasons": set(),
                }
            per_arm_counts[arm_name]["scheduled"] += arm_stat.get("scheduled_count", 0)
            per_arm_counts[arm_name]["completed"] += arm_stat.get("completed_count", 0)
            per_arm_counts[arm_name]["verified"] += arm_stat.get("verified_count", 0)
            per_arm_counts[arm_name]["failed"] += arm_stat.get("failed_count", 0)
            per_arm_counts[arm_name]["excluded"] += arm_stat.get("excluded_count", 0)
            per_arm_counts[arm_name]["cost_eligible"] += arm_stat.get("cost_eligible_count", 0)
            for re_item in arm_stat.get("exclusion_reasons", []):
                per_arm_counts[arm_name]["exclusion_reasons"].add(re_item)

    cumulative_arms: Dict[str, Dict[str, Any]] = {}
    for arm_name in per_arm_counts:
        per_arm_counts[arm_name]["exclusion_reasons"] = sorted(list(per_arm_counts[arm_name]["exclusion_reasons"]))
        arm_rows = [r for r in all_enriched_rows if r["arm"].lower() == arm_name]
        active_arm_rows = [r for r in arm_rows if r.get("source_kind") != "imported"] or arm_rows
        eff = _compute_arm_efficiency_metrics(active_arm_rows)
        per_arm_counts[arm_name].update(eff)
        cumulative_arms[arm_name] = dict(eff)

    for required_arm in ("baseline", "icm"):
        if required_arm not in cumulative_arms:
            cumulative_arms[required_arm] = _compute_arm_efficiency_metrics([])

    failed_rows = [
        r for r in all_enriched_rows
        if r.get("verification_status") in ("failed", "evaluator_error") or r.get("execution_status") == "failed"
    ]
    failed_inputs = [r["input_tokens"] for r in failed_rows if r.get("input_tokens") is not None]
    failed_outputs = [r["output_tokens"] for r in failed_rows if r.get("output_tokens") is not None]
    failed_costs = [r["cost_usd"] for r in failed_rows if r.get("cost_usd") is not None]

    failed_avg_input_tokens = (sum(failed_inputs) / len(failed_inputs)) if failed_inputs else None
    failed_avg_output_tokens = (sum(failed_outputs) / len(failed_outputs)) if failed_outputs else None
    failed_avg_cost_usd = (sum(failed_costs) / len(failed_costs)) if failed_costs else None

    total_scheduled = sum(a["scheduled"] for a in per_arm_counts.values())
    total_completed = sum(a["completed"] for a in per_arm_counts.values())
    total_verified = sum(a["verified"] for a in per_arm_counts.values())
    total_failed = sum(a["failed"] for a in per_arm_counts.values())
    total_excluded = sum(a["excluded"] for a in per_arm_counts.values())

    is_demo = bool(not has_measured_pairs and (total_fixture_count > 0 or total_historical_count > 0 or total_imported_count > 0 or total_simulated_count > 0 or total_scheduled > 0))

    cursor.execute("PRAGMA table_info(runs)")
    table_cols = {row[1] for row in cursor.fetchall()}
    if "source_kind" in table_cols:
        cursor.execute("SELECT source_kind, count(*) as c FROM runs GROUP BY source_kind")
        source_kind_counts = {row["source_kind"]: row["c"] for row in cursor.fetchall()}
    else:
        cursor.execute("SELECT count(*) as c FROM runs")
        total_c = cursor.fetchone()["c"]
        source_kind_counts = {"unknown": total_c} if total_c > 0 else {}

    if "evidence_status" in table_cols:
        cursor.execute("SELECT evidence_status, count(*) as c FROM runs GROUP BY evidence_status")
        evidence_status_counts = {row["evidence_status"]: row["c"] for row in cursor.fetchall()}
    else:
        cursor.execute("SELECT count(*) as c FROM runs")
        total_c = cursor.fetchone()["c"]
        evidence_status_counts = {"unverified": total_c} if total_c > 0 else {}

    result = {
        "has_measured_data": has_measured_pairs,
        "is_simulation": is_sim,
        "counter_semantics_qualification": (
            "Token counts represent source model tokenizer outputs; cross-model repricing is an indicative rate-card simulation that does not adjust for target model tokenization ratios, cache threshold semantics, or thinking token billing differences."
            if is_sim else None
        ),
        "is_demo_report": is_demo,
        "tasks_evaluated": len([t for t in task_summaries if t.get("has_measured_data")]),
        "total_tasks": len(task_summaries),
        "total_runs": total_measured_runs,
        "scheduled_count": total_scheduled,
        "completed_count": total_completed,
        "verified_count": total_verified,
        "failed_count": total_failed,
        "excluded_count": total_excluded,
        "per_arm_counts": per_arm_counts,
        "arms": cumulative_arms,
        "failed_avg_input_tokens": failed_avg_input_tokens,
        "failed_avg_output_tokens": failed_avg_output_tokens,
        "failed_avg_cost_usd": failed_avg_cost_usd,
        "source_kind_counts": source_kind_counts,
        "evidence_status_counts": evidence_status_counts,
        "fixture_runs_count": total_fixture_count,
        "historical_runs_count": total_historical_count,
        "imported_runs_count": total_imported_count,
        "simulated_runs_count": total_simulated_count,
        "passed_runs_count": total_passed_count,
        "failed_runs_count": total_failed_count,
        "cost_incomplete_runs_count": total_cost_incomplete_count,
        "comparison_eligible_runs_count": total_comparison_eligible_count,
        "total_baseline_cost_usd": total_baseline_cost if has_measured_pairs else None,
        "total_icm_cost_usd": total_icm_cost if has_measured_pairs else None,
        "total_baseline_tokens": total_baseline_tokens if has_measured_pairs else None,
        "total_icm_tokens": total_icm_tokens if has_measured_pairs else None,
        "cumulative_savings_usd": measured_savings_usd,
        "cumulative_savings_percent": savings_pct,
        "pct_saved_usd": savings_pct,
        "baseline_cache_hit_pct": baseline_cache_hit_pct,
        "icm_cache_hit_pct": icm_cache_hit_pct,
        "cost_per_mtok_baseline": cost_per_mtok_base,
        "cost_per_mtok_icm": cost_per_mtok_icm,
        "savings_usd_per_mtok": savings_usd_per_mtok,
        "projected_savings_10m": (savings_usd_per_mtok * 10) if savings_usd_per_mtok is not None else None,
        "projected_savings_100m": (savings_usd_per_mtok * 100) if savings_usd_per_mtok is not None else None,
        "tasks": task_summaries,
    }

    if should_close:
        conn.close()

    return result


def print_cascade(conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None) -> None:
    """Print multi-model spend cascade demonstrating how savings scale across model price tiers."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pricing ORDER BY input_usd_per_mtok ASC")
        pricing_rows = [dict(r) for r in cursor.fetchall()]

        if not pricing_rows:
            print("No pricing models found in ledger.")
            return

        print("=" * 86)
        print("  SPEND CASCADE ACROSS FOUNDATION MODELS (Measured Token Profile)")
        print("=" * 86)
        header = f"{'Model':<20} | {'In/M':<7} | {'Out/M':<7} | {'Cache/M':<7} | {'Baseline':<9} | {'ICM':<9} | {'Saved ($)':<9} | {'Save %':<6} | {'100M Scale'}"
        print(header)
        print("-" * 86)

        for p in pricing_rows:
            m = p["model"]
            cum = cumulative_savings(conn=conn, model_override=m)
            b_cost = cum["total_baseline_cost_usd"]
            i_cost = cum["total_icm_cost_usd"]
            saved = cum["cumulative_savings_usd"]
            pct = cum["cumulative_savings_percent"]
            proj_100m = cum["projected_savings_100m"]

            b_str = f"${b_cost:<8.4f}" if b_cost is not None else "N/A     "
            i_str = f"${i_cost:<8.4f}" if i_cost is not None else "N/A     "
            s_str = f"${saved:<8.4f}" if saved is not None else "N/A     "
            p_str = f"{pct:>5.1f}%" if pct is not None else " N/A "
            pr_str = f"+${proj_100m:,.2f}" if proj_100m is not None else "N/A"

            row = (
                f"{m:<20} | "
                f"${p['input_usd_per_mtok']:<6.3f} | "
                f"${p['output_usd_per_mtok']:<6.2f} | "
                f"${p['cache_read_usd_per_mtok']:<6.4f} | "
                f"{b_str} | "
                f"{i_str} | "
                f"{s_str} | "
                f"{p_str} | "
                f"{pr_str}"
            )
            print(row)

        print("=" * 86)
        print("[ENTERPRISE PROJECTIONS @ 1 BILLION TOKENS]")
        for p in pricing_rows:
            m = p["model"]
            cum = cumulative_savings(conn=conn, model_override=m)
            saved_1b = (cum["savings_usd_per_mtok"] * 1000.0) if cum["savings_usd_per_mtok"] is not None else None
            base_1b = (cum["cost_per_mtok_baseline"] * 1000.0) if cum["cost_per_mtok_baseline"] is not None else None
            icm_1b = (cum["cost_per_mtok_icm"] * 1000.0) if cum["cost_per_mtok_icm"] is not None else None
            if saved_1b is not None and base_1b is not None and icm_1b is not None:
                print(f"  • {m:<20}: Base ${base_1b:>10,.2f}  ->  ICM ${icm_1b:>10,.2f}  |  Net Savings: +${saved_1b:>10,.2f}")
            else:
                print(f"  • {m:<20}: Pricing simulation unavailable (no qualifying tokens)")
        print("=" * 86)
    finally:
        if should_close:
            conn.close()


def print_summary(
    task_id: Optional[str] = None,
    model_override: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Pretty-print summary to terminal."""
    conn = get_connection(db_path)
    try:
        if model_override:
            try:
                rates = get_pricing(model_override, conn=conn)
                print("~" * 72)
                print(f"  [SIMULATED MODEL PRICING: {model_override.upper()}]")
                print(f"  Rates: Input ${rates['input_usd_per_mtok']:.3f}/M, Cache ${rates['cache_read_usd_per_mtok']:.4f}/M, Output ${rates['output_usd_per_mtok']:.2f}/M")
                print("~" * 72)
            except Exception as e:
                print(f"~ Warning: could not load simulated rates for {model_override}: {e} ~")

        if task_id:
            s = task_summary(task_id, conn=conn, model_override=model_override)
            if s.get("total_runs", 0) == 0:
                print(f"No runs found for task: {task_id}")
                return

            print("=" * 72)
            print(f"  USAGE LEDGER SUMMARY: Task {task_id}")
            print(f"  Total Runs: {s['total_runs']} (Measured: {s['measured_runs_count']}, Fixtures: {s['fixture_runs_count']}, Historical: {s['historical_runs_count']}, Imported: {s['imported_runs_count']})")
            if not s["has_measured_data"] and not s["is_simulation"]:
                print("  [STATUS: NO ELIGIBLE MEASURED DATA — Excluded from empirical totals]")
            print("=" * 72)
            arm_names = sorted(s.get("arms", {}).keys(), key=lambda x: (0 if x == "baseline" else 1, x))
            for arm_name in arm_names:
                a = s["arms"][arm_name]
                print(f"\n[{arm_name.upper()} ARM] (n={a['n']}, Model: {a['model']})")
                cost_str = f"${a['mean_cost_usd']:.5f}" if a["mean_cost_usd"] is not None else "unavailable"
                print(f"  Mean Cost:           {cost_str}")
                in_str = f"{a['mean_input_tokens']:,.0f}" if a['mean_input_tokens'] is not None else "unknown"
                cache_str = f"{a['mean_cache_read_tokens']:,.0f}" if a['mean_cache_read_tokens'] is not None else "unknown"
                out_str = f"{a['mean_output_tokens']:,.0f}" if a['mean_output_tokens'] is not None else "unknown"
                tot_str = f"{a['mean_total_tokens']:,.0f}" if a['mean_total_tokens'] is not None else "unknown"
                print(f"  Mean Input Tokens:   {in_str}")
                print(f"  Mean Cache Read:     {cache_str}")
                print(f"  Mean Output Tokens:  {out_str}")
                print(f"  Mean Total Tokens:   {tot_str}")
                print(f"  Cache Hit Ratio:     {a['cache_hit_ratio'] * 100:.2f}%")
                print(f"  Mean Turns:          {a['mean_num_turns']:.1f}")
                print(f"  Mean Duration:       {a['mean_duration_seconds']:.2f}s")

            if s.get("savings"):
                sv = s["savings"]
                gov_label = s.get("governed_arm", "ICM").upper()
                print("-" * 72)
                print(f"[MEASURED SAVINGS: BASELINE vs. {gov_label}]")
                print(f"  Cost Reduction:      ${sv['mean_savings_usd']:.5f} ({sv['mean_savings_percent']:.2f}%)")
                if sv['mean_total_tokens_saved'] is not None:
                    print(f"  Total Tokens Saved:  {sv['mean_total_tokens_saved']:,.0f}")
                print(f"  Turns Saved:         {sv['mean_turns_saved']:.1f}")
                print(f"  Duration Saved:      {sv['mean_duration_seconds_saved']:.2f}s")
                print(f"  Cache Hit Ratio:     Baseline {sv['cache_hit_ratio_baseline']*100:.1f}% -> {gov_label} {sv['cache_hit_ratio_icm']*100:.1f}%")
            print("=" * 72)

        else:
            cum = cumulative_savings(conn=conn, model_override=model_override)
            print("=" * 72)
            print("  USAGE LEDGER CUMULATIVE SUMMARY (ALL TASKS)")
            print("=" * 72)
            print(f"Tasks Evaluated (Measured): {cum['tasks_evaluated']} of {cum['total_tasks']}")
            print(f"Measured Runs Recorded:     {cum['total_runs']}")
            print(f"Excluded / Historical Runs: Fixture: {cum['fixture_runs_count']} | Historical: {cum['historical_runs_count']} | Imported: {cum['imported_runs_count']}")
            if cum["has_measured_data"]:
                print(f"Total Baseline Cost:        ${cum['total_baseline_cost_usd']:.5f}")
                print(f"Total ICM Cost:             ${cum['total_icm_cost_usd']:.5f}")
                print(f"Cumulative Savings:         ${cum['cumulative_savings_usd']:.5f} ({cum['cumulative_savings_percent']:.2f}%)")
            else:
                print("Status:                     No qualifying measured runs exist.")
            print("=" * 72)
    finally:
        conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="A/B Usage Ledger SQLite Engine")
    subparsers = parser.add_subparsers(dest="command")

    # init
    init_p = subparsers.add_parser("init", help="Initialize the database schema")
    init_p.add_argument("--db", default=None, help="Custom path to SQLite database")

    # migrate
    mig_p = subparsers.add_parser("migrate", help="Migrate database to Phase 1 provenance schema")
    mig_p.add_argument("--db", default=None, help="Custom path to SQLite database")

    # seed-pricing
    seed_p = subparsers.add_parser("seed-pricing", help="Seed pricing table from config/PRICING.json")
    seed_p.add_argument("--config", help="Custom path to PRICING.json")
    seed_p.add_argument("--db", default=None, help="Custom path to SQLite database")
    seed_p.add_argument("--prune", action="store_true", help="Remove stale pricing rows absent from config")

    # summary
    sum_p = subparsers.add_parser("summary", help="Print summary of tasks and savings")
    sum_p.add_argument("task_id", nargs="?", default=None, help="Task ID to summarize")
    sum_p.add_argument("--model", "-m", default=None, help="Simulate spend under a specific model pricing rate card")
    sum_p.add_argument("--db", default=None, help="Custom path to SQLite database")

    # cumulative
    cum_p = subparsers.add_parser("cumulative", help="Print cumulative measured savings across all tasks")
    cum_p.add_argument("--model", "-m", default=None, help="Simulate spend under a specific model pricing rate card")
    cum_p.add_argument("--db", default=None, help="Custom path to SQLite database")

    # cascade
    casc_p = subparsers.add_parser("cascade", help="Print multi-model spend cascade demonstrating how savings scale")
    casc_p.add_argument("--db", default=None, help="Custom path to SQLite database")

    args = parser.parse_args()
    custom_db = Path(args.db) if hasattr(args, "db") and args.db else None

    if args.command == "init":
        conn = get_connection(custom_db)
        conn.close()
        print("✓ Ledger database initialized.")
    elif args.command == "migrate":
        conn = get_connection(custom_db)
        applied = migrate_db(conn)
        conn.close()
        if applied:
            print("✓ Database successfully migrated to Phase 1 schema.")
        else:
            print("✓ Database was already migrated (no changes needed).")
    elif args.command == "seed-pricing":
        p = Path(args.config) if args.config else None
        count = seed_pricing(pricing_path=p, db_path=custom_db, prune=args.prune)
        print(f"✓ Seeded pricing for {count} model(s) from config/PRICING.json.")
    elif args.command == "cascade":
        print_cascade(db_path=custom_db)
    elif args.command == "cumulative":
        print_summary(None, model_override=args.model, db_path=custom_db)
    elif args.command == "summary":
        print_summary(args.task_id, model_override=args.model, db_path=custom_db)
    else:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            print_summary(sys.argv[1], db_path=custom_db)
        else:
            print_summary(None, db_path=custom_db)


if __name__ == "__main__":
    main()

