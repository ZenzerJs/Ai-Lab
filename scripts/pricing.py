#!/usr/bin/env python3
"""
scripts/pricing.py - ACU Cost Normalization & Cost Source Classification

Provides configurable Devin ACU-to-USD conversion (default: $2.25/ACU via
DEVIN_ACU_USD_RATE) and explicit cost_source classification distinguishing
direct API billing ("billed_direct") from ACU-derived estimates
("estimated_acu_derived").
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_PATH = DEFAULT_ROOT / "config" / "PRICING.json"

DEFAULT_DEVIN_ACU_USD_RATE: float = 2.25
DEVIN_ACU_USD_RATE_ENV: str = "DEVIN_ACU_USD_RATE"

COST_SOURCE_BILLED_DIRECT: str = "billed_direct"
COST_SOURCE_ESTIMATED_ACU_DERIVED: str = "estimated_acu_derived"
COST_SOURCE_UNAVAILABLE: str = "unavailable"
VALID_COST_SOURCES = (
    COST_SOURCE_BILLED_DIRECT,
    COST_SOURCE_ESTIMATED_ACU_DERIVED,
    COST_SOURCE_UNAVAILABLE,
)


def _validate_positive_rate(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive finite number, got boolean")
    try:
        rate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive finite number, got {value!r}") from exc
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError(f"{label} must be a positive finite number, got {rate}")
    return rate


def validate_acus_consumed(value: Any) -> Optional[float]:
    """Validate and normalize acus_consumed as a non-negative finite float."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"acus_consumed must be numeric, got boolean: {value}")
    try:
        acus = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"acus_consumed must be numeric, got {value!r}") from exc
    if not math.isfinite(acus) or acus < 0:
        raise ValueError(f"acus_consumed must be a non-negative finite number, got {acus}")
    return round(acus, 6)


def get_devin_acu_usd_rate(
    rate_override: Optional[float] = None,
    pricing_path: Optional[Path] = None,
) -> float:
    """Resolve the USD-per-ACU conversion rate.

    Precedence:
    1. Explicit `rate_override` argument
    2. `DEVIN_ACU_USD_RATE` environment variable
    3. `acu_defaults.devin_acu_usd_rate` in `config/PRICING.json`
    4. `DEFAULT_DEVIN_ACU_USD_RATE` (2.25)
    """
    if rate_override is not None:
        return _validate_positive_rate(rate_override, "acu_usd_rate")

    env_val = os.environ.get(DEVIN_ACU_USD_RATE_ENV)
    if env_val is not None and str(env_val).strip() != "":
        return _validate_positive_rate(env_val.strip(), DEVIN_ACU_USD_RATE_ENV)

    path = Path(pricing_path) if pricing_path is not None else DEFAULT_PRICING_PATH
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            acu_defaults = payload.get("acu_defaults") if isinstance(payload, dict) else None
            if isinstance(acu_defaults, dict) and acu_defaults.get("devin_acu_usd_rate") is not None:
                return _validate_positive_rate(
                    acu_defaults["devin_acu_usd_rate"],
                    "PRICING.json acu_defaults.devin_acu_usd_rate",
                )
        except (OSError, json.JSONDecodeError):
            pass

    return DEFAULT_DEVIN_ACU_USD_RATE


def calculate_acu_cost(
    acus_consumed: Optional[float],
    acu_usd_rate: Optional[float] = None,
    is_simulation: bool = False,
    is_partial: bool = False,
    pricing_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Derive estimated USD cost from Devin ACUs consumed."""
    acus = validate_acus_consumed(acus_consumed)
    if acus is None:
        return {
            "cost_usd": None,
            "estimated_cost_usd": None,
            "acus_consumed": None,
            "acu_usd_rate": None,
            "cost_status": "unavailable",
            "cost_source": COST_SOURCE_UNAVAILABLE,
            "reasons": ["missing_acu_telemetry"],
        }

    rate = get_devin_acu_usd_rate(rate_override=acu_usd_rate, pricing_path=pricing_path)
    estimated = round(acus * rate, 6)

    reasons: List[str] = []
    if is_simulation:
        cost_status = "simulation"
        reasons.append("simulation")
    elif is_partial:
        cost_status = "incomplete"
        reasons.append("partial_telemetry")
    else:
        cost_status = COST_SOURCE_ESTIMATED_ACU_DERIVED

    return {
        "cost_usd": estimated,
        "estimated_cost_usd": estimated,
        "acus_consumed": acus,
        "acu_usd_rate": rate,
        "cost_status": cost_status,
        "cost_source": COST_SOURCE_ESTIMATED_ACU_DERIVED,
        "reasons": reasons,
    }


def classify_cost_source(run: Mapping[str, Any]) -> str:
    """Classify a run's cost_source as billed_direct, estimated_acu_derived, or unavailable."""
    raw_source = run.get("cost_source")
    if isinstance(raw_source, str) and raw_source.strip().lower() in VALID_COST_SOURCES:
        return raw_source.strip().lower()

    status = str(run.get("cost_status") or "").strip().lower()
    cost_usd = run.get("cost_usd")
    has_cost = (
        isinstance(cost_usd, (int, float))
        and not isinstance(cost_usd, bool)
        and math.isfinite(cost_usd)
    )
    acus = run.get("acus_consumed")
    has_acus = (
        isinstance(acus, (int, float))
        and not isinstance(acus, bool)
        and math.isfinite(acus)
    )

    if status == COST_SOURCE_ESTIMATED_ACU_DERIVED:
        return COST_SOURCE_ESTIMATED_ACU_DERIVED
    if has_acus and has_cost and run.get("input_tokens") is None:
        return COST_SOURCE_ESTIMATED_ACU_DERIVED
    if has_cost and status not in ("unavailable", "incomplete", "unknown"):
        return COST_SOURCE_BILLED_DIRECT
    return COST_SOURCE_UNAVAILABLE
